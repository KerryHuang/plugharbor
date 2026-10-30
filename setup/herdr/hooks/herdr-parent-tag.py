#!/usr/bin/env python3
"""Pre/PostToolUse hook for Bash（user 層）：Claude 在 herdr 裡開的 pane 標上 launcher，側欄才會把 worker 掛在它底下。

Claude 開 worker 的寫法很多（dispatch-worker 的 pane split、自己組 tab create＋agent start、變數帶 pane id），
看指令解析抓不全，所以改成比對：Pre 記下現有 pane，Post 把多出來的 pane 寫 parent_pane=$HERDR_PANE_ID，
再呼叫側欄 plugin（plugharbor.sidebar）的 refresh 動作重算樹（寫 metadata 本身不會觸發 plugin）。
只在 HERDR_ENV=1 且指令真的呼叫開 pane 的 herdr 子指令時動作；任何失敗都放行，不擋 Bash。
只認「指令提到 herdr」會誤掛：grep／heredoc 裡出現 herdr 字樣的指令（subagent 也繼承 HERDR_PANE_ID）跑的那幾秒，
使用者自己開的 tab 也會被當成這個 session 的 worker。
限制：run_in_background 的指令 Post 會先回來，那時還沒開出的 pane 標不到。
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

SOURCE = "claude-parent-tag"
SNAP_DIR = Path(tempfile.gettempdir()) / "herdr-parent-tag"
SPAWN = re.compile(r"\bherdr\b.*?\b(pane\s+split|tab\s+create|workspace\s+create|worktree\s+(create|open))\b")


def herdr(*args: str) -> str:
    out = subprocess.run(["herdr", *args], capture_output=True, text=True, encoding="utf-8", timeout=10)
    if out.returncode != 0:
        raise RuntimeError(f"herdr {' '.join(args[:2])}: {out.stderr.strip() or out.stdout.strip()}")
    return out.stdout


def panes() -> list[str]:
    return [p["pane_id"] for p in json.loads(herdr("pane", "list"))["result"]["panes"]]


def main() -> int:
    sys.stdin.reconfigure(encoding="utf-8")
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    me = os.environ.get("HERDR_PANE_ID")
    cmd = (payload.get("tool_input") or {}).get("command") or ""
    if os.environ.get("HERDR_ENV") != "1" or not me or not SPAWN.search(cmd):
        return 0
    snap = SNAP_DIR / f"{payload.get('tool_use_id', 'none')}.json"
    try:
        if payload.get("hook_event_name") == "PreToolUse":
            SNAP_DIR.mkdir(exist_ok=True)
            snap.write_text(json.dumps(panes()), encoding="utf-8")
            return 0
        if not snap.exists():
            return 0
        before = set(json.loads(snap.read_text(encoding="utf-8")))
        snap.unlink()
        new = [p for p in panes() if p not in before and p != me]
        for p in new:
            herdr("pane", "report-metadata", p, "--source", SOURCE, "--token", f"parent_pane={me}")
        if new:
            # action 依平台分開宣告（herdr-plugin.toml），Windows 呼叫 refresh 會回 platform_unsupported
            herdr("plugin", "action", "invoke", "plugharbor.sidebar.refresh-windows" if os.name == "nt" else "plugharbor.sidebar.refresh")
    except Exception as e:  # 只影響側欄顯示：記一行到 stderr 後放行
        print(f"herdr-parent-tag: {e}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
