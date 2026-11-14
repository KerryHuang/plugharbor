#!/usr/bin/env python3
"""SessionStart（compact）hook：context 壓縮後提醒 agent 沿用使用者指示的語言與格式。
壓縮摘要與 harness 續接提示常是英文，會把回覆語言帶偏（2026-11-11 壓縮後連續多輪改用英文）。
文字規則擋不住，所以在壓縮後主動注入一次。

另比對本 session 載入的 toolkit 版本與已安裝版本：plugin 只在 session 開始時載入，
長 session 拿不到之後的修正（2026-11 一個自動駕駛 session 開了 9 天，一直跑 0.13.0，漏了 8 版）。

壓縮過就提示換新的時機與做法：在 herdr 內 session 能自己 /clear、/reload-plugins 再接回（handoff skill）。
"""
import json
import os
import sys
from pathlib import Path

MSG = ("[toolkit] context 剛壓縮。回覆語言（含工具呼叫的說明文字）、回合結尾格式、提問方式一律照使用者的 CLAUDE.md 與 rules；"
       "壓縮摘要與續接提示用什麼語言，不代表要換語言。")


def handoff_note() -> str:
    """任務未完時換新的時機與做法；在 herdr 內才能自己換。"""
    when = "\n[toolkit] 任務還沒做完的話，停在沒有 subagent、背景工作、CI 等待的點時換新 session 接手："
    root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if os.environ.get("HERDR_ENV") == "1" and root:
        skill = Path(root, "skills", "handoff", "SKILL.md")
        return (when + f"使用者在場先用 AskUserQuestion 問一次，同意或無人值守就讀 {skill} 照做"
                "（自動駕駛改照它自己的「換新 session」）。任務已完成就不換。")
    return when + "告一段落時建議使用者打 /handoff。任務已完成就不換。"


def version_tuple(v: str):
    try:
        return tuple(int(x) for x in v.split("."))
    except ValueError:
        return None


def drift_note() -> str:
    """載入版落後已安裝版就回一句提醒；讀不到或判斷不了就回空字串（fail-open）。"""
    root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if not root:
        return ""
    loaded = Path(root).name
    reg = Path.home() / ".claude" / "plugins" / "installed_plugins.json"
    try:
        data = json.loads(reg.read_text(encoding="utf-8"))
        entries = data.get("plugins", {}).get("toolkit@" + Path(root).parent.parent.name, [])
        installed = entries[0]["version"]
    except (OSError, ValueError, KeyError, IndexError, TypeError, AttributeError):
        return ""
    a, b = version_tuple(loaded), version_tuple(installed)
    if a is None or b is None or a >= b:
        return ""
    return (f"\n[toolkit] 本 session 載入的 toolkit 是 {loaded}，已安裝的是 {installed}：plugin 只在 session 開始時載入，"
            "之後的修正這個 session 拿不到。")


def main():
    out = json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart",
                                             "additionalContext": MSG + drift_note() + handoff_note()}},
                     ensure_ascii=False)
    sys.stdout.buffer.write(out.encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
