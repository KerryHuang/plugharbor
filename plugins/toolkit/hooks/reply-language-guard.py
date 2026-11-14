#!/usr/bin/env python3
"""Stop hook：使用者用 CJK 提問，這回合卻有整段英文回覆時擋下，要求用使用者的語言重述。

起因：context 壓縮後回覆漂成英文，壓縮時注入一次提醒（compact-context.py）仍擋不住，
漂移多在工具呼叫之間的進度短句（2026-11-12）。
判斷：去掉程式碼、inline code、URL、路徑後，有 3 個以上英文單字、且沒有任何 CJK 字的文字段就算英文段。
使用者最後一則提問不是 CJK 為主就不管；只掃最後一個回合起點（含 meta 列開啟的回合）之後的回覆。stop_hook_active 代表已擋過一次，放行避免迴圈。fail-open。
"""
import json
import os
import re
import sys

TAIL_BYTES = 4 * 1024 * 1024
CJK = re.compile(r"[぀-ヿ㐀-䶿一-鿿가-힯]")
STRIP = [re.compile(p, re.S) for p in (r"```.*?(```|$)", r"`[^`\n]*`", r"https?://\S+", r"(?<!\w)[\w.~-]*/[\w./~-]+")]
WORD = re.compile(r"[A-Za-z]{2,}")


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


def prompt_text(row):
    """真正的使用者提問回傳文字，其他（tool_result、meta、壓縮摘要）回傳 None。"""
    if row.get("type") != "user" or row.get("isMeta") or row.get("isCompactSummary"):
        return None
    content = row.get("message", {}).get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list) and not is_tool_result(row):
        return " ".join(c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text")
    return None


def is_tool_result(row):
    content = row.get("message", {}).get("content")
    return isinstance(content, list) and any(isinstance(c, dict) and c.get("type") == "tool_result" for c in content)


def is_cjk_prompt(text):
    letters = len(CJK.findall(text)) + len(re.findall(r"[A-Za-z]", text))
    return letters > 0 and len(CJK.findall(text)) * 3 >= letters


def english_block(text):
    for pattern in STRIP:
        text = pattern.sub(" ", text)
    return not CJK.search(text) and len(WORD.findall(text)) >= 3


def main():
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return
    path = payload.get("transcript_path")
    if payload.get("stop_hook_active") or not path or not os.path.exists(path):
        return
    rows = read_rows(path)
    for i in range(len(rows) - 1, -1, -1):
        prompt = prompt_text(rows[i])
        if prompt is not None:
            break
    else:
        return
    if not is_cjk_prompt(prompt):
        return
    # 回合起點：最後一個非 tool_result 的 user 列。跨 session 訊息、subagent 交回、Stop hook 回饋都是 meta 列，
    # 也會開啟新回合；只從提問算起的話，自動駕駛開場回合的英文會在之後每個回合被重擋（2026-11-14）
    start = max(j for j in range(i, len(rows)) if rows[j].get("type") == "user" and not is_tool_result(rows[j]))
    texts = [c.get("text", "") for row in rows[start + 1:] if row.get("type") == "assistant"
             for c in row.get("message", {}).get("content", []) if isinstance(c, dict) and c.get("type") == "text"]
    # Stop 觸發時最後一則回覆常還沒寫進 transcript，只在 payload 裡
    texts.append(payload.get("last_assistant_message") or "")
    for text in texts:
        if english_block(text):
            sample = text.strip().splitlines()[0][:80]
            reason = (f"這一回合有回覆用了英文（例：「{sample}」），使用者用中文提問。"
                      "語言照使用者的 CLAUDE.md，context 壓縮摘要與系統提示的語言不算數。"
                      "用使用者的語言重述這一回合的結論再結束，之後的進度說明也一樣。")
            sys.stdout.buffer.write(json.dumps({"decision": "block", "reason": reason},
                                               ensure_ascii=False).encode("utf-8"))
            return


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # fail-open：hook 壞掉不能卡住回合結束
        print(f"[reply-language-guard] {e}", file=sys.stderr)
    sys.exit(0)
