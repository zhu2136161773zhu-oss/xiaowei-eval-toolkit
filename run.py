# -*- coding: utf-8 -*-
"""
小微 AI 助手评测 —— 采集驱动器

两条采集路径：

  manual  半自动（零依赖，立刻可用）
      脚本把指令写入剪贴板 → 你在手机/PC 微信里粘贴发给小微
      → 小微回复后你复制 → 脚本读剪贴板自动落盘
      适合：没有 ADB、只想先把用例跑起来

  uia2    全自动（需要安卓手机 + USB 调试）
      通过 uiautomator2 直接驱动手机微信：找入口 → 输入 → 等回复 → 截图落盘
      适合：批量跑变参测试、上万条筛选

红线保护：QPM 硬上限 16（官方明令），默认 8；超过会自动降速并告警。

用法：
  python run.py --mode manual --cases cases/A.json --out data/raw_A.jsonl
  python run.py --mode uia2 --cases cases/A.json --out data/raw_A.jsonl --serial <设备号>
"""

import argparse
import json
import os
import random
import subprocess
import sys
import time
from datetime import datetime

# ---------------------------------------------------------------- 剪贴板
def set_clipboard(text):
    """写入 Windows 剪贴板（纯 ctypes，无需 pywin32）。"""
    import ctypes
    from ctypes import wintypes

    CF_UNICODETEXT = 13
    GMEM_MOVEABLE = 0x0002

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    # 显式声明返回类型，避免 64 位下指针被截断
    kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
    kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalUnlock.restype = wintypes.BOOL
    kernel32.GlobalFree.argtypes = [wintypes.HGLOBAL]
    user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
    user32.SetClipboardData.restype = wintypes.HANDLE
    user32.GetClipboardData.argtypes = [wintypes.UINT]
    user32.GetClipboardData.restype = wintypes.HANDLE

    if not user32.OpenClipboard(0):
        # 剪贴板可能被其他程序占用，稍等重试
        for _ in range(5):
            time.sleep(0.2)
            if user32.OpenClipboard(0):
                break
        else:
            raise RuntimeError("无法打开剪贴板（可能被其他程序占用），请重试")

    try:
        user32.EmptyClipboard()
        data = text + "\0"
        size = len(data) * ctypes.sizeof(ctypes.c_wchar)
        handle = kernel32.GlobalAlloc(GMEM_MOVEABLE, size)
        if not handle:
            raise RuntimeError("GlobalAlloc 失败，内存不足")
        locked = kernel32.GlobalLock(handle)
        if not locked:
            kernel32.GlobalFree(handle)
            raise RuntimeError("GlobalLock 失败")
        try:
            ctypes.memmove(locked, ctypes.create_unicode_buffer(data), size)
        finally:
            kernel32.GlobalUnlock(handle)
        if not user32.SetClipboardData(CF_UNICODETEXT, handle):
            kernel32.GlobalFree(handle)
            raise RuntimeError("SetClipboardData 失败")
    finally:
        user32.CloseClipboard()


def get_clipboard():
    """读取 Windows 剪贴板文本。"""
    import ctypes
    from ctypes import wintypes

    CF_UNICODETEXT = 13
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalUnlock.restype = wintypes.BOOL

    if not user32.OpenClipboard(0):
        return ""
    try:
        handle = user32.GetClipboardData(CF_UNICODETEXT)
        if not handle:
            return ""
        locked = kernel32.GlobalLock(handle)
        if not locked:
            return ""
        try:
            return ctypes.c_wchar_p(locked).value or ""
        finally:
            kernel32.GlobalUnlock(handle)
    finally:
        user32.CloseClipboard()


# ---------------------------------------------------------------- 限速器
class RateLimiter:
    def __init__(self, qpm, min_interval, max_interval, jitter, ceiling=16):
        if qpm > ceiling:
            print(f"[WARN] QPM={qpm} 超过赛事红线 {ceiling}，已强制降为 {ceiling}")
            qpm = ceiling
        self.min_interval = max(min_interval, 60.0 / qpm)
        self.max_interval = max(max_interval, self.min_interval)
        self.jitter = jitter
        self.sent = 0
        self.last = 0.0

    def wait(self):
        now = time.time()
        gap = self.min_interval + random.uniform(0, self.jitter)
        elapsed = now - self.last
        if self.sent > 0 and elapsed < gap:
            time.sleep(gap - elapsed)
        self.last = time.time()
        self.sent += 1


