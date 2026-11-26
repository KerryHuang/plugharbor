import json, re, glob, os, sys
from collections import Counter
SUG = re.compile(r"^[ \t>*\-]*建議[^\n]{0,10}session 標題[^\n]*?/rename\s+([^\n`]+)", re.M)
stats = Counter(); samples = []
for f in glob.glob(os.path.expanduser("~/.claude/projects/*/*.jsonl")):
    try: L = open(f, encoding="utf-8").read().splitlines()
    except OSError: continue
    recs = []
    for l in L:
        try: recs.append(json.loads(l))
        except ValueError: recs.append({})
    for i, r in enumerate(recs):
        if r.get("type") != "assistant": continue
        c = (r.get("message") or {}).get("content")
        if not isinstance(c, list): continue
        txt = "\n".join(b.get("text","") for b in c if isinstance(b,dict) and b.get("type")=="text")
        m = SUG.findall(txt)
        if not m: continue
        ts = r.get("timestamp","")
        # 找下一則真正的使用者 prompt（字串內容、不是 task-notification／系統訊息）
        j = i + 1; nxt = None
        while j < len(recs):
            q = recs[j]; qc = (q.get("message") or {}).get("content")
            if q.get("type") == "assistant": break
            if q.get("type") == "user" and isinstance(qc, str) and not qc.lstrip().startswith("<"):
                nxt = j; break
            j += 1
        if nxt is None: continue
        prompt = recs[nxt]["message"]["content"]
        # 排隊：有 enqueue 且內容相同、時間早於建議行
        queued = any(q.get("type")=="queue-operation" and q.get("operation")=="enqueue" and q.get("content")==prompt and q.get("timestamp","") < ts for q in recs[max(0,i-200):nxt])
        applied = any(q.get("type")=="custom-title" for q in recs[i:nxt+40])
        k = ("queued" if queued else "normal", "applied" if applied else "missing")
        stats[k] += 1
        if len(samples) < 8 and k == ("normal","missing"): samples.append((f.split('/')[-2][-30:], nxt+1))
print(dict(stats)); print("normal-missing 範例", samples)
