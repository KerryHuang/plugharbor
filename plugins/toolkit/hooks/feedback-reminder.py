#!/usr/bin/env python3
"""SessionStart hook：回饋佇列積到門檻就提醒跑 /feedback-review。

門檻：未處理 ≥ COUNT_THRESHOLD 筆，或佇列非空且距上次回顧 ≥ DAYS_THRESHOLD 天。
queue.jsonl 留下的都是未處理（已處理的由 skill 搬到 archive.jsonl）；
上次回顧時間在 last-review（skill 寫入），不存在就以最早一筆佇列時間起算。
沒達門檻不輸出；任何例外吞掉、exit 0。
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

FEEDBACK = Path(os.path.expanduser("~/.claude")) / "feedback-loop"
COUNT_THRESHOLD = 10
DAYS_THRESHOLD = 7


def _parse(ts):
    dt = datetime.fromisoformat(str(ts).strip())
    return dt if dt.tzinfo else dt.astimezone()


def main():
    text = ""
    # processing 檔是 /feedback-review 歸檔中斷時留下的，裡面一樣是未處理
    for name in ("queue.jsonl", "queue.processing.jsonl"):
        f = FEEDBACK / name
        if f.exists():
            text += f.read_text(encoding="utf-8", errors="replace") + "\n"
    stamps = []
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            stamps.append(_parse(json.loads(line)["ts"]))
        except (ValueError, KeyError, TypeError, AttributeError):
            stamps.append(None)   # 壞列仍算一筆未處理
    n = len(stamps)
    if n == 0:
        return
    now = datetime.now().astimezone()
    last = FEEDBACK / "last-review"
    try:
        since, label = _parse(last.read_text(encoding="utf-8")), "上次回顧"
    except (OSError, ValueError):
        valid = [s for s in stamps if s]
        since, label = (min(valid) if valid else now), "從未回顧，最早一筆"
    days = (now - since).days
    if n < COUNT_THRESHOLD and days < DAYS_THRESHOLD:
        return
    msg = f"回饋佇列有 {n} 條未處理（{label} {days} 天前），可跑 /feedback-review"
    # 使用者不會記得何時該回顧，所以交代 agent 主動提議；但不能岔開使用者當下的任務
    ask = ("。做完使用者這次交辦的任務後，用 AskUserQuestion 問一次要不要跑 /feedback-review；"
           "使用者拒絕就不再提，不要在任務進行中插入，也不要未經同意直接執行。")
    sys.stdout.write(json.dumps({
        "systemMessage": msg,
        "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": msg + ask},
    }, ensure_ascii=False))


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        main()
    except Exception as exc:
        try:
            sys.stderr.write(f"feedback-reminder: {exc!r}\n")
        except Exception:
            pass
    sys.exit(0)
