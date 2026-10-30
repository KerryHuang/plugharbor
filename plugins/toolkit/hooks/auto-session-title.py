#!/usr/bin/env python3
"""UserPromptSubmit hook：套用 skill 建議的 session 標題。

一般 session 交給 Claude Code 內建的 ai-title（以開場內容命名，含票號／功能代碼，品質夠用）；
本 hook 只在上一回合 assistant 給了「建議 session 標題…：/rename <標題>」（如 sdlc:linear-triage
報告末尾）時，於下一次送出輸出 sessionTitle 套用——model 無法自己執行 /rename。
使用者手動 /rename 的（nameSource="user"）不覆寫。

註：曾自己用 haiku 產標題，但寫入的 custom-title 會蓋掉內建 ai-title，實測幾乎都比內建差，已移除。
"""
import json
import os
import re
import sys
from pathlib import Path

SUGGEST_RE = re.compile(r"建議[^\n]{0,10}session 標題[^\n]*?/rename\s+([^\n`]+)")
TAIL_BYTES = 256 * 1024
MAX_TITLE = 80


def current_name(sid):
    """回傳 (nameSource, name)；找不到這個 session 回 ("", "")。
    名稱寫在 ~/.claude/sessions/<pid>.json，以 sessionId 比對。"""
    d = Path(os.path.expanduser("~/.claude")) / "sessions"
    try:
        files = list(d.glob("*.json"))
    except OSError:
        return "", ""
    for f in files:
        try:
            rec = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if rec.get("sessionId") == sid:
            return rec.get("nameSource") or "", (rec.get("name") or "").strip()
    return "", ""


def suggested_title(transcript):
    """從 transcript 尾端找上一回合 assistant 文字裡的建議標題；沒有回空字串。
    往回掃到真正的使用者 prompt（非 tool_result）為止；當輪 prompt 若已寫入就先跳過。"""
    try:
        with open(transcript, "rb") as fh:
            fh.seek(0, os.SEEK_END)
            fh.seek(max(0, fh.tell() - TAIL_BYTES))
            tail = fh.read().decode("utf-8", errors="replace")
    except OSError:
        return ""
    seen_assistant = False
    for line in reversed(tail.splitlines()):
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        content = (rec.get("message") or {}).get("content")
        if rec.get("type") == "user":
            is_prompt = isinstance(content, str) or (
                isinstance(content, list)
                and any(isinstance(b, dict) and b.get("type") != "tool_result" for b in content)
            )
            if is_prompt and seen_assistant:
                return ""
            continue
        if rec.get("type") != "assistant" or not isinstance(content, list):
            continue
        seen_assistant = True
        text = "\n".join(
            b.get("text", "") for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        )
        hits = SUGGEST_RE.findall(text)
        if hits:
            title = hits[-1].strip(" *`「」\"'")
            return title if 0 < len(title) <= MAX_TITLE else ""
    return ""


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return
    sid = data.get("session_id")
    transcript = data.get("transcript_path")
    if not sid or not transcript:
        return
    title = suggested_title(transcript)
    if not title:
        return
    source, name = current_name(sid)
    if source == "user" or name == title:
        return
    sys.stdout.write(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "sessionTitle": title,
        }
    }, ensure_ascii=False))


if __name__ == "__main__":
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    main()
