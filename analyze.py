# -*- coding: utf-8 -*-
"""
小微 AI 助手评测 —— 自动异常检测器

对采集到的「指令 → 回复」序列做规则化异常筛查，把人工看不出来的
上下文污染、状态串台、参数丢失、模糊失败话术、幻觉数值、答案翻转
自动标出来，只把可疑样本推给人工复核。

这是官方明确允许且明确给分的手段：
  「用自动化框架生成上万条输入、只挑异常案例提交」—— 允许
  「在报告中展示技术实现与实际效果」—— 允许，且可提升「创新与方法论」评分

用法：
  python analyze.py --input data/raw_xxx.jsonl --config config.json --out data/flagged_xxx.json
"""

import argparse
import json
import os
import re
import unicodedata

# ---------------------------------------------------------------- 文本工具
CJK_PUNCT = "，。！？；：、“”‘’（）《》【】…—～·"

# 通用词黑名单：只由这些词构成的片段没有区分度，不能作为污染/串台证据
GENERIC_FRAGMENTS = {
    "小程序", "建议", "手动", "已经", "帮你", "打开", "搜索", "可以", "无法",
    "系统", "接口", "抱歉", "检索", "相关", "结果", "好的", "一下", "什么",
    "需要", "支持", "功能", "使用", "提供", "找到", "没有", "这个", "那个",
    "目前", "暂时", "直接", "如果", "或者", "一起", "帮你", "为你", "帮你",
    "正在", "正在为你", "订单", "确认", "页面", "服务", "选择", "规格",
    "备注", "如下", "请问", "希望", "根据", "以及", "并且", "然后",
}


def _is_generic(fragment):
    """判断片段是否完全由通用词构成（无区分度）。"""
    if not fragment:
        return True
    for g in GENERIC_FRAGMENTS:
        if fragment == g:
            return True
    # 片段的所有 2 字子串都在黑名单里 → 视为泛词
    if len(fragment) >= 2:
        subs = [fragment[i:i + 2] for i in range(len(fragment) - 1)]
        if all(s in GENERIC_FRAGMENTS for s in subs):
            return True
    return False


def normalize(text):
    """全角转半角 + 去空白 + 去标点 + 小写，用于稳定比对。"""
    if not text:
        return ""
    out = []
    for ch in text:
        code = unicodedata.normalize("NFKC", ch)
        if code in CJK_PUNCT:
            continue
        if code.isspace():
            continue
        # 去掉中英文标点，避免「小程序,」这种带尾巴的碎片
        if unicodedata.category(code).startswith("P"):
            continue
        out.append(code.lower())
    return "".join(out)


def shingles(text, n=3):
    s = normalize(text)
    if len(s) < n:
        return {s} if s else set()
    return {s[i:i + n] for i in range(len(s) - n + 1)}


def jaccard(a, b):
    if not a or not b:
        return 0.0
    inter = len(a & b)
    return inter / float(len(a | b))


def extract_numbers(text):
    """抽出文本中的数字（含中文数字量词），用于幻觉与参数丢失检测。"""
    if not text:
        return []
    norm = unicodedata.normalize("NFKC", text)
    nums = re.findall(r"\d+(?:\.\d+)?", norm)
    cn = re.findall(r"[一二三四五六七八九十百千万零两]+", norm)
    out = []
    for n in nums:
        out.append(n)
    for c in cn:
        out.append("CN:" + c)
    return out


def extract_constraint_tokens(text):
    """抽取指令里的约束词：预算、人数、时间、数量、以及显式限定词。"""
    if not text:
        return []
    norm = unicodedata.normalize("NFKC", text)
    tokens = []
    patterns = [
        r"人均\s*\d+\s*元",
        r"预算[^，。；,\s]{0,6}\d+[^，。；,\s]{0,4}",
        r"\d+\s*人",
        r"\d+\s*元",
        r"\d+\s*分钟(?:后)?",
        r"\d+\s*天(?:后)?",
        r"\d+\s*小时",
        r"\d+\s*周",
        r"\d+\s*项",
        r"\d+\s*%",
        r"以内|以下|不超过|最多|至少|不少于|超过|以上",
        r"附近|周边|身边",
        r"连续\s*\d+\s*天",
    ]
    for p in patterns:
        for m in re.findall(p, norm):
            tokens.append(m)
    return tokens


