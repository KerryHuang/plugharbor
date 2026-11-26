# superpowers 覆寫

superpowers（外部 plugin）管 brainstorm → plan → 實作 → 審查；以下偏好優先於它的預設。

- 設計文件與計畫：照 superpowers 預設放 `docs/superpowers/specs/`、`docs/superpowers/plans/`，進版控（專案刻意排除 `docs/superpowers` 就只放本機），每個專案都一樣；專案還沒有這兩個目錄（含新專案）時先問使用者再建。有 lifecycle 設定時 `spec.dir` 也設成前者。
- worktree：建在 repo 同層 `../<repo>-<名稱>`，不建 `.worktrees/`；細節照 workspace:worktree。
- 裝了 lifecycle：要問我的決定題（設計題、回來報告的待決、自動駕駛記下的「主控裁決待確認」，一題也算）一律先交 `lifecycle:domain-advisor`（`mode: triage`）分流，只把它判「要問使用者」的交給我；「開始實作」走 `lifecycle:implement`；專案 AGENTS.md 有 lifecycle 段落就照它。
- 派工：superpowers 的 skill 要派 subagent（逐件實作、審查、總審、修正波）時，派給誰、用什麼模型照 `dispatch.md` 判準表與等級表，不照 skill 預設的 Agent subagent；要 MCP 的才用 Agent。
- 裁決分兩類：設計、計畫、實作、審查任一階段，碰到使用者看得到或感覺得到的取捨（多一個彈窗、版面變小、等待變久、流程多一步）就停下來用 AskUserQuestion 問，寫回設計再繼續；技術題（介面、測試、派工、效能內部做法）照 skill 自己裁決、記進帳本。skill 要求「不停」不適用於前者。
- 討論與規劃結果列進 `docs/feature.md`（每項一行：`[x]` 完成、`[ ]` 加 🚧 進行中／📋 已規劃／💡 構想、`[-]` 不做附理由）；有 lifecycle 照它的 `references/feature-checklist.md`（排線、todo 分界）。
