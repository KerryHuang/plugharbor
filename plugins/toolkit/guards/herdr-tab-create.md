---
tool: Bash
pattern: '(?:^|[;&|(])\s*herdr\s+tab\s+create\b(?![^;&|\n]*--help)'
action: ask
evidence: 2026-11-14～15 主 session 沒載入 agent-dispatch，兩次用 tab create＋pane run claude 開 session，沒帶 model／effort、沒重排、沒掛 worker 標記
---
開新 tab 只有兩種合法用途：同 tab 已有 6 個 worker 後的第 7 個起，或替別的專案開不回報的長駐獨立 session。
其餘派 worker 一律照 agent-dispatch：`herdr pane split --current --direction right --no-focus` → `herdr_layout.py` → `herdr agent start … -- <模型參數>`。
合法用途也要用 `herdr agent start` 起 CLI，不用 `pane run`。
