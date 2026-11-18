#!/usr/bin/env python3
"""Stop hook：在 Herdr.app 內把 Claude 的 session 標題同步成分頁名稱。

Herdr.app 分頁顯示的是分頁自己的 name（開 Claude 時多半固定成「Claude Code」、沒名字顯示編號），
不跟 terminal title 走；Claude 的標題（內建 ai-title 或 /rename）只寫進 terminal title。
每回合結束讀 `hc get` 的 title，用 `herdr-app do tab.rename` 寫進分頁名稱。

不覆寫手動命名：分頁名稱是預設值（空、編號、「Claude Code」）或等於上次本 hook 寫的才改。
分頁有多個 terminal（worker 切在旁邊）時只認第一個，worker 不改主分頁。
不在 Herdr.app 內（沒有 HC_TERMINAL_ID）或指令失敗，一律安靜結束。
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

DEFAULT_NAMES = {"", "Claude Code"}
LEADING_GLYPHS = re.compile(r"^[^\w\[(（「【]+")
MAX_TITLE = 80
STATE = Path(os.path.expanduser("~/.claude/state/herdr-tab-title.json"))


def run_json(argv):
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=3, encoding="utf-8")
    except (OSError, subprocess.SubprocessError):
        return None
    if p.returncode != 0:
        return None
    try:
        return json.loads(p.stdout)
    except ValueError:
        return None


def find_tab(ls, tab_id):
    for space in (ls or {}).get("spaces") or []:
        for tab in space.get("tabs") or []:
            if tab.get("id") == tab_id:
                return tab
    return None


def load_state():
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def main():
    term = os.environ.get("HC_TERMINAL_ID")
    if not term:
        return
    info = run_json(["hc", "get", "--json", term])
    if not info:
        return
    title = LEADING_GLYPHS.sub("", (info.get("title") or "").strip()).strip()
    tab_id = (info.get("labels") or {}).get("herdr.tab")
    if not title or title in DEFAULT_NAMES or len(title) > MAX_TITLE or not tab_id:
        return
    tab = find_tab(run_json(["herdr-app", "ls"]), tab_id)
    if not tab:
        return
    terms = [t.get("terminal") for t in tab.get("terminals") or []]
    if terms and terms[0] != term:
        return
    name = (tab.get("name") or "").strip()
    state = load_state()
    if name == title:
        return
    if name not in DEFAULT_NAMES and not name.isdigit() and name != state.get(tab_id):
        return  # 使用者手動改過
    if run_json(["herdr-app", "do", "tab.rename", "--id", tab_id, "--name", title]) is None:
        return
    state[tab_id] = title
    try:
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


if __name__ == "__main__":
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdin.read()
    main()
