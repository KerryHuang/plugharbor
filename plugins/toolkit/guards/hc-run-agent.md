---
tool: Bash
pattern: '(?:^|[;&|(])\s*hc\s+run\b[^;&|\n]*?\s["'']?(?:claude|codex|agy|pi)(?=[\s"'']|$)'
action: deny
evidence: 2026-11-17 轉用 Herdr.app 後，mux.py spawn 是唯一啟動 agent 的入口（解析 CLI 絕對路徑、清污染環境變數、帶 --no-notify、放進主 session 旁）；直接 hc run 起 CLI 會漏帶 model／effort 並繞過這些處理
---
用 `python3 ${CLAUDE_PLUGIN_ROOT}/skills/agent-dispatch/scripts/mux.py spawn --name <唯一名稱> --kind <claude|codex|agy|pi> --cwd <目錄> -- <模型參數>` 起 CLI（claude `--model <m> --effort <e>`，其他見 agent-mesh-check 的 cli-notes.md），再用 `mux.py send` 送 prompt。
`hc run` 跑一般指令（如 `hc run 'npm test'`）不受影響。