# ---------------------------------------------------------------- 各类检测器
def detect_context_pollution(turns, idx, cfg):
    """
    上下文污染：本轮回复中出现了属于「前面某一轮」的文本片段，
    且该片段并未出现在本轮指令里 —— 说明前序上下文干扰了当前任务。
    例：先点咖啡，再找火锅 → 火锅回复里冒出「咖啡相关的小程序」。

    实现：对本轮回复取 n-gram，与前序各轮的（指令 + 回复）求差集命中。
    只比对「不在本轮指令中」的片段，避免误报。
    """
    hit = []
    reply = turns[idx]["reply"]
    if not reply:
        return hit
    n = 4
    cur_grams = shingles(reply, n)
    if not cur_grams:
        return hit
    cur_prompt_grams = shingles(turns[idx]["prompt"], n)
    # 本轮回复里出现、但本轮指令里没有的片段
    novel = cur_grams - cur_prompt_grams

    best = None
    for j in range(idx):
        prior_text = (turns[j]["prompt"] or "") + " " + (turns[j]["reply"] or "")
        prior_grams = shingles(prior_text, n)
        shared = {g for g in (novel & prior_grams) if not _is_generic(g)}
        if not shared:
            continue
        # 找出最长连续片段，便于人工判断
        phrase = _longest_common(ngrams=shared, text=normalize(reply), size=n)
        length = len(phrase)
        if best is None or length > best[1]:
            best = (j, length, phrase)

    if best and best[1] >= n:
        j, length, phrase = best
        hit.append({
            "type": "context_pollution",
            "severity": "high" if length >= 6 else "medium",
            "detail": (f"本轮回复中出现了前序（第 {j+1} 轮）的文本片段「{phrase}」，"
                       f"该片段并未出现在本轮指令中，疑似上下文污染"),
            "evidence": {"leaked_from_turn": j + 1, "matched_phrase": phrase,
                         "match_len": length},
        })
    return hit


def _longest_common(ngrams, text, size=4):
    """在原文中找出由命中 n-gram 拼出的最长连续片段。"""
    best = ""
    for g in ngrams:
        if g not in text:
            continue
        # 向两侧扩展
        start = text.find(g)
        left = start
        while left > 0 and text[left - 1:left + size - 1] in ngrams:
            left -= 1
        right = start + size
        while right + size <= len(text) and text[right:right + size] in ngrams:
            right += 1
        cand = text[left:right]
        if len(cand) > len(best):
            best = cand
    return best


def detect_state_leak(turns, idx, cfg):
    """
    状态串台：本轮回复中出现「本轮指令里没有、但之前某轮回复里出现过」的片段，
    说明前序内容被带到了本轮（草稿/上下文未隔离）。
    例：给「光头强」发消息，预填内容变成上一轮的「可以出发了」。

    corpus 为跨会话滚动语料（此前所有用例的回复），
    因为真实的串台常常来自「上一次测试」而非同一条用例内部。
    """
    hit = []
    if not turns[idx].get("reply"):
        return hit
    reply = turns[idx]["reply"]
    n = 3
    cur_grams = shingles(reply, n)
    if not cur_grams:
        return hit
    cur_prompt_grams = shingles(turns[idx]["prompt"], n)
    novel = cur_grams - cur_prompt_grams
    if not novel:
        return hit

    # 候选来源：本用例内的前序回复 + 跨会话滚动语料
    candidates = []
    for j in range(idx):
        old = turns[j].get("reply")
        if old:
            candidates.append((f"本用例第 {j+1} 轮", old))
    for label, old in (cfg.get("_corpus") or []):
        candidates.append((label, old))

    # 若本用例没有任何前序轮次，且无跨会话语料，则无从判断串台
    if not candidates:
        return hit

    best = None
    for label, old in candidates:
        old_grams = shingles(old, n)
        shared = {g for g in (novel & old_grams) if not _is_generic(g)}
        sim = jaccard(cur_grams, old_grams)
        if shared and (best is None or len(shared) > best[1]):
            best = (label, len(shared), sim, old)

    th = cfg.get("state_leak_threshold", 0.34)
    if best and (best[1] >= 2 or best[2] >= th):
        label, shared_n, sim, old_reply = best
        phrase = _longest_common(ngrams=(novel & shingles(old_reply, n)),
                                 text=normalize(reply), size=n)
        hit.append({
            "type": "state_leak",
            "severity": "high",
            "detail": (f"本轮回复中出现「{label}」的残留内容「{phrase or '（片段重合）'}」"
                       f"（相似度 {sim:.2f}），疑似状态隔离失效"),
            "evidence": {"source": label, "similarity": round(sim, 3),
                         "shared_ngrams": shared_n, "matched_phrase": phrase},
        })
    return hit


