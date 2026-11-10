#!/bin/bash
# Claude Code subagentStatusLine — agent 面板每列：類型 · 模型/effort · 進度 · token
# stdin：{"columns": N, "tasks": [{id, agentType, model?, effort?, label, tokenCount, ...}]}
# stdout：每列一行 {"id": ..., "content": ...}
# Windows 的 python3 可能是 Store 捷徑跑不起來，依序找能執行的
PY=python3
"$PY" -c '' >/dev/null 2>&1 || PY=python
PYTHONUTF8=1 exec "$PY" -c '
import json, re, sys

data = json.load(sys.stdin)
cols = int(data.get("columns") or 80)
DIM, RESET = "\033[38;5;240m", "\033[0m"
COLORS = {"opus": "\033[38;5;177m", "sonnet": "\033[38;5;110m", "haiku": "\033[38;5;78m", "fable": "\033[38;5;220m"}

for t in data.get("tasks", []):
    name = t.get("name") or t.get("agentType") or "agent"
    model = t.get("model") or ""
    m = re.search(r"(opus|sonnet|haiku|fable)", model)
    short = m.group(1) if m else (model.replace("claude-", "") or "?")
    effort = t.get("effort")
    tag = short + (f"/{effort}" if effort else "")
    color = COLORS.get(short, "")
    label = t.get("label") or t.get("description") or ""
    tokens = str(int(t.get("tokenCount") or 0) // 1000) + "K"

    fixed = len(name) + len(tag) + len(tokens) + 9  # 三個 " · " 分隔
    room = max(cols - fixed, 8)
    if len(label) > room:
        label = label[: room - 1] + "…"

    content = f"{name}{DIM} · {RESET}{color}{tag}{RESET}{DIM} · {RESET}{label}{DIM} · {tokens}{RESET}"
    print(json.dumps({"id": t["id"], "content": content}, ensure_ascii=False))
'
