# superpowers 覆寫

superpowers（外部 plugin）管 brainstorm → plan → 實作 → 審查的方法；以下是使用者偏好，優先於它的預設。

- 設計文件與規格：專案有 lifecycle 設定就放 `<spec.dir>`（預設 `docs/specs/`），沒有就照 superpowers 預設。
- 實作計畫：放 `.tmp/plans/<yyyymmdd-slug>/`（專案的 `.tmp/` 必須已 gitignore），不放 `docs/superpowers/plans/`。
- worktree：建在 repo 的同層目錄 `../<repo>-<名稱>`，不建 `.worktrees/`；建立與移除的細節照 workspace:worktree。
- 專案裝了 lifecycle 時：brainstorming 判定要寫設計文件、準備叫 writing-plans 之前，先叫 `lifecycle:implement` 的前段（讀經驗、規格閘門），由它交給 writing-plans；小改動照 brainstorming 原本的做法。