def extract_entities(text):
    """抽取任务实体词：引号内容、书名号、常见品类词。"""
    if not text:
        return []
    ents = []
    for m in re.findall(r"[「『\"“]([^」』\"”]{2,12})[」』\"”]", text):
        ents.append(m)
    for m in re.findall(r"《([^》]{2,20})》", text):
        ents.append(m)
    for m in re.findall(r"(咖啡|火锅|奶茶|瑞幸|美团|滴滴|星巴克|麦当劳|肯德基)", text):
        ents.append(m)
    return ents


# 品类同义词表：同一品类下的不同说法，用于捕捉「上下文污染」这种语义级串台
# 例：前一轮点了「瑞幸生椰拿铁」，本轮搜「火锅」却返回「咖啡相关的小程序」——
#     字面 n-gram 抓不到，但品类层面能抓到。
CATEGORY_SYNONYMS = {
    "咖啡": ["咖啡", "瑞幸", "生椰拿铁", "拿铁", "美式", "摩卡", "latte", "星巴克"],
    "火锅": ["火锅", "海底捞", "呷哺", "凑凑", "hotpot"],
    "奶茶": ["奶茶", "喜茶", "奈雪", "霸王茶姬", "古茗", "蜜雪"],
    "外卖": ["外卖", "美团", "饿了么", "点餐", "订餐"],
    "打车": ["打车", "滴滴", "出租车", "网约车", "高德打车"],
    "酒店": ["酒店", "住宿", "宾馆", "民宿", "如家", "汉庭"],
    "车票": ["车票", "高铁", "火车票", "12306", "机票", "航班"],
    "外卖平台": ["美团", "饿了么", "大众点评"],
    "记账": ["记账", "账本", "收支", "消费记录", "账单"],
    "打卡": ["打卡", "签到", "早睡", "喝水", "运动记录"],
    "错题": ["错题", "刷题", "题目", "习题", "练习"],
    "团费": ["团费", "团费收缴", "缴费", "收缴"],
    "血压": ["血压", "收缩压", "舒张压", "高压", "低压"],
    "心率": ["心率", "心跳", "脉搏"],
    "血糖": ["血糖", "空腹血糖", "糖化"],
    "步数": ["步数", "走路", "步行", "运动步数"],
    "实验": ["实验", "测量", "采样", "波形", "数据点"],
}


def detect_category_leak(turns, idx, cfg):
    """
    语义级上下文污染：检测本轮回复是否提到了「属于前序任务品类、但不属于本轮任务」
    的品类词。
    例：前一轮点了咖啡，本轮找火锅，回复里却出现「咖啡相关的小程序」。
    """
    hit = []
    reply = turns[idx]["reply"]
    if not reply or idx == 0:
        return hit
    reply_low = normalize(reply)

    # 前序任务涉及的品类
    prior_cats = set()
    for j in range(idx):
        pt = (turns[j]["prompt"] or "") + " " + (turns[j]["reply"] or "")
        for cat, words in CATEGORY_SYNONYMS.items():
            if any(normalize(w) in normalize(pt) for w in words):
                prior_cats.add(cat)
    if not prior_cats:
        return hit

    # 本轮任务涉及的品类
    cur_text = normalize(turns[idx]["prompt"])
    cur_cats = set()
    for cat, words in CATEGORY_SYNONYMS.items():
        if any(normalize(w) in cur_text for w in words):
            cur_cats.add(cat)

    # 本轮回复里出现的品类
    reply_cats = set()
    matched_words = {}
    for cat, words in CATEGORY_SYNONYMS.items():
        for w in words:
            nw = normalize(w)
            if nw and nw in reply_low:
                reply_cats.add(cat)
                matched_words.setdefault(cat, w)

    # 前序有、本轮没有、但回复里出现了 → 污染
    leaked = (prior_cats - cur_cats) & reply_cats
    for cat in leaked:
        hit.append({
            "type": "context_pollution",
            "severity": "high",
            "detail": (f"本轮任务未涉及「{cat}」品类，但回复中出现了「{matched_words.get(cat)}」"
                       f"（该品类属于前序任务），疑似上下文污染"),
            "evidence": {"category": cat, "matched_word": matched_words.get(cat),
                         "prior_categories": sorted(prior_cats),
                         "current_categories": sorted(cur_cats)},
        })
    return hit


