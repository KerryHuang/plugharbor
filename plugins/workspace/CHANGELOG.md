# Changelog

格式：每次改動 `skills/`、`agents/`、`references/` 時，於最上方新增版本條目並同步 bump 版號（規則見 `.claude/rules/version-consistency.md`）。

## [1.2.0] - 2026-11-04

- feat: `review` 新增 `skills/review/references/evidence.md`——預設只報告、變更檔歸屬表、「查無」前先證明查得到、被削弱的測試／拉長的 timeout／新 suppression 要列出、新套件查 registry；只排除改動前就存在的 suppression。
- fix: `quality-check` 的可選銜接改指 `lifecycle:implement`。

## [1.1.2] - 2026-11-04

- fix: 可選叫用與退路改指向 `lifecycle`（sa-flow／delivery-flow／dev-flow 已合併為 lifecycle）。

## [1.1.1] - 2026-11-03

- fix: `debugging` 的 tdd-cycle 角色分工補沒裝 dev-flow 時的退路，並要求把職責 plugin 的附錄路徑帶進派工 prompt。

## [1.1.0] - 2026-11-03

- feat: 新 skill `cross-platform`（跨平台路徑、換行、大小寫、shell 差異），改寫自 desktop-avalonia 的同名 skill，不再綁 Avalonia。
- feat: `debugging` 吸收 backend-dotnet 的 `tdd-cycle`（Red-Green-Refactor 通用做法放 `skills/debugging/references/tdd-cycle.md`，.NET 指令移到 backend 的附錄）。
- feat: `review` 吸收 frontend-vue 的 `review-remote`（審查遠端 PR／MR，`skills/review/references/review-remote.md`）。

## [1.0.1] - 2026-11-03

- fix: `dual-tool-mirror` 同步時略過含 `.plugharbor-root` 的目錄（plugharbor install-project 複製模式的 skill 複本），不再把它們當成多餘副本刪掉；加 node 測試。

## [1.0.0] - 2026-11-03

- feat: 新 plugin，自 dev-flow 0.3.0 拆出 12 個與規格流程無關、任何專案都用得到的 skill：`commit`、`worktree`、`triage-branch-cleanup`、`submodule-relay`、`tmp-scratch`、`context-hygiene`、`agent-orchestration`、`dual-tool-mirror`、`convention-first`、`debugging`、`review`、`quality-check`。內容不變；叫用 dev-flow 的地方（`quality-check` 銜接 `work-on`、`submodule-relay` 銜接 `release`）改寫成 `dev-flow:` 並標可選。
- feat: 加 `package.json`（`pi.skills`），pi 也載入得到。
