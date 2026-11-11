# superpowers 覆寫

superpowers（外部 plugin）管 brainstorm → plan → 實作 → 審查；以下偏好優先於它的預設。

- 設計文件與規格：有 lifecycle 設定就放 `<spec.dir>`（預設 `docs/specs/`），否則照預設。
- 實作計畫：放 `.tmp/plans/<yyyymmdd-slug>/`（`.tmp/` 須已 gitignore），不放 `docs/superpowers/plans/`。
- worktree：建在 repo 同層 `../<repo>-<名稱>`，不建 `.worktrees/`；細節照 workspace:worktree。
- 裝了 lifecycle 時：brainstorming 要寫設計文件、叫 writing-plans 前，先叫 `lifecycle:implement` 前段（讀經驗、規格閘門），由它交給 writing-plans；小改動照原做法。
- 設計初稿（含 subagent 起草）送審前，影響使用者行為的待確認先問完、寫回設計；技術類標為自己的決定。
- 專案的討論與規劃結果列進 `docs/feature-checklist.md`（每項一行：`[x]` 完成、`[ ]` 加 🚧 進行中／📋 已規劃／💡 構想、`[-]` 不做附理由）；裝了 lifecycle 照它的 `references/feature-checklist.md`（含排線）與腳本。
