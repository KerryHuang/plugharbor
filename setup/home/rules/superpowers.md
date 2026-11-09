# superpowers 覆寫

superpowers（外部 plugin）管 brainstorm → plan → 實作 → 審查的方法；以下是使用者偏好，優先於它的預設。

- 設計文件與規格：專案有 lifecycle 設定就放 `<spec.dir>`（預設 `docs/specs/`），沒有就照 superpowers 預設。
- 實作計畫：放 `.tmp/plans/<yyyymmdd-slug>/`（專案的 `.tmp/` 必須已 gitignore），不放 `docs/superpowers/plans/`。
- worktree：建在 repo 的同層目錄 `../<repo>-<名稱>`，不建 `.worktrees/`；建立與移除的細節照 workspace:worktree。
