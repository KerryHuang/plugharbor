# Changelog

格式：每次改動 `skills/`、`agents/`、`references/`、`templates/` 時，於最上方新增版本條目並同步 bump 版號（規則見 `.claude/rules/version-consistency.md`）。

## [1.0.0] - 2026-11-15

起因：lifecycle 一個 plugin 管太多事（規格、票務、勘察、手冊、發版），要用票務的人得裝整包。設計見 `docs/superpowers/specs/2026-11-15-lifecycle-split-design.md`，第二批「拆 plugin」，tickets 是第一個拆出來的。

- 自 lifecycle 3.0.0 搬入：skills `ticket-ops`、`ticket-create`、`ticket-reply`、`ticket-report`、`triage`；agents `report-writer`、`silent-failure-hunter`；references `pipeline.md`、`report-calendar.md`。叫用名由 `lifecycle:<名稱>` 改為 `tickets:<名稱>`。
- 能單獨安裝，所以帶一份共用 references／scripts 副本（`harness-terms`、`config`、`shared-preludes*`、`consultant-desk` 等核心包，加 `feature-checklist.md`、`feature_checklist.py`）；canonical 在 lifecycle，漂移由 validate 的共用副本檢查擋。
- `scout` 的副本改名 `tickets-scout`（`<plugin>-<原名>` 規則），避免與 lifecycle 的 `lifecycle:scout` 同名混淆；`triage` 帶自己的 second-opinion 副本；`references/pipeline.md` 內的 `scout` 改為 `tickets-scout`。
- 新增 `scripts/test_skill_contracts.py`（自 lifecycle 搬來票務相關的接點契約，另驗 `reconcile.py` 找得到清單解析器）。
