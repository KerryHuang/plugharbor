#!/usr/bin/env python3
"""Stop hook：回合以文字問句結尾、這回合又沒呼叫 AskUserQuestion 時擋下一次，要求改用 AskUserQuestion。

起因：user 層規則早寫「需要我決定的事一律用 AskUserQuestion」，跑 brainstorming 時 agent 仍照 skill
用一段文字一題一題問，使用者回「你怎麼沒用 AskUserQuestion 問我」（2026-11-12，回饋佇列）。文字規則已失效，改成機制。
判斷：去掉程式碼與 inline code 後，最後一段（略過「建議 session 標題」行）有一行以「？」或「?」結尾。
無人值守 worker（AGENT_DISPATCH_UNATTENDED=1）不管。stop_hook_active 代表已擋過一次，放行避免迴圈。fail-open。
"""
import json
import os
import re
import sys

TAIL_BYTES = 4 * 1024 * 1024
STRIP = [re.compile(p, re.S) for p in (r"```.*?(```|$)", r"`[^`\n]*`")]
SKIP_LINE = re.compile(r"^\s*建議 session 標題")
QUESTION_END = re.compile(r"[？?][\s*_）)」』]*$")


def read_rows(path):
    with open(path, "rb") as f:
        f.seek(0, os.SEEK_END)
        f.seek(max(0, f.tell() - TAIL_BYTES))
        data = f.read().decode("utf-8", "replace")
    rows = []
    for line in data.splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue  # 截斷的第一行或壞行
    return rows


def is_tool_result(row):
    content = row.get("message", {}).get("content")
    return isinstance(content, list) and any(isinstance(c, dict) and c.get("type") == "tool_result" for c in content)


def blocks(row):
    content = row.get("message", {}).get("content")
    return [c for c in content if isinstance(c, dict)] if isinstance(content, list) else []


def question_line(text):
    """最後一段裡以問號結尾的行；沒有回傳 None。"""
    for pattern in STRIP:
        text = pattern.sub(" ", text)
    lines = [ln for ln in text.strip().splitlines() if not SKIP_LINE.match(ln)]
    paragraphs = re.split(r"\n\s*\n", "\n".join(lines).strip())
    for line in paragraphs[-1].splitlines() if paragraphs else []:
        if QUESTION_END.search(line.strip()):
            return line.strip()
    return None


def main():
    if os.environ.get("AGENT_DISPATCH_UNATTENDED") == "1":
        return
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return
    path = payload.get("transcript_path")
    if payload.get("stop_hook_active") or not path or not os.path.exists(path):
        return
    rows = read_rows(path)
    starts = [j for j, r in enumerate(rows) if r.get("type") == "user" and not is_tool_result(r)]
    turn = rows[starts[-1] + 1:] if starts else rows
    assistant = [r for r in turn if r.get("type") == "assistant"]
    if any(b.get("type") == "tool_use" and b.get("name") == "AskUserQuestion" for r in assistant for b in blocks(r)):
        return
    # Stop 觸發時最後一則回覆常還沒寫進 transcript，只在 payload 裡
    last = payload.get("last_assistant_message")
    if not last:
        texts = [b.get("text", "") for r in assistant for b in blocks(r) if b.get("type") == "text"]
        last = texts[-1] if texts else ""
    line = question_line(last)
    if not line:
        return
    reason = (f"這一回合以文字問句結尾（「{line[:80]}」）。要使用者回答或裁決的事改用 AskUserQuestion 問："
              "一次一題、推薦選項放第一個；開放式問題也給 2–4 個典型答案，使用者可選 Other 自填。"
              "不是要使用者回答（反問、引述別人的問題）就把結尾改成陳述句再結束。")
    sys.stdout.buffer.write(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False).encode("utf-8"))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # fail-open：hook 壞掉不能卡住回合結束
        print(f"[text-question-guard] {e}", file=sys.stderr)
    sys.exit(0)