def detect_constraint_drop(turns, idx, cfg):
    """
    参数丢失：指令里明确给了约束（预算/人数/附近/时间），
    但回复里完全找不到对应表述。
    例：要求 500 元以下 → 给出 400 元以上的选项。
    """
    hit = []
    prompt = turns[idx]["prompt"]
    reply = turns[idx]["reply"] or ""
    if not reply:
        return hit
    cons = extract_constraint_tokens(prompt)
    if not cons:
        return hit
    norm_reply = normalize(reply)
    norm_prompt = normalize(prompt)
    for c in cons:
        cc = normalize(c)
        if len(cc) < cfg.get("constraint_min_len", 2):
            continue
        if cc in norm_reply:
            continue
        # 数字类约束：检查指令里的数字是否出现在回复
        nums = [n for n in extract_numbers(c) if not n.startswith("CN:")]
        if nums and any(n in unicodedata.normalize("NFKC", reply) for n in nums):
            continue
        # 纯限定词（如「以内」「附近」）单独出现时证据偏弱，降级为 low
        sev = "low" if not nums else "medium"
        hit.append({
            "type": "constraint_drop",
            "severity": sev,
            "detail": f"指令中的约束「{c}」在回复中未体现",
            "evidence": {"constraint": c},
        })
    return hit


def detect_vague_failure(turns, idx, cfg):
    """
    模糊失败话术：小微把失败原因归给「接口 / 系统 / 检索结果」，
    而非坦承自身能力不足。这类回复不是有效交付，需人工判断是否为 Bad Case。
    """
    hit = []
    reply = turns[idx]["reply"] or ""
    if not reply:
        return hit
    for p in cfg.get("vague_phrases", []):
        if p in reply:
            hit.append({
                "type": "vague_failure",
                "severity": "medium",
                "detail": f"回复中出现模糊兜底话术「{p}」",
                "evidence": {"phrase": p},
            })
            break
    return hit


def detect_hallucination_number(turns, idx, cfg):
    """
    数值幻觉：回复中出现了指令里完全没有的数字，
    且量级看起来像「具体数据」（价格、评分、时长、坐标）。
    需人工确认，但这是最容易出真 Bad Case 的一类。
    """
    hit = []
    prompt = unicodedata.normalize("NFKC", turns[idx]["prompt"])
    reply = turns[idx]["reply"] or ""
    if not reply:
        return hit
    reply_norm = unicodedata.normalize("NFKC", reply)
    prompt_nums = set(extract_numbers(prompt))
    # 只看「像真实数据」的数字：带小数点、或 >= 20、或带分值语义
    suspicious = []
    for m in re.finditer(r"\d+(?:\.\d+)?", reply_norm):
        val = m.group()
        if val in prompt_nums:
            continue
        try:
            fv = float(val)
        except ValueError:
            continue
        if "." in val or fv >= 20:
            suspicious.append(val)
    if suspicious:
        uniq = sorted(set(suspicious))[:6]
        hit.append({
            "type": "hallucination_number",
            "severity": "medium",
            "detail": f"回复中出现指令里没有的具体数值：{', '.join(uniq)}",
            "evidence": {"numbers": uniq},
        })
    return hit


