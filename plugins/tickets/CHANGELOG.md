# Changelog

格式：每次改動 `skills/`、`agents/`、`references/`、`templates/` 時，於最上方新增版本條目並同步 bump 版號（規則見 `.claude/rules/version-consistency.md`）。

## [1.2.0] - 2026-11-17

起因：使用者 2026-11-17 轉用 Herdr.app，派工流程在 app 內無法開 worker。

- 同上：`references/advisor-discussion.md`、`consultant-desk.md`、`shared-preludes.md`、`scripts/advisor_last_reply.py` 從 lifecycle 4.2.0 的同名檔依對照表同步（只差 agent 名稱）；新增 `scripts/mux.py`、`scripts/app_layout.py`、`scripts/herdr_layout.py`（版面腳本，與 toolkit `agent-dispatch` 正本位元組相同；顧問 pane 排進主 session 旁；版面不依賴 toolkit，hc 下讀顧問 transcript 需 toolkit 的 SessionStart hook，沒有就改走 subagent 模式）。
- 同上（最終審查）：同步 lifecycle 4.2.0 的 `advisor-discussion.md` 修正（`session` 為 null 最多重試 3 次，缺 hook 改走 subagent 模式）與 `mux.py`、`app_layout.py` 副本更新。
- fix（實機驗收）：`app_layout.py` 副本同步（見 toolkit 0.25.0：spawn 後立刻放置會回 `no running terminal`，改為重試）。

## [1.1.0] - 2026-11-16

起因：xiaoxiao 的 34 張票在 D1 補開時誤掛到 plugharbor 的看板 #1（違反票務雙軌設計「每個 repo 各建看板」），`reconcile.py` 只收本 repo 的票，兩邊對帳都是差異 0，沒人發現；之後用票號找看板項目時撞到同號的兩張票才暴露。

- `ticket-ops/scripts/reconcile.py`：看板上有別的 repo 的 Issue 時，在報告加一行 ⚠️ 列出各 repo 張數（不計入差異、不影響退出碼）；新增純函式 `other_repo_issues()` 與測試。

## [1.0.1] - 2026-11-16

起因：lifecycle 4.1.0 把設計文件改成新章節格式（設計見 `docs/superpowers/specs/2026-11-15-lifecycle-split-design.md`，第三批），本 plugin 的共用 references 副本跟著改讀新章節。

**改動**

- `references/` 共用副本（config、shared-preludes、shared-preludes-details、analysis-rigor、consultant-desk、legacy-parity）改讀新章節，舊章節以「（舊範本 §n）」括號別名保留。
- `references/pipeline.md`、`skills/ticket-reply/SKILL.md`：implement 步驟改稱實作前檢查；CR 流程與 TD 留置的章節對照改指新章節。

## [1.0.0] - 2026-11-15

起因：lifecycle 一個 plugin 管太多事（規格、票務、勘察、手冊、發版），要用票務的人得裝整包。設計見 `docs/superpowers/specs/2026-11-15-lifecycle-split-design.md`，第二批「拆 plugin」，tickets 是第一個拆出來的。

- 自 lifecycle 3.0.0 搬入：skills `ticket-ops`、`ticket-create`、`ticket-reply`、`ticket-report`、`triage`；agents `report-writer`、`silent-failure-hunter`；references `pipeline.md`、`report-calendar.md`。叫用名由 `lifecycle:<名稱>` 改為 `tickets:<名稱>`。
- 能單獨安裝，所以帶一份共用 references／scripts 副本（`harness-terms`、`config`、`shared-preludes*`、`consultant-desk` 等核心包，加 `feature-checklist.md`、`feature_checklist.py`）；canonical 在 lifecycle，漂移由 validate 的共用副本檢查擋。
- `scout` 的副本改名 `tickets-scout`（`<plugin>-<原名>` 規則），避免與 lifecycle 的 `lifecycle:scout` 同名混淆；`triage` 帶自己的 second-opinion 副本；`references/pipeline.md` 內的 `scout` 改為 `tickets-scout`。
- 新增 `scripts/test_skill_contracts.py`（自 lifecycle 搬來票務相關的接點契約，另驗 `reconcile.py` 找得到清單解析器）。
