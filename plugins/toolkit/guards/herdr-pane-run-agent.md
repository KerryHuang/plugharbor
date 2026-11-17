---
tool: Bash
pattern: '(?:^|[;&|(])\s*herdr\s+pane\s+run\s+\S+\s+["'']?(?:claude|codex|agy|pi)(?=[\s"'']|$)'
action: deny
evidence: 2026-11-14～15 主 session 用 herdr pane run <pane> claude 起 session，繞過 agent start，沒帶 model／effort、herdr 也追蹤不到 agent
---
用 `python3 ${CLAUDE_PLUGIN_ROOT}/skills/agent-dispatch/scripts/mux.py spawn --name <唯一名稱> --kind <claude|codex|agy|pi> --cwd <目錄> -- <模型參數>` 起 CLI（claude `--model <m> --effort <e>`，其他見 agent-mesh-check 的 cli-notes.md），再用 `mux.py send` 送 prompt。
