#!/usr/bin/env python3
"""PreToolUse hook for AskUserQuestion（user 層）：題目不自明就退回重寫。

使用者常只看得到對話框、看不到前文；曾出現只寫「要選 A 還是 B」、選項沒說明的題目，
答不出來只能回頭問（見 shared/communication.md「提問」）。本 hook 擋三件事：
question 太短、選項 description 太短、沒有任何選項標「（推薦）」（預設值類標「（預設）」也算，
同 sa-flow／sdlc preludes）。門檻只是最低線，寫夠長不代表自明。解析不到 stdin 時 fail-open。
"""
import json
import sys

MIN_QUESTION = 40
MIN_DESCRIPTION = 15
MARK = "（推薦）"
MARKS = (MARK, "（預設）")


def problems(questions) -> list:
    out = []
    for i, q in enumerate(questions, 1):
        if not isinstance(q, dict):
            continue
        text = "".join((q.get("question") or "").split())
        if len(text) < MIN_QUESTION:
            out.append("第 %d 題 question 只有 %d 字（至少 %d）：補上背景——發現了什麼、要決定什麼、選錯會怎樣"
                       % (i, len(text), MIN_QUESTION))
        options = [o for o in q.get("options") or [] if isinstance(o, dict)]
        for o in options:
            desc = "".join((o.get("description") or "").split())
            if len(desc) < MIN_DESCRIPTION:
                out.append("第 %d 題選項「%s」的 description 太短（至少 %d 字）：寫選了之後會發生什麼、代價是什麼"
                           % (i, o.get("label") or "", MIN_DESCRIPTION))
        if options and not any(m in (o.get("label") or "") for o in options for m in MARKS):
            out.append("第 %d 題沒有選項標「%s」：推薦選項放第一個、label 結尾標「%s」、description 寫理由"
                       % (i, MARK, MARK))
    return out


def main() -> int:
    # Windows 預設編碼不是 UTF-8：中文 payload 解碼失敗會被下面吞掉、guard 靜默失效
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        payload = json.load(sys.stdin)
        if payload.get("tool_name") != "AskUserQuestion":
            return 0
        questions = payload["tool_input"]["questions"]
        found = problems(questions) if isinstance(questions, list) else []
    except Exception:
        return 0
    if not found:
        return 0
    json.dump({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": "ask-question-guard：使用者可能只看得到對話框，題目要能單獨看懂。請修正後重問：\n- "
                                        + "\n- ".join(found),
        }
    }, sys.stdout, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
