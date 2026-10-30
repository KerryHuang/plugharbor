#!/usr/bin/env python3
"""UserPromptSubmit hook：偵測使用者在糾正 agent 的語句，追加到回饋佇列。

命中就 append 一行 JSON 到 ~/.claude/feedback-loop/queue.jsonl，由 /feedback-review 人審處理。
只記錄、不擋：stdout 一律不輸出（UserPromptSubmit 的 stdout 會注入 context），
任何例外都吞掉、exit 0。偵測寧可誤判不可漏判——雜訊由人審階段丟棄。
"""
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

QUEUE = Path(os.path.expanduser("~/.claude")) / "feedback-loop" / "queue.jsonl"
MAX_PROMPT = 2000   # 超過視為貼上的長文，跳過
EXCERPT = 300

PATTERN = re.compile(
    r"不對|不是這樣|錯了|搞錯|我說過|我剛說|我剛剛說|跟你說過|我不是說|不是叫你|不是要你|我要的是"
    r"|改用|不要再|別再|又來了|怎麼又|為什麼又|你漏了|漏掉|沒照|沒有照|為什麼沒|為什麼不"
    r"|怎麼停|怎麼沒|應該.{0,30}才對|不就.{0,30}嗎|我都要|還要我"
    r"|\bwrong\b|that'?s not what|not what I (?:asked|meant|said)|\bI said\b|\bI told you\b"
    r"|\bI asked\b|\byou missed\b|\byou forgot\b|\bdon'?t do that\b|\bstop doing\b"
    r"|\bwhy did(?:n'?t)? you\b|\bincorrect\b|^\s*no[,.!\s]",
    re.IGNORECASE,
)


def main():
    data = json.load(sys.stdin)
    prompt = (data.get("prompt") or "").strip()
    if not prompt or len(prompt) > MAX_PROMPT or prompt.startswith(("/", "<", 'Sub-agent "')):
        return
    matched = list(dict.fromkeys(m.group(0).strip() for m in PATTERN.finditer(prompt)))
    if not matched:
        return
    now = datetime.now().astimezone()
    rec = {
        "id": now.strftime("%Y%m%d%H%M%S") + "-" + os.urandom(3).hex(),
        "ts": now.isoformat(timespec="seconds"),
        "session_id": data.get("session_id", ""),
        "cwd": data.get("cwd", ""),
        "matched": matched,
        "excerpt": prompt[:EXCERPT],
    }
    QUEUE.parent.mkdir(parents=True, exist_ok=True)
    with open(QUEUE, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    try:
        sys.stdin.reconfigure(encoding="utf-8", errors="replace")
        main()
    except Exception as exc:   # 只記錄的 hook 絕不能擋住使用者
        try:
            sys.stderr.write(f"feedback-capture: {exc!r}\n")
        except Exception:
            pass
    sys.exit(0)
