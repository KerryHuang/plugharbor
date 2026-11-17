#!/usr/bin/env python3
"""PostToolUse hook（SendMessage）：收件人找不到時，提示用 ListAgents 找回收件方、用目前名稱重送一次。

起因：送達比對的是名稱；收件方在派工後改名（建議標題 hook、/rename、重開）就回
「No agent named '<X>' is reachable」，worker 照指示寫 undelivered 不重試。11-01～11-17 有 5 起、
10-21 派工批次 61 次；改送「目前名稱 [同一個 ref]」每次都成功（docs/retrospective/20261117-reply-address）。
送不到時 Claude Code 觸發的是 PostToolUse（tool_response.success=false），不是 PostToolUseFailure
（2026-11-17 以 claude -p 實測）。fail-open：判不出就不輸出。
"""
import json
import re
import sys

REF = re.compile(r"\[([0-9a-f]{6})\]\s*$")


def main():
    try:
        payload = json.loads(sys.stdin.buffer.read().decode("utf-8") or "{}")
    except ValueError:
        return
    if payload.get("tool_name") != "SendMessage":
        return
    resp = payload.get("tool_response")
    text = resp.get("message", "") if isinstance(resp, dict) else str(resp or "")
    if not str(text).startswith("No agent named"):
        return
    to = str((payload.get("tool_input") or {}).get("to", ""))
    m = REF.search(to)
    find = "帶 [%s] 的那一列" % m.group(1) if m else "對應的那一列（看 Did you mean 與名稱）"
    ctx = ("收件方可能改名或重開了：先用 ListAgents 找%s，改用那列的「目前名稱 [ref]」重送一次"
           "（不要只寫 ref）；找不到或仍失敗，才照原本的指示處理（如寫 undelivered）。" % find)
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": ctx}},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