# ---------------------------------------------------------------- 手动模式
def run_manual(cases, cfg, out_path, entries):
    limiter = RateLimiter(
        cfg["limits"]["qpm"],
        cfg["limits"]["min_interval_sec"],
        cfg["limits"]["max_interval_sec"],
        cfg["limits"].get("jitter_sec", 3.0),
        cfg["limits"].get("qpm_hard_ceiling", 16),
    )
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    fout = open(out_path, "a", encoding="utf-8")

    session_id = datetime.now().strftime("session_%Y%m%d_%H%M%S")
    print("=" * 68)
    print(f"半自动采集模式   会话 {session_id}")
    print(f"用例文件: {cases['count']} 条   入口: {cases['entry_label']}")
    print("=" * 68)
    print("操作说明：")
    print("  1) 脚本把一条指令放进剪贴板")
    print("  2) 切到微信 → 点开小微 → Ctrl+V 粘贴 → 发送")
    print("  3) 等小微答完 → 复制它的回复")
    print("  4) 切回本窗口按 Ctrl+V 再回车，脚本会自动读走剪贴板内容")
    print("     （也可以直接粘贴文本后回车；输入 SKIP 跳过 / QUIT 结束）")
    print("=" * 68)

    total_turn = sum(len(c["turns"]) for c in cases["cases"])
    done_turn = 0
    for case in cases["cases"]:
        print("\n" + "-" * 68)
        print(f"[{case['case_id']}] {case['title']}   ({case['playbook']})")
        print(f"  期望: {case['expected']}")
        if case.get("checkpoints"):
            print(f"  观察点: {' / '.join(case['checkpoints'])}")
        print("-" * 68)

        turns_out = []
        for ti, prompt in enumerate(case["turns"]):
            done_turn += 1
            print(f"\n>>> 第 {ti+1}/{len(case['turns'])} 轮  (全局进度 {done_turn}/{total_turn})")
            print(f"    指令: {prompt}")
            limiter.wait()
            try:
                set_clipboard(prompt)
            except Exception as e:
                print(f"    [剪贴板写入失败] {e}")
                continue
            print("    ↑ 指令已在剪贴板，请粘贴给小微")
            raw = input("    ← 复制小微回复后回车（可直接粘贴；SKIP 跳过 / QUIT 结束）：").strip()

            # 若用户只是按了回车（没粘贴文本），尝试自动读剪贴板
            if raw == "":
                try:
                    clip = get_clipboard().strip()
                except Exception:
                    clip = ""
                if clip and clip != prompt:
                    raw = clip
                    print(f"    ✓ 已自动读走剪贴板（{len(raw)} 字）")
                else:
                    print("    [未获取到内容，本轮记为空]")
                    raw = ""

            if raw.upper() == "QUIT":
                fout.write(json.dumps({
                    "session_id": session_id, "case_id": case["case_id"],
                    "suite": case["suite"], "playbook": case["playbook"],
                    "title": case["title"], "entry": case["entry"],
                    "expected": case["expected"],
                    "checkpoints": case.get("checkpoints", []),
                    "turns": turns_out, "aborted": True,
                    "ts": datetime.now().isoformat(timespec="seconds"),
                }, ensure_ascii=False) + "\n")
                fout.flush()
                print("\n已保存并结束。")
                fout.close()
                return
            if raw.upper() == "SKIP":
                print("    [跳过本轮]")
                turns_out.append({
                    "index": ti, "prompt": prompt, "reply": "",
                    "skipped": True, "ts": datetime.now().isoformat(timespec="seconds"),
                })
                continue
            turns_out.append({
                "index": ti, "prompt": prompt, "reply": raw,
                "skipped": False, "ts": datetime.now().isoformat(timespec="seconds"),
            })
            print(f"    ✓ 已记录 {len(raw)} 字")

        fout.write(json.dumps({
            "session_id": session_id,
            "case_id": case["case_id"],
            "suite": case["suite"],
            "playbook": case["playbook"],
            "title": case["title"],
            "entry": case["entry"],
            "expected": case["expected"],
            "checkpoints": case.get("checkpoints", []),
            "turns": turns_out,
            "aborted": False,
            "ts": datetime.now().isoformat(timespec="seconds"),
        }, ensure_ascii=False) + "\n")
        fout.flush()
        print(f"    ✓ 用例 {case['case_id']} 已落盘")

    fout.close()
    print(f"\n[OK] 全部完成 → {out_path}")


