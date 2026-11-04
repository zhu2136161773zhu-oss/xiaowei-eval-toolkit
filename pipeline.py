# -*- coding: utf-8 -*-
"""
小微 AI 助手评测 —— 一键流水线

把「生成用例 → 采集 → 自动筛查 → 出报告」串成一条命令。

用法：
  # 只生成用例
  python pipeline.py gen --suite A

  # 半自动采集（你手动粘贴，脚本负责落盘）
  python pipeline.py run --suite A --mode manual

  # 全自动采集（安卓手机 + USB 调试）
  python pipeline.py run --suite A --mode uia2 --serial <设备号>

  # 只做筛查 + 出报告（对已有 raw_*.jsonl）
  python pipeline.py report --raw data/raw_A.jsonl --suite A
"""

import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def sh(cmd, **kw):
    print(f"\n$ {' '.join(cmd)}")
    r = subprocess.run(cmd, cwd=HERE, **kw)
    if r.returncode != 0:
        print(f"[FAIL] 命令退出码 {r.returncode}")
        sys.exit(r.returncode)
    return r


def main():
    ap = argparse.ArgumentParser(description="小微评测一键流水线")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_gen = sub.add_parser("gen", help="生成用例")
    p_gen.add_argument("--suite", default="all")
    p_gen.add_argument("--playbook", default="all")
    p_gen.add_argument("--entry", default="negative_one_screen")

    p_run = sub.add_parser("run", help="采集")
    p_run.add_argument("--suite", default="all")
    p_run.add_argument("--playbook", default="all")
    p_run.add_argument("--entry", default="negative_one_screen")
    p_run.add_argument("--mode", default="manual", choices=["manual", "uia2", "loop"])
    p_run.add_argument("--serial", default=None)
    p_run.add_argument("--rounds", type=int, default=None, help="loop 模式循环轮次")

    p_rep = sub.add_parser("report", help="筛查 + 出报告")
    p_rep.add_argument("--raw", required=True, help="采集结果 JSONL")
    p_rep.add_argument("--suite", default="all")
    p_rep.add_argument("--docx", action="store_true")

    args = ap.parse_args()
    tag = args.suite if args.suite != "all" else "all"
    cases_path = f"cases/{tag}.json"
    raw_path = f"data/raw_{tag}.jsonl"
    flagged_path = f"data/flagged_{tag}.json"

    if args.cmd == "gen":
        sh([sys.executable, "gen_cases.py", "--suite", args.suite,
            "--playbook", args.playbook, "--entry", args.entry, "--out", cases_path])

    elif args.cmd == "run":
        if not os.path.exists(os.path.join(HERE, cases_path)):
            sh([sys.executable, "gen_cases.py", "--suite", args.suite,
                "--playbook", args.playbook, "--entry", args.entry, "--out", cases_path])
        cmd = [sys.executable, "run.py", "--mode", args.mode,
               "--cases", cases_path, "--config", "config.json", "--out", raw_path]
        if args.serial:
            cmd += ["--serial", args.serial]
        if args.rounds:
            cmd += ["--rounds", str(args.rounds)]
        if args.mode == "loop" and args.suite != "all":
            cmd += ["--suite", args.suite]
        sh(cmd)

    elif args.cmd == "report":
        sh([sys.executable, "analyze.py", "--input", args.raw,
            "--config", "config.json", "--out", flagged_path])
        out = f"data/reports/report_{tag}.docx" if args.docx else f"data/reports/report_{tag}.md"
        cmd = [sys.executable, "report.py", "--input", flagged_path,
               "--config", "config.json", "--out", out]
        if args.docx:
            cmd.append("--docx")
        sh(cmd)
        print(f"\n[完成] 报告 → {out}")


if __name__ == "__main__":
    main()