def detect_answer_flip(turns, idx, cfg):
    """
    答案翻转（鲁棒性缺陷）：小微先给出了正确答案，
    随后被用户错误质疑后改口 —— 官方答疑明确认定这算 Bad Case。
    需要 case 中包含「质疑句」才会触发。
    """
    hit = []
    if idx < 1:
        return hit
    reply = turns[idx]["reply"] or ""
    if not reply:
        return hit
    doubt_markers = ["不对", "错了", "不是", "你确定", "不是这样", "你搞错", "再想想", "我说的是"]
    prompt = turns[idx]["prompt"]
    if not any(m in prompt for m in doubt_markers):
        return hit
    prev_reply = turns[idx - 1].get("reply") or ""
    if not prev_reply:
        return hit
    # 若本轮回复与上一轮回复差异极大，且本轮出现自我更正确认
    a, b = shingles(prev_reply), shingles(reply)
    sim = jaccard(a, b)
    if sim < 0.2:
        flip_markers = ["抱歉", "你说得对", "我搞错了", "刚才说错", "修正", "确实是我错了"]
        if any(m in reply for m in flip_markers):
            hit.append({
                "type": "answer_flip",
                "severity": "high",
                "detail": "小微疑似在用户错误质疑下推翻了自己先前的正确答案（鲁棒性缺陷）",
                "evidence": {"prev_similarity": round(sim, 3)},
            })
    return hit


def detect_overclaim(turns, idx, cfg):
    """
    越界宣称：官方明示不支持的能力，小微却说「可以 / 支持 / 没问题」。
    这类必须人工复核——说「不支持」是洞察，说「支持」后失败才是 Bad Case。
    """
    hit = []
    reply = turns[idx]["reply"] or ""
    if not reply:
        return hit
    claim = ["可以的", "支持", "没问题", "已经帮你", "已为你"]
    for t in cfg.get("overclaim_targets", []):
        if t in reply:
            if any(c in reply for c in claim):
                hit.append({
                    "type": "overclaim",
                    "severity": "high",
                    "detail": f"对小微明示不支持的能力「{t}」作出了支持性表述，需复核",
                    "evidence": {"target": t},
                })
    return hit


DETECTORS = {
    "context_pollution": detect_context_pollution,
    "category_leak": detect_category_leak,
    "state_leak": detect_state_leak,
    "constraint_drop": detect_constraint_drop,
    "vague_failure": detect_vague_failure,
    "hallucination_number": detect_hallucination_number,
    "answer_flip": detect_answer_flip,
    "overclaim": detect_overclaim,
}


# ---------------------------------------------------------------- 主流程
def analyze_session(session, cfg, corpus=None):
    """session: {"session_id":..., "cases":[...]}，每个 case 含 turns 列表。"""
    a_cfg = cfg.get("analyzer", {})
    # 注入跨会话滚动语料（此前所有用例的回复），供状态串台检测使用
    a_cfg = dict(a_cfg)
    a_cfg["_corpus"] = corpus or []
    results = []
    for case in session.get("cases", []):
        turns = case.get("turns", [])
        flags = []
        for i in range(len(turns)):
            for name, fn in DETECTORS.items():
                key = "enable_" + name
                if not a_cfg.get(key, True):
                    continue
                try:
                    flags.extend(fn(turns, i, a_cfg))
                except Exception as e:
                    flags.append({
                        "type": "detector_error", "severity": "low",
                        "detail": f"{name} 检测异常: {e}", "evidence": {},
                    })
        sev_rank = {"high": 3, "medium": 2, "low": 1}
        max_sev = max((sev_rank.get(f["severity"], 1) for f in flags), default=0)
        results.append({
            "case_id": case.get("case_id"),
            "suite": case.get("suite"),
            "playbook": case.get("playbook"),
            "title": case.get("title"),
            "expected": case.get("expected"),
            "entry": case.get("entry"),
            "turn_count": len(turns),
            "flag_count": len(flags),
            "max_severity": {3: "high", 2: "medium", 1: "low", 0: "none"}[max_sev],
            "flags": flags,
            "turns": turns,
            "suggestion": _suggest(case, flags),
        })
    return results


