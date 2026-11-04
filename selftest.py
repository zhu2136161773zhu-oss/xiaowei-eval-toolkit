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
    checks = [check_syntax, check_cases, check_analyzer, check_report]
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
