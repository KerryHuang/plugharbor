#!/usr/bin/env python3
"""Stop hook：主 session 的 context 超過門檻時，提醒使用者換題先 /clear。

每輪重送整份 context，長 session 換題不清會每輪重讀前一件事（2026-10-21 /usage：
「Start fresh when you switch tasks」佔近 24h 用量 62%）。只用 systemMessage 給人看，
不進 Claude 的 context；不擋停止。超過 THRESHOLD 後每多長 STEP 才再提醒一次。
任何例外吞掉、exit 0（hook fail-open：提醒失效不該擋住停止）。
"""
import json
import os
import sys
from pathlib import Path

THRESHOLD = 200_000
STEP = 50_000
TAIL_BYTES = 512 * 1024
STATE_DIR = Path(os.path.expanduser("~/.claude")) / "context-reminder"


def last_context(transcript):
    """transcript 尾端最後一筆主鏈 assistant 的 context 大小（input＋cache）。"""
    with open(transcript, "rb") as f:
        f.seek(0, os.SEEK_END)
        f.seek(max(0, f.tell() - TAIL_BYTES))
        lines = f.read().decode("utf-8", "ignore").splitlines()
    for line in reversed(lines):
        if '"usage"' not in line:
            continue
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get("type") != "assistant" or d.get("isSidechain"):
            continue
        u = (d.get("message") or {}).get("usage") or {}
        return (u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0)
                + u.get("cache_creation_input_tokens", 0))
    return 0


def main():
    sys.stdin.reconfigure(encoding="utf-8")
    payload = json.load(sys.stdin)
    sid = payload.get("session_id") or ""
    transcript = payload.get("transcript_path") or ""
    if not sid or not os.path.isfile(transcript):
        return
    ctx = last_context(transcript)
    state = STATE_DIR / sid
    if ctx < THRESHOLD:
        state.unlink(missing_ok=True)   # compact 後掉回門檻下，再長上來要重新提醒
        return
    bucket = (ctx - THRESHOLD) // STEP
    try:
        last = int(state.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        last = -1
    if bucket <= last:
        return
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state.write_text(str(bucket), encoding="utf-8")
    msg = ("context %dK：每輪都會整份重送。要換主題就先 /rename 再 /clear"
           "（之後可 /resume 找回）；同一件事還要接續，先跑 /handoff 落交接檔再 /clear。") % (ctx // 1000)
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps({"systemMessage": msg}, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
