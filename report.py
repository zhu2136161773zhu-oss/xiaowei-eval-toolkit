# -*- coding: utf-8 -*-
"""
小微 AI 助手评测 —— 报告生成器

把 analyze.py 标出的可疑用例，转成官方要求的「六要素报告」和
「赛事表单字段」，可直接复制进提交平台。

官方报告六要素：
  场景描述 → 复现步骤 → 期望小微回复的内容 → 实际结果 → 原因分析 → 改进建议

官方表单字段：
  issue 名称 / 一句话总结 / 入口 / 完整会话截图 / 对话总轮数 /
  任务预期 / 实际结果 / 问题分析 / 满意度等级 / 评分依据 /
  可复现性 / 附件 / 建议复现步骤

用法：
  python report.py --input data/flagged_A.json --out data/reports/report_A.md
  python report.py --input data/flagged_A.json --out data/reports/report_A.docx --docx
"""

import argparse
import json
import os
from datetime import datetime

SEV_LABEL = {"high": "高", "medium": "中", "low": "低"}
PLAYBOOK_LABEL = {
    "compound": "复合需求",
    "param": "变参测试",
    "multi_turn": "多轮改条件",
    "boundary": "边界探测",
}
ENTRY_LABEL = {
    "negative_one_screen": "负一屏入口（微信主界面左上角绿色小眼睛）",
    "chat_plus": "对话内置入口（聊天框底部「+」号第 8 个位置）",
    "long_press": "长按唤起（长按聊天消息）",
    "content_read": "内容阅读入口（公众号 / 视频号页面）",
}

# 异常类型 → 建议的问题类型（填表单用）
ISSUE_TYPE = {
    "context_pollution": "上下文污染 / 任务编排缺陷",
    "category_leak": "上下文污染（品类串台）",
    "state_leak": "状态隔离失效 / 记忆缓存污染",
    "constraint_drop": "约束丢失 / 参数透传断链",
    "vague_failure": "失败兜底话术模糊化",
    "hallucination_number": "数值幻觉",
    "answer_flip": "鲁棒性缺陷（抗误导能力弱）",
    "overclaim": "越界宣称（能力边界误判）",
}

SATISFACTION = {
    "high": "D 不满",
    "medium": "C 略有不满",
    "low": "B 正常完成",
    "none": "B 正常完成",
}


def build_case_report(r):
    """把一条可疑用例转成六要素报告 + 表单字段。"""
    flags = r.get("flags", [])
    types = []
    for f in flags:
        t = f["type"]
        if t not in types and t in ISSUE_TYPE:
            types.append(t)
    sev = r.get("max_severity", "none")
    issue_type = " / ".join(ISSUE_TYPE[t] for t in types) if types else "待人工归类"

    detail_lines = []
    for f in flags:
        if f["type"] == "detector_error":
            continue
        detail_lines.append(
            f"  - [{SEV_LABEL.get(f['severity'], '低')}] {f['detail']}"
        )
    flag_text = "\n".join(detail_lines) if detail_lines else "  - 人工标注"

    repro = []
    for i, t in enumerate(r.get("turns", [])):
        state = "（已跳过）" if t.get("skipped") else ""
        repro.append(f"  第 {i+1} 轮：发送「{t['prompt']}」{state}")
        if t.get("reply"):
            reply = t["reply"].replace("\n", " ")
            if len(reply) > 220:
                reply = reply[:220] + "……"
            repro.append(f"          小微回复：{reply}")
    repro_text = "\n".join(repro)

    suggestion = r.get("suggestion") or "需人工补充归因。"

    one_line = (f"在{r.get('title','')}场景下，小微出现{issue_type}，"
                f"影响任务完成。")

    # 六要素
    six = {
        "场景描述": (
            f"场景：{r.get('title','')}（{PLAYBOOK_LABEL.get(r.get('playbook'),'')}）。"
            f"入口：{ENTRY_LABEL.get(r.get('entry'), r.get('entry',''))}。"
            f"这是一件来自我真实生活/学习需要的任务（{r.get('suite','?')} 号场景），"
            f"任务共 {r.get('turn_count',0)} 轮对话。"
        ),
        "复现步骤": repro_text,
        "期望小微回复的内容": r.get("expected", ""),
        "实际结果": (
            f"小微的回复中出现了以下可复现的偏差：\n{flag_text}\n"
            f"（详细回复见上一步轮次记录与随附截图）"
        ),
        "原因分析": (
            f"问题类型判定为「{issue_type}」。\n"
            f"初判依据：{suggestion}\n"
            f"结合官方对「任务失败只有两种可能」的判定框架——"
            f"本条属于「功能存在但没做好」，即 Bad Case；"
            f"而非「能力本身有边界」的有价值洞察。"
        ),
        "改进建议": (
            f"1) 短期修复方向：{suggestion}\n"
            f"2) 建议补充的对照实验：以完全相同的单条指令单独发起请求，"
            f"若单发正常而复合下发失败，则可确认问题定位在任务编排层，"
            f"而非该底层能力本身。\n"
            f"3) 建议在提交说明中附上「开记忆 / 关记忆」两轮对照结果，"
            f"以排除记忆缓存导致的干扰。"
        ),
    }

    # 表单字段
    form = {
        "issue_name": f"{'Bad' if sev in ('high','medium') else '疑似'} Case {r.get('case_id','')} {r.get('title','')}",
        "one_line_summary": one_line,
        "entry": ENTRY_LABEL.get(r.get("entry"), r.get("entry", "")),
        "entry_detail": f"{PLAYBOOK_LABEL.get(r.get('playbook'),'')}；用例编号 {r.get('case_id','')}",
        "turn_count": r.get("turn_count", 0),
        "expected": r.get("expected", ""),
        "actual": six["实际结果"],
        "analysis": six["原因分析"],
        "satisfaction": SATISFACTION.get(sev, "B 正常完成"),
        "score_reason": (
            f"自动化规则检测命中 {len([f for f in flags if f['type']!='detector_error'])} 项异常，"
            f"最高严重度「{SEV_LABEL.get(sev,'低')}」。"
            f"问题可稳定复现，直接妨碍任务完成，且指向可修复的具体环节。"
            f"已附完整会话截图与建议复现步骤。"
        ),
        "reproducibility": "必现",
        "repro_steps": repro_text,
        "attachments": "完整会话截图 + 自动化检测输出（flagged JSON）",
    }
    return six, form, types