# ---------------------------------------------------------------- 安卓自动化
def run_uia2(cases, cfg, out_path, serial=None, max_cases=None):
    try:
        import uiautomator2 as u2
    except ImportError:
        print("[ERROR] 未安装 uiautomator2。先执行：")
        print("        pip install uiautomator2")
        print("        然后手机开启「开发者选项 → USB 调试」并连接数据线")
        sys.exit(1)

    d = u2.connect(serial) if serial else u2.connect()
    print(f"[OK] 已连接设备: {d.info.get('productName')} / Android {d.info.get('sdkInt')}")

    d_cfg = cfg["drivers"]["uia2"]
    entry = d_cfg["wechat_entry"]
    pkg = d_cfg["package_name"]
    limiter = RateLimiter(
        cfg["limits"]["qpm"],
        cfg["limits"]["min_interval_sec"],
        cfg["limits"]["max_interval_sec"],
        cfg["limits"].get("jitter_sec", 3.0),
        cfg["limits"].get("qpm_hard_ceiling", 16),
    )

    shot_dir = os.path.join(os.path.dirname(out_path) or ".", "shots")
    os.makedirs(shot_dir, exist_ok=True)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    fout = open(out_path, "a", encoding="utf-8")

    def open_xiaowei():
        """回到微信首页并点开小微入口。"""
        d.app_start(pkg, stop=True)
        time.sleep(3.5)
        w, h = d.window_size()
        x = int(w * entry["ratio_x"])
        y = int(h * entry["ratio_y"])
        d.click(x, y)
        time.sleep(2.5)

    def read_replies(limit=6):
        """从 hierarchy XML 里捞出小微的回复文本。"""
        xml = d.dump_hierarchy()
        exclude = set(d_cfg["reply_region"].get("exclude_resource_ids", []))
        texts = []
        for node in xml.split("node ")[1:]:
            if "text=" not in node:
                continue
            try:
                txt = node.split('text="', 1)[1].split('"', 1)[0]
                rid = node.split('resource-id="', 1)[1].split('"', 1)[0] if 'resource-id="' in node else ""
            except IndexError:
                continue
            if not txt.strip() or rid in exclude:
                continue
            if node.count('text="') and 'class="android.widget.TextView"' in node:
                texts.append(txt.strip())
        return texts[-limit:]

    def send_text(text):
        """优先 set_text；中文失败则走剪贴板粘贴。"""
        try:
            d.send_keys(text, clear=True)
        except Exception:
            try:
                set_clipboard(text)
            except Exception:
                pass
            # 长按输入框 → 粘贴
            rid = d_cfg["input_box"].get("resource_id")
            try:
                sel = d(resourceId=rid)
            except Exception:
                sel = None
            if sel:
                sel.long_click()
                time.sleep(0.8)
                try:
                    d(text="粘贴").click(timeout=2)
                except Exception:
                    sel.set_text(text)
            else:
                sel = d(textContains=cfg.get("_input_hint", "发送"))
                sel.set_text(text)

    session_id = datetime.now().strftime("session_%Y%m%d_%H%M%S")
    total_turn = sum(len(c["turns"]) for c in cases["cases"])
    done_turn = 0
    stop = False

    for case in cases["cases"][:max_cases] if max_cases else cases["cases"]:
        if stop:
            break
        print(f"\n[{case['case_id']}] {case['title']}")
        turns_out = []
        try:
            open_xiaowei()
            for ti, prompt in enumerate(case["turns"]):
                done_turn += 1
                limiter.wait()
                print(f"  → ({done_turn}/{total_turn}) {prompt[:40]}...")
                send_text(prompt)
                d.press("enter")
                time.sleep(2.0)
                # 等回复：轮询直到有新文本出现
                deadline = time.time() + cfg["limits"]["request_timeout_sec"]
                before = read_replies(6)
                replies = before
                while time.time() < deadline:
                    time.sleep(3)
                    replies = read_replies(6)
                    if len(replies) > len(before):
                        break
                reply = replies[-1] if replies else ""
                shot = os.path.join(shot_dir, f"{case['case_id']}_t{ti+1}.png")
                try:
                    d.screenshot(shot)
                except Exception:
                    shot = ""
                turns_out.append({
                    "index": ti, "prompt": prompt, "reply": reply,
                    "screenshot": shot, "skipped": False,
                    "ts": datetime.now().isoformat(timespec="seconds"),
                })
                print(f"    ✓ 回复 {len(reply)} 字  截图 {os.path.basename(shot)}")
        except Exception as e:
            print(f"  [ERROR] {case['case_id']} 采集异常: {e}")
            stop = True

        fout.write(json.dumps({
            "session_id": session_id, "case_id": case["case_id"],
            "suite": case["suite"], "playbook": case["playbook"],
            "title": case["title"], "entry": case["entry"],
            "expected": case["expected"],
            "checkpoints": case.get("checkpoints", []),
            "turns": turns_out, "aborted": False,
            "ts": datetime.now().isoformat(timespec="seconds"),
        }, ensure_ascii=False) + "\n")
        fout.flush()

    fout.close()
    print(f"\n[OK] 采集完成 → {out_path}   截图 → {shot_dir}")


