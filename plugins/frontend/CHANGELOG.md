# Changelog

格式：每次改動 `skills/`、`agents/`、`references/` 時，於最上方新增版本條目並同步 bump 版號（規則見 `.claude/rules/version-consistency.md`）。

## [1.0.2] - 2026-11-04

- fix: 派工引用改為 `lifecycle:` 命名空間（sa-flow／delivery-flow／dev-flow 已合併為 lifecycle）。

## [1.0.1] - 2026-11-03

- fix: 派 `dev-flow:reviewer`／`dev-flow:tester`（或 general-purpose 退路）時，把 §0 載入的附錄絕對路徑寫進派工 prompt。

## [1.0.0] - 2026-11-03

- feat: 新 plugin，自 frontend-vue 0.x 改寫為「職責＋技術棧附錄」：`frontend-architecture`、`component-logic`（原 `vue-composables`）、`i18n`（原 `i18n-implementation`）、`runtime-debug`（原 `chrome-devtools-debug`）。各 skill 開頭偵測 `package.json` 載入附錄。
- feat: 新增附錄 `references/stacks/vue.md`，收 Vue 3＋TypeScript＋Quasar＋Pinia＋TanStack Query 的範例與 `## 常見坑`；`react`、`svelte`、`@angular/core` 暫無附錄，走退路。
- refactor: `release-workflow` 併入 `dev-flow:release`；`review-remote` 併入 `workspace:review`。
- BREAKING: 移除 `openspec-propose`、`openspec-apply-change`、`openspec-archive-change`、`openspec-explore`，不搬。
- BREAKING: `code-reviewer`、`test-engineer` 不搬，改由 `dev-flow:reviewer`／`dev-flow:tester`（可選）承接；沒裝就用 general-purpose subagent 附角色說明。
