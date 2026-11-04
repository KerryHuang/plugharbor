#!/usr/bin/env python3
"""讀某個 session 的 transcript，回報其最後一輪的 context 佔用量。

agent 讀不到 /context（使用者端 slash command），但 transcript 的 message.usage 有同等資訊。
input_tokens + cache_read_input_tokens + cache_creation_input_tokens ≈ 該輪 context 佔用。

⚠ PM 與 controller 的數字是移動標的（自己一直在跑），worker 完成後的數字才是穩定值。
   報數字時務必標明量測時點。
"""
import json, os, sys, glob

# Windows 預設 cp950：印中文會亂碼、印 emoji 直接炸 UnicodeEncodeError。
# 與 parse_foxpro.py 同一做法，腳本自己處理，不靠呼叫端設 PYTHONUTF8。
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

def find(prefix):
    root = os.path.expanduser("~/.claude/projects")
    hits = glob.glob(os.path.join(root, "*", f"{prefix}*.jsonl"))
    return hits[0] if hits else None

def last_usage(path):
    best = None
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            try: d = json.loads(line)
            except Exception: continue
            u = (d.get("message") or {}).get("usage")
            if isinstance(u, dict) and "input_tokens" in u:
                best = u
    return best

def main():
    if len(sys.argv) < 2:
        print("用法：ctx.py <sessionId 前綴>...", file=sys.stderr)
        return 2
    rc = 0
    for pre in sys.argv[1:]:
        p = find(pre)
        if not p:
            print(f"{pre}: 找不到 transcript", file=sys.stderr); rc = 1; continue
        u = last_usage(p)
        if not u:
            print(f"{pre}: transcript 無 usage 紀錄", file=sys.stderr); rc = 1; continue
        total = (u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0)
                 + u.get("cache_creation_input_tokens", 0))
        print(f"{pre}\tcontext={total}")
    return rc

if __name__ == "__main__":
    sys.exit(main())