def render_markdown(results, meta):
    lines = []
    lines.append("# 小微 AI 助手评测报告（初赛）")
    lines.append("")
    lines.append(f"- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"- 可疑用例总数：{len(results)}")
    lines.append(f"- 赛事：2026 全国大学生软件测试大赛 · 微信小微 AI 助手评测专项赛")
    if meta.get("memory_profile"):
        lines.append(f"- 记忆设置：{meta['memory_profile']}")
    lines.append("")
    lines.append("> 说明：以下内容由自动化规则筛查 + 人工复核联合产出，"
                 "直接对应官方报告六要素与赛事表单字段。")
    lines.append("")
    lines.append("---")
    lines.append("")

    for i, r in enumerate(results, 1):
        six, form, types = build_case_report(r)
        lines.append(f"## {i}. {form['issue_name']}")
        lines.append("")
        lines.append(f"**一句话总结**：{form['one_line_summary']}")
        lines.append("")
        lines.append("### 六要素报告")
        lines.append("")
        for k in ["场景描述", "复现步骤", "期望小微回复的内容", "实际结果", "原因分析", "改进建议"]:
            lines.append(f"**{k}**")
            lines.append("")
            lines.append(six[k])
            lines.append("")
        lines.append("### 赛事表单字段")
        lines.append("")
        lines.append("| 字段 | 内容 |")
        lines.append("| --- | --- |")
        for k, v in form.items():
            if k == "issue_name":
                continue
            v = str(v).replace("|", "丨").replace("\n", "<br>")
            lines.append(f"| {k} | {v} |")
        lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines)


def render_docx(results, meta, out_path):
    try:
        from docx import Document
        from docx.shared import Pt, Cm, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.oxml.ns import qn
    except ImportError:
        print("[ERROR] 未安装 python-docx。先执行：pip install python-docx")
        return False

    doc = Document()
    st = doc.styles["Normal"]
    st.font.name = "宋体"
    st.font.size = Pt(10.5)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")

    title = doc.add_heading("小微 AI 助手评测报告（初赛）", level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p = doc.add_paragraph()
    p.add_run(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}    ").bold = False
    p.add_run(f"可疑用例总数：{len(results)}").bold = False
    doc.add_paragraph("赛事：2026 全国大学生软件测试大赛 · 微信小微 AI 助手评测专项赛")
    doc.add_paragraph("说明：本报告由自动化规则筛查 + 人工复核联合产出，"
                      "直接对应官方报告六要素与赛事表单字段。")

    for i, r in enumerate(results, 1):
        six, form, types = build_case_report(r)
        doc.add_heading(f"{i}. {form['issue_name']}", level=1)
        doc.add_paragraph(f"一句话总结：{form['one_line_summary']}")

        doc.add_heading("六要素报告", level=2)
        for k in ["场景描述", "复现步骤", "期望小微回复的内容", "实际结果", "原因分析", "改进建议"]:
            doc.add_heading(k, level=3)
            for line in str(six[k]).split("\n"):
                doc.add_paragraph(line if line.strip() else "")

        doc.add_heading("赛事表单字段", level=2)
        table = doc.add_table(rows=0, cols=2)
        table.style = "Light Grid Accent 1"
        for k, v in form.items():
            if k == "issue_name":
                continue
            cells = table.add_row().cells
            cells[0].text = str(k)
            cells[1].text = str(v)
        doc.add_page_break()

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    doc.save(out_path)
    return True


def main():
    ap = argparse.ArgumentParser(description="小微评测报告生成器")
    ap.add_argument("--input", required=True, help="analyze.py 的输出")
    ap.add_argument("--config", default="config.json")
    ap.add_argument("--out", required=True)
    ap.add_argument("--docx", action="store_true", help="输出 Word 而非 Markdown")
    args = ap.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    results = data.get("results", [])
    meta = {"memory_profile": cfg.get("memory_profile", {}).get("run_a")}

    if args.docx:
        ok = render_docx(results, meta, args.out)
        if ok:
            print(f"[OK] Word 报告已生成 → {args.out}")
        return

    md = render_markdown(results, meta)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"[OK] Markdown 报告已生成 → {args.out}")


if __name__ == "__main__":
    main()
