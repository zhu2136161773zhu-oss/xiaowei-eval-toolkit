# -*- coding: utf-8 -*-
"""
项目自检脚本 —— 供 GitHub Actions 与本地使用

检查项：
  1. 所有 Python 文件语法正确
  2. 用例生成器输出结构正确、数量达标
  3. 检测器能命中预期的异常类型
  4. 报告生成器能正常产出

用法：
    python selftest.py
退出码 0 表示全部通过。
"""

import ast
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
PY_FILES = ["gen_cases.py", "run.py", "analyze.py", "report.py",
            "pipeline.py", "make_manual.py", "selftest.py"]
EXPECT_FLAGS = {"context_pollution", "constraint_drop", "vague_failure", "overclaim"}
MIN_CASES = 70


def step(msg):
    print(f"[自检] {msg}", flush=True)


def check_syntax():
    bad = []
    for f in PY_FILES:
        p = ROOT / f
        if not p.exists():
            bad.append(f"{f}: missing")
            continue
        try:
            ast.parse(p.read_text(encoding="utf-8"))
        except SyntaxError as e:
            bad.append(f"{f}: {e}")
    if bad:
        raise AssertionError("syntax errors: " + "; ".join(bad))
    step(f"syntax OK ({len(PY_FILES)} files)")


def check_cases():
    import gen_cases
    cases = gen_cases.generate("all", "all")
    assert len(cases) == len({c["case_id"] for c in cases}), "duplicate case_id"
    assert len(cases) >= MIN_CASES, f"too few cases: {len(cases)}"
    for c in cases:
        assert c["case_id"], "missing case_id"
        assert c["turns"], f"{c['case_id']}: empty turns"
        assert c["expected"], f"{c['case_id']}: missing expected"
        assert c["playbook"] in ("compound", "param", "multi_turn", "boundary"), \
            f"{c['case_id']}: bad playbook {c['playbook']}"
    by = {}
    for c in cases:
        by[c["playbook"]] = by.get(c["playbook"], 0) + 1
    step(f"cases OK ({len(cases)} cases: {by})")


def check_no_page_jump():
    """
    用例不得触发「跳转新页面」—— 回归保护。

    2026-11-04 实测发现：小微在生成小工具时会跳转到独立页面，
    对话被打断，回复根本无法采集，采集链路直接断掉。
    因此所有用例的每一轮指令都不得包含「生成工具」类表述。

    工具类能力已单独归入 D 套 boundary 的「能力边界洞察」分类，
    且只问能力说明、不要求实际生成，故不会触发跳转。
    """
    import re
    import gen_cases
    cases = gen_cases.generate("all", "all")
    trig = re.compile(gen_cases.TRIGGER_PATTERN)
    bad = []
    for c in cases:
        for i, t in enumerate(c["turns"]):
            if trig.search(t):
                bad.append(f"{c['case_id']} 第{i+1}轮: {t[:40]}")
    assert not bad, ("用例触发了页面跳转风险（会导致回复无法采集）:\n  "
                      + "\n  ".join(bad))
    step(f"no page-jump risk OK ({len(cases)} cases checked)")


