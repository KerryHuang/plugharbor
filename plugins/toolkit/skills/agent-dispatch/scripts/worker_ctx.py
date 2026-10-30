#!/usr/bin/env python3
"""印出某個 claude worker 最後一輪的 context 大小（input＋cache），判斷要不要中途交接。

用法：worker_ctx.py <session id 或前綴>
session id 從 `herdr agent list` 該 worker 的 agent_session.value 取；/clear 後會換新，要重抓。
只讀 transcript 尾端，找不到 session 時 exit 1。
"""
import json
import os
import sys
from pathlib import Path

TAIL_BYTES = 512 * 1024


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) != 2:
        print("用法：worker_ctx.py <session id 或前綴>", file=sys.stderr)
        return 2
    hits = sorted(Path.home().glob(f".claude/projects/*/{sys.argv[1]}*.jsonl"), key=lambda p: p.stat().st_mtime)
    if not hits:
        print(f"找不到 session {sys.argv[1]}", file=sys.stderr)
        return 1
    with open(hits[-1], "rb") as f:
        f.seek(0, os.SEEK_END)
        f.seek(max(0, f.tell() - TAIL_BYTES))
        lines = f.read().decode("utf-8", "ignore").splitlines()
    for line in reversed(lines):
        try:
            u = (json.loads(line).get("message") or {}).get("usage")
        except ValueError:
            continue
        if isinstance(u, dict) and "input_tokens" in u:
            n = sum(u.get(k) or 0 for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
            print(n)
            return 0
    print("transcript 裡沒有 usage", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
