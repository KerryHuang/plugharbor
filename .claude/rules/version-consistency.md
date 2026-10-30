---
description: 改 plugin 內容時的版號與 CHANGELOG 規則
globs:
  - "plugins/*/.claude-plugin/plugin.json"
  - "plugins/*/skills/**"
  - "plugins/*/agents/**"
  - "plugins/*/references/**"
  - "plugins/*/templates/**"
  - "plugins/*/CHANGELOG.md"
  - ".claude-plugin/marketplace.json"
  - "README.md"
---

# Version Consistency

- 改到 `skills/`、`agents/`、`references/`、`templates/` 時，**同一個 commit** 內完成：
  1. 該 plugin 的 `CHANGELOG.md` 最上方新增 `## [x.y.z] - yyyy-mm-dd` 條目（正體中文）
  2. bump `plugin.json`、`marketplace.json`、根 `README.md` 版本欄（`release-plugin` skill 會同步三處）
  不可累積多個 commit 後才補。
- Bump 級距：`fix` → patch；`feat`（新 skill／功能）→ minor；BREAKING（改名、拆分、移除、介面不相容）→ major；`docs`／`chore`／`refactor` → patch。
- 新增／改名／刪除 skill 或 agent 時，同步根 `README.md` 的「skills 與 agents」表與該 plugin 的 README。
- 以上由 `scripts/ci/validate.py` 機械檢查（CI 與 pre-commit 都會跑）；commit 前可先手動執行。
