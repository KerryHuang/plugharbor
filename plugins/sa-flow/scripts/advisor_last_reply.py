#!/usr/bin/env python3
"""印出某個 session 最後一輪的完整回覆文字（雙顧問討論，pane 模式用）。

顧問是唯讀 agent、不能寫檔；`herdr agent prompt --wait` 只回狀態不回內容，
`herdr agent read` 回的是終端畫面、會被捲動與折行截斷。transcript 才是完整內容，
主線用本腳本取出後自行落檔成每輪回應檔。

「最後一輪」＝最後一則使用者輸入（不含工具結果）之後，所有 assistant 文字區塊依序串接。
找不到 transcript、或最後一輪沒有任何文字 → exit 1 並說明原因，不印空字串
（空輸出長得像「顧問沒意見」，會被當成共識）。

用法：advisor_last_reply.py <sessionId 或其前綴>
"""
import glob
import json
import os
import sys

# Windows 預設 cp950：印中文會亂碼、印 emoji 直接炸 UnicodeEncodeError。
# 與 parse_foxpro.py 同一做法，腳本自己處理，不靠呼叫端設 PYTHONUTF8。
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")


def find_transcript(prefix, root=None):
    root = root or os.path.expanduser("~/.claude/projects")
    hits = glob.glob(os.path.join(root, "*", f"{prefix}*.jsonl"))
    if len(hits) > 1:
        raise LookupError(f"前綴 {prefix} 對到 {len(hits)} 份 transcript，請給更長的 sessionId")
    return hits[0] if hits else None


def is_user_prompt(entry):
    if entry.get("type") != "user":
        return False
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, str):
        return True
    if isinstance(content, list):
        return any(isinstance(b, dict) and b.get("type") == "text" for b in content) and not any(
            isinstance(b, dict) and b.get("type") == "tool_result" for b in content)
    return False


def last_reply(path):
    texts, seen = [], set()
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if is_user_prompt(entry):
                texts, seen = [], set()
                continue
            if entry.get("type") != "assistant":
                continue
            msg = entry.get("message") or {}
            for i, block in enumerate(msg.get("content") or []):
                if isinstance(block, dict) and block.get("type") == "text" and block.get("text", "").strip():
                    key = (msg.get("id"), i, block["text"])
                    if key not in seen:
                        seen.add(key)
                        texts.append(block["text"])
    return "\n\n".join(texts)


def main(argv):
    if len(argv) != 1:
        print("用法：advisor_last_reply.py <sessionId 或其前綴>", file=sys.stderr)
        return 2
    try:
        path = find_transcript(argv[0])
    except LookupError as e:
        print(e, file=sys.stderr)
        return 1
    if not path:
        print(f"{argv[0]}: 找不到 transcript", file=sys.stderr)
        return 1
    reply = last_reply(path)
    if not reply:
        print(f"{argv[0]}: 最後一輪沒有任何回覆文字（顧問可能還在跑或中斷）", file=sys.stderr)
        return 1
    print(reply)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