def _suggest(case, flags):
    """给出一条初步归因猜测，供人工参考。"""
    types = {f["type"] for f in flags}
    if "state_leak" in types and ("context_pollution" in types or "category_leak" in types):
        return ("状态隔离失效 + 上下文污染：怀疑任务编排层未隔离前序子任务的上下文与草稿状态，"
                "建议做「同一指令单发 vs 复合下发」的差分对照以确认。")
    if "state_leak" in types:
        return "状态隔离失效：建议用「清理对话后重发」与「不清理直接重发」做对照，验证是否为记忆缓存污染。"
    if "category_leak" in types:
        return ("上下文污染（品类串台）：本轮任务与前序任务品类不同，回复却携带前序品类的检索结果，"
                "建议把该子任务单独发给小微——若单发正常，即可确认问题定位在复合指令的任务编排层。")
    if "context_pollution" in types:
        return ("上下文污染：建议把该子任务单独发给小微，若单发正常，则问题定位在复合指令的任务编排层，"
                "而非该能力本身。")
    if "constraint_drop" in types:
        return "参数透传断链：建议改写指令为显式重复关键约束后重发，若仍丢失则确认为约束保持缺陷。"
    if "answer_flip" in types:
        return "鲁棒性缺陷：官方答疑明确认定「先答对、后被错误质疑改错」为独立 Bad Case，建议补齐前后两轮完整截图。"
    if "vague_failure" in types:
        return ("失败话术模糊化：需判断该失败属于「主动拒绝（产品红线）」还是「尝试后失败（工程能力不足）」，"
                "后者建议作为 Bad Case 并附上接口名/错误码等细节。")
    if "hallucination_number" in types:
        return "数值幻觉：请人工核对回复中出现的具体数值是否有真实来源，无来源即构成幻觉 Bad Case。"
    if "overclaim" in types:
        return "越界宣称：请核对官方明示的不支持清单，若小微先承诺后失败，认定为 Bad Case 而非洞察。"
    return ""


def main():
    ap = argparse.ArgumentParser(description="小微评测自动异常检测")
    ap.add_argument("--input", required=True, help="采集到的会话 JSON/JSONL")
    ap.add_argument("--config", default="config.json")
    ap.add_argument("--out", required=True, help="输出：标注了异常的用例")
    ap.add_argument("--min-severity", default="low", choices=["low", "medium", "high"])
    args = ap.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    raw = open(args.input, "r", encoding="utf-8").read().strip()
    if not raw:
        print("[ERROR] 输入文件为空")
        return
    if raw.startswith("["):
        sessions = json.loads(raw)
    elif raw.startswith("{") and "\n{" not in raw:
        obj = json.loads(raw)
        sessions = obj if isinstance(obj, list) else [obj]
    else:
        sessions = [json.loads(l) for l in raw.splitlines() if l.strip()]

    # 兼容两种落盘格式：
    #   A) 嵌套 session：{"session_id":..., "cases":[ {...}, ... ]}
    #   B) 扁平 case：  {"case_id":..., "turns":[...]}   （run.py 的 JSONL 产出）
    normalized = []
    for s in sessions:
        if isinstance(s, dict) and "cases" in s:
            normalized.append(s)
        elif isinstance(s, dict) and "turns" in s:
            normalized.append({"session_id": s.get("session_id", "flat"), "cases": [s]})
    sessions = normalized

    all_results = []
    corpus = []          # 跨会话滚动语料：(标签, 回复文本)
    for s in sessions:
        all_results.extend(analyze_session(s, cfg, corpus))
        # 分析完一条会话后，把它的回复加入语料，供后续会话做串台比对
        for case in s.get("cases", []):
            cid = case.get("case_id", "?")
            for t in case.get("turns", []):
                if t.get("reply"):
                    corpus.append((f"历史用例 {cid}", t["reply"]))

    order = {"high": 3, "medium": 2, "low": 1, "none": 0}
    thresh = order[args.min_severity]
    flagged = [r for r in all_results if order.get(r["max_severity"], 0) >= thresh]
    flagged.sort(key=lambda r: (-order.get(r["max_severity"], 0), -r["flag_count"]))

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({
            "analyzed_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
            "total_cases": len(all_results),
            "flagged_cases": len(flagged),
            "results": flagged,
        }, f, ensure_ascii=False, indent=2)

    print(f"[OK] 共分析 {len(all_results)} 条用例，命中可疑 {len(flagged)} 条 -> {args.out}")
    stat = {}
    for r in flagged:
        for fl in r["flags"]:
            stat[fl["type"]] = stat.get(fl["type"], 0) + 1
    if stat:
        print("    异常类型分布:")
        for k, v in sorted(stat.items(), key=lambda kv: -kv[1]):
            print(f"      {k}: {v}")


if __name__ == "__main__":
    main()
