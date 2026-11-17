---
tool: Bash
pattern: '(?:^|[;&|(])\s*hc\s+run\b[^;&|\n]*?(?<!--cwd)\s["'']?(?:\S*/)?(?:claude|codex|agy|pi)(?=[\s"'']|$)'
action: deny
evidence: 同 herdr-pane-run-agent 的 2026-11-14～15 事故（直接用終端指令起 CLI，沒帶 model／effort）；Herdr.app 後 mux.py spawn 是唯一入口，直接 hc run 起 CLI 還會繞過 CLI 絕對路徑解析、污染環境變數清除、--no-notify 與版面放置
---
用 agent-dispatch skill 的 scripts 目錄下的 `mux.py spawn --name <唯一名稱> --kind <claude|codex|agy|pi> --cwd <目錄> -- <模型參數>` 起 CLI（claude `--model <m> --effort <e>`，其他見 agent-mesh-check 的 cli-notes.md），再用 `mux.py send` 送 prompt。
`hc run` 跑一般指令（如 `hc run 'npm test'`）不受影響。
