# superpowers 覆寫

superpowers（外部 plugin）管 brainstorm → plan → 實作 → 審查；以下偏好優先於它的預設。

- 設計文件與計畫：照 superpowers 預設放 `docs/superpowers/specs/`、`docs/superpowers/plans/`，進版控（專案刻意排除 `docs/superpowers` 就只放本機），每個專案都一樣；專案還沒有這兩個目錄（含新專案）時先問使用者再建。有 lifecycle 設定時 `spec.dir` 也設成前者。
- worktree：建在 repo 同層 `../<repo>-<名稱>`，不建 `.worktrees/`；細節照 workspace:worktree。
- 裝了 lifecycle：要問我的決定題（設計題、回來報告的待決、自動駕駛記下的「主控裁決待確認」，一題也算）一律先交 `lifecycle:domain-advisor`（`mode: triage`）分流，只把它判「要問使用者」的交給我（使用者 2026-11-21 裁決，起因：待決直接逐題問、漏了分流）；「開始實作」走 `lifecycle:implement`；專案 AGENTS.md 有 lifecycle 段落就照它。
- 設計初稿（含 subagent 起草）送審前，影響使用者行為的待確認先問完、寫回設計；技術類標為自己的決定。
- 討論與規劃結果列進 `docs/feature.md`（每項一行：`[x]` 完成、`[ ]` 加 🚧 進行中／📋 已規劃／💡 構想、`[-]` 不做附理由）；有 lifecycle 照它的 `references/feature-checklist.md`（排線、todo 分界）。