def run_loop(cases, cfg, out_path, rounds=None, suite_filter=None):
    """
    持续提问模式：把选中的用例反复循环提问，用于「同一指令反复复现」，
    验证官方第五条标准里的「能稳定复现」，也用于观察非必现（偶现）问题的出现频率。

    与 run_manual 的区别：不逐条确认，把整个批次连续问完，中途可随时 Ctrl+C 停。
    """
    limiter = RateLimiter(
        cfg["limits"]["qpm"],
        cfg["limits"]["min_interval_sec"],
        cfg["limits"]["max_interval_sec"],
        cfg["limits"].get("jitter_sec", 3.0),
        cfg["limits"].get("qpm_hard_ceiling", 16),
    )
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    fout = open(out_path, "a", encoding="utf-8")
    session_id = datetime.now().strftime("loop_%Y%m%d_%H%M%S")

    pool = [c for c in cases["cases"]
            if (suite_filter is None or c["suite"] == suite_filter)]
    if not pool:
        print("[ERROR] 没有匹配的用例")
        return

    print("=" * 68)
    print(f"持续提问模式   会话 {session_id}")
    print(f"用例池 {len(pool)} 条   计划轮次 {rounds or '不限'}   QPM 上限 {limiter.min_interval:.1f}s/条")
    print("=" * 68)
    print("每条指令会进入剪贴板 → 你粘贴给小微 → 复制回复 → 回本窗口按 Ctrl+V 回车")
    print("Ctrl+C 可随时中断，已采集内容会自动保存。")
    print("=" * 68)

    r = 0
    try:
        while rounds is None or r < rounds:
            r += 1
            print(f"\n{'=' * 68}\n第 {r} 轮循环")
            for case in pool:
                print(f"\n>>> [{case['case_id']}] {case['title']}")
                for ti, prompt in enumerate(case["turns"]):
                    limiter.wait()
                    try:
                        set_clipboard(prompt)
                    except Exception as e:
                        print(f"  [剪贴板失败] {e}")
                        continue
                    print(f"  指令({ti+1}/{len(case['turns'])}): {prompt}")
                    print("  ↑ 已放入剪贴板")
                    raw = input("  ← 复制回复后 Ctrl+V 回车（空回车=读剪贴板 / SKIP / QUIT）：").strip()
                    if raw.upper() == "QUIT":
                        raise KeyboardInterrupt
                    if raw == "":
                        try:
                            clip = get_clipboard().strip()
                        except Exception:
                            clip = ""
                        raw = clip if clip and clip != prompt else ""
                    if raw.upper() == "SKIP":
                        continue
                    fout.write(json.dumps({
                        "session_id": session_id, "case_id": case["case_id"],
                        "suite": case["suite"], "playbook": case["playbook"],
                        "title": case["title"], "entry": case["entry"],
                        "expected": case["expected"],
                        "checkpoints": case.get("checkpoints", []),
                        "loop_round": r,
                        "turns": [{"index": ti, "prompt": prompt, "reply": raw,
                                   "skipped": False,
                                   "ts": datetime.now().isoformat(timespec="seconds")}],
                        "aborted": False,
                        "ts": datetime.now().isoformat(timespec="seconds"),
                    }, ensure_ascii=False) + "\n")
                    fout.flush()
    except KeyboardInterrupt:
        print("\n已中断，正在保存…")
    finally:
        fout.close()
        print(f"[OK] 采集完成 → {out_path}")


# ---------------------------------------------------------------- 入口
def main():
    ap = argparse.ArgumentParser(description="小微评测采集驱动器")
    ap.add_argument("--mode", default="manual", choices=["manual", "uia2", "loop"])
    ap.add_argument("--cases", required=True, help="用例 JSON（gen_cases.py 产出）")
    ap.add_argument("--config", default="config.json")
    ap.add_argument("--out", required=True, help="采集结果 JSONL")
    ap.add_argument("--serial", default=None, help="uia2 模式下的设备序列号")
    ap.add_argument("--max-cases", type=int, default=None, help="本次最多跑多少条")
    ap.add_argument("--rounds", type=int, default=None, help="loop 模式：循环轮次")
    ap.add_argument("--suite", default=None, help="loop 模式：只跑某个 suite")
    args = ap.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    with open(args.cases, "r", encoding="utf-8") as f:
        cases = json.load(f)

    print(f"用例 {cases['count']} 条 | 入口 {cases['entry_label']} | 模式 {args.mode}")

    if args.mode == "manual":
        run_manual(cases, cfg, args.out, cases.get("entry_label"))
    elif args.mode == "loop":
        run_loop(cases, cfg, args.out, args.rounds, args.suite)
    else:
        run_uia2(cases, cfg, args.out, args.serial, args.max_cases)


if __name__ == "__main__":
    main()
