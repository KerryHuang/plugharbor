#!/usr/bin/env python3
"""SessionStart hook：讓 codex／agy 唯讀看到 Claude Code 的 auto-memory 索引（plugharbor#72）。

Claude 自己會載入 MEMORY.md，所以 transcript_path 在 ~/.claude/ 底下（＝Claude）時不輸出。
從 cwd 往上找 ~/.claude/projects/<slug>/memory/MEMORY.md，slug＝絕對路徑的非英數字元換成 `-`（Claude 的命名）；
只取前 200 行（同 Claude 的截斷）。找不到或任何錯誤都不輸出、exit 0。
pi 不走 hook，由 pi/memory.ts 以同樣規則注入。
"""
import json
import os
import re
import sys

MAX_LINES = 200
HEAD = ("[toolkit] 以下是 Claude Code 為這個專案記下的 auto-memory 索引（唯讀，來源 {path}）。"
        "每行指向同目錄的一個 topic 檔，跟當前工作相關時再讀原檔；"
        "記憶是寫下當時的觀察，動手前先對照現況。不要新增、修改或刪除這些記憶檔。\n\n")


def slug(path):
    return re.sub(r"[^A-Za-z0-9]", "-", path)


def find_index(cwd, home):
    base = os.path.join(home, ".claude", "projects")
    cur = os.path.abspath(cwd)
    while True:
        f = os.path.join(base, slug(cur), "memory", "MEMORY.md")
        if os.path.isfile(f):
            return f
        parent = os.path.dirname(cur)
        if parent == cur:
            return None
        cur = parent


def is_claude(payload, home):
    t = payload.get("transcript_path")
    if not isinstance(t, str) or not t:
        return False
    norm = os.path.normcase(os.path.abspath(t))
    return norm.startswith(os.path.normcase(os.path.join(home, ".claude")) + os.sep)


def main():
    try:
        raw = sys.stdin.buffer.read().decode("utf-8") if not sys.stdin.isatty() else ""
        payload = json.loads(raw) if raw.strip() else {}
        if not isinstance(payload, dict):
            payload = {}
        home = os.path.expanduser("~")
        if is_claude(payload, home):
            return 0
        # agy 的 payload 沒有 cwd，改給 workspacePaths；注入格式也不同（injectSteps，見 antigravity.google/docs/hooks.md）
        agy = isinstance(payload.get("workspacePaths"), list)
        ws = payload.get("workspacePaths") if agy else None
        f = find_index(payload.get("cwd") or (ws[0] if ws else None) or os.getcwd(), home)
        if not f:
            return 0
        with open(f, encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()[:MAX_LINES]
        if not any(l.strip() for l in lines):
            return 0
        text = HEAD.format(path=f.replace("\\", "/")) + "\n".join(lines)
        body = ({"injectSteps": [{"systemMessage": {"systemMessage": text}}]} if agy else
                {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": text}})
        out = json.dumps(body, ensure_ascii=False)
        sys.stdout.buffer.write(out.encode("utf-8"))
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