def check_detector_precision():
    """
    检测器精确率回归 —— 防止「误报比真问题还多」。

    真实评测里误报率过高等于没筛：所有用例都被标成可疑，人工复核成本反而更高。
    这里用四个典型场景锁定检测器行为：
      应命中的必须命中，不该命中的必须干净。
    """
    import analyze
    cfg = {"shingle_size": 3, "state_leak_threshold": 0.34}

    cases = [
        # (场景名, turns, 检查下标, 是否应命中, 检测器)
        ("咖啡→火锅 品类串台（应命中）", [
            {"prompt": "帮我点一杯瑞幸的生椰拿铁去冰",
             "reply": "好的，已经帮你调起瑞幸小程序，选好了生椰拿铁去冰，现在停在订单确认页。"},
            {"prompt": "再帮我在附近找一家评分4.5分以上的火锅店",
             "reply": "抱歉，检索到的都是咖啡相关的小程序，没有匹配到合适的结果，建议您手动打开大众点评。"},
        ], 1, True, "detect_category_leak"),

        ("错题主题延续（不应命中）", [
            {"prompt": "帮我做一个错题记录小工具。",
             "reply": "已经为你生成「错题记录本」小工具，可以记录题目、我的解答和错因。"},
            {"prompt": "我发你一张错题照片，你帮我把题目和我的解答识别出来填进去。",
             "reply": "图片已识别完成：题目是「求 ∫₀^π x·sin x dx」，已帮你填入错题记录本的对应字段。"},
        ], 1, False, "detect_category_leak"),

        ("记账→点外卖 不同品类（不应命中）", [
            {"prompt": "帮我做一个记账小工具。",
             "reply": "已经为你生成记账小工具，含金额与分类字段。"},
            {"prompt": "今天中午吃什么好",
             "reply": "不如试试附近的川菜馆，人均 30 元左右。"},
        ], 1, False, "detect_category_leak"),

        ("咖啡→咖啡 同品类延续（不应命中）", [
            {"prompt": "帮我点一杯瑞幸的生椰拿铁", "reply": "已经帮你调起瑞幸小程序。"},
            {"prompt": "再来一杯生椰拿铁", "reply": "好的，又是一杯生椰拿铁，已加入订单。"},
        ], 1, False, "detect_category_leak"),

        ("串台：消息草稿带出历史用例内容（应命中）", [
            {"prompt": "跟光头强说明天早上来接我", "reply": "可以出发了"},
            {"prompt": "跟光头强发消息说今天不想加班，语气委婉一点", "reply": "可以出发了"},
        ], 1, True, "detect_state_leak"),
    ]

    failed = []
    for name, turns, idx, should_hit, fn_name in cases:
        fn = getattr(analyze, fn_name)
        hits = fn(turns, idx, cfg)
        got = len(hits) > 0
        if got != should_hit:
            failed.append(f"{name}: 期望{'命中' if should_hit else '不命中'}，实际{'命中' if got else '不命中'}")
    assert not failed, "检测器精确率回归失败:\n  " + "\n  ".join(failed)
    step(f"detector precision OK ({len(cases)} scenarios)")


def check_analyzer():
    fixture = ROOT / "data" / "mock_sample.jsonl"
    assert fixture.exists(), "missing fixture data/mock_sample.jsonl"
    import analyze
    # 夹具为「扁平 case」格式（每行一个 case），与 run.py 的落盘格式一致，
    # 需归一化为 session 结构后再分析
    sessions = []
    for line in fixture.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        if "cases" in obj:
            sessions.append(obj)
        elif "turns" in obj:
            sessions.append({"session_id": obj.get("session_id", "flat"),
                             "cases": [obj]})
    assert sessions, "no sessions parsed from fixture"

    cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    results = []
    corpus = []
    for s in sessions:
        results.extend(analyze.analyze_session(s, cfg, corpus))
        for case in s.get("cases", []):
            for t in case.get("turns", []):
                if t.get("reply"):
                    corpus.append((f"case {case.get('case_id')}", t["reply"]))
    flagged = [r for r in results if r["max_severity"] != "none"]
    assert len(flagged) >= 3, f"too few flagged cases: {len(flagged)}"
    types = {f["type"] for r in flagged for f in r["flags"]}
    missing = EXPECT_FLAGS - types
    assert not missing, f"detector missed: {sorted(missing)}"
    step(f"analyzer OK ({len(flagged)} flagged, types: {sorted(types)})")


def check_report():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        out = pathlib.Path(td) / "r.md"
        import report
        results = [{
            "case_id": "T-001", "suite": "T", "playbook": "compound",
            "title": "selftest", "expected": "ok", "entry": "negative_one_screen",
            "turn_count": 1, "max_severity": "medium",
            "flags": [{"type": "vague_failure", "severity": "medium",
                       "detail": "selftest", "evidence": {}}],
            "suggestion": "selftest",
            "turns": [{"index": 0, "prompt": "p", "reply": "r"}],
        }]
        md = report.render_markdown(results, {})
        assert "场景描述" in md and "改进建议" in md, "missing six-element sections"
        assert "issue_name" in md or "一句话总结" in md, "missing form fields"
        step("report OK (six-element + form fields present)")


def main():
    print("=" * 60)
    print("小微评测工具包 · 项目自检")
    print("=" * 60)
    checks = [check_syntax, check_cases, check_no_page_jump, check_detector_precision,
               check_analyzer, check_report]
    failed = 0
    for fn in checks:
        try:
            fn()
        except Exception as e:
            failed += 1
            print(f"[FAIL] {fn.__name__}: {e}", flush=True)
    print("=" * 60)
    if failed:
        print(f"[FAIL] {failed}/{len(checks)} checks failed", flush=True)
        return 1
    print("[PASS] all checks passed", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
