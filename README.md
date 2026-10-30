# plugharbor

一個給 Claude Code 用的多外掛 marketplace，收斂日常開發從需求到出版的共通做法：
上游 SDLC、跨語言工作流、.NET 後端、Vue 前端、SQL Server、UI/UX、Avalonia 桌面。

## 安裝

```bash
# 1. 註冊 marketplace（只需一次）
claude plugin marketplace add https://github.com/KerryHuang/plugharbor.git

# 2. 安裝需要的外掛
claude plugin install sa-flow@plugharbor
claude plugin install dev-flow@plugharbor
```

安裝後 skills 會自動被 Claude Code 發現，用 `/` 或自然語言觸發即可；agents 則由主流程按需求派工。

## 外掛一覽

| 外掛 | 版本 | 內容 |
|------|------|------|
| [sa-flow](./plugins/sa-flow/README.md) | 3.1.0 | SDLC 上游與驗收——需求探索、需求文件、系統分析、前後端規格、就緒度、規格驗證、Linear 開票與報表、實機驗收、操作手冊，另含 FoxPro 舊系統分析 |
| [dev-flow](./plugins/dev-flow/README.md) | 0.2.0 | 跨語言開發工作流——git 生命週期、工作編排、context 治理 |
| [backend-dotnet](./plugins/backend-dotnet/README.md) | 0.1.0 | .NET Clean Architecture 後端——CQRS / Repository / EF Core / Dapper 產碼、單元測試、TDD |
| [frontend-vue](./plugins/frontend-vue/README.md) | 0.1.0 | Vue 3 + TypeScript + Quasar 前端——架構分層、composable 抽取、DevTools 除錯、i18n、OpenSpec |
| [database-sqlserver](./plugins/database-sqlserver/README.md) | 0.1.0 | SQL Server——table/view 撰寫慣例、TableDescription 生成、EF Core migration 與疑難排解 |
| [ui-ux](./plugins/ui-ux/README.md) | 0.1.1 | UI/UX 設計知識庫——風格系統、版面、配色、互動慣例、資訊呈現 |
| [desktop-avalonia](./plugins/desktop-avalonia/README.md) | 0.1.0 | Avalonia 桌面 .NET——MVVM 慣例、跨平台路徑、建置與發佈 |
| [toolkit](./plugins/toolkit/README.md) | 0.1.0 | 通用 hooks 與分層 guard——桌面通知、session 自動命名、AskUserQuestion 品質檢查、糾正回饋收集、context 提醒、git 紅線攔截 |

### skills 與 agents

| 外掛 | skills | agents |
|------|--------|--------|
| sa-flow | `consolidate-docs` `dev-feedback` `dev-readiness` `dispatch-worker` `explore` `foxpro-analyzer` `interview-prep` `issue-triage` `linear-create` `linear-daily-report` `linear-illustrate` `linear-reply` `linear-triage` `linear-weekly-report` `live-drive` `meeting-minutes` `operation-manual` `pdf-converter` `plugin-healthcheck` `qa-sweep` `qa-verify` `requirement` `retrospective` `sample-verify` `spec-chain` `spec-docs` `specify-backend` `specify-frontend` `survey-existing-system` `system-analysis` `verifying-specs` `write-doc` | `browser-surveyor` `doc-fidelity-reviewer` `domain-advisor` `manual-explorer` `manual-reviewer` `manual-writer` `qa-fixture` `qa-planner` `qa-runner-ui` `report-writer` `scout` `silent-failure-hunter` `spec-sampler` `spec-writer` |
| dev-flow | `work-on` `feature` `implement` `spec` `commit` `review` `release` `debugging` `quality-check` `convention-first` `agent-orchestration` `context-hygiene` `worktree` `triage-branch-cleanup` `submodule-relay` `tmp-scratch` `dual-tool-mirror` | — |
| backend-dotnet | `clean-architecture` `cqrs-handler` `repository-pattern` `domain-entity` `dapper-query` `webapi-controller` `hangfire-job` `unit-testing` `tdd-cycle` | `architect` `developer` `reviewer` `tester` `debugger` |
| frontend-vue | `frontend-architecture` `vue-composables` `chrome-devtools-debug` `i18n-implementation` `release-workflow` `review-remote` `openspec-propose` `openspec-apply-change` `openspec-archive-change` `openspec-explore` | `code-reviewer` `test-engineer` |
| database-sqlserver | `table-conventions` `view-conventions` `generating-table-description` `syncing-db-entities` `ef-migration` `migration-troubleshoot` | — |
| ui-ux | `ui-ux-pro-max` | — |
| desktop-avalonia | `avalonia-mvvm` `cross-platform` `desktop-build-publish` | — |
| toolkit | — | — |

## 典型動線

需求進來 → `sa-flow` 的 `explore` → `requirement` → `system-analysis` → `specify-backend` → `specify-frontend` → `dev-readiness` → `verifying-specs` → `linear-create` 開票；
進實作後交給 `dev-flow` 的 `work-on` / `feature` 起頭，技術層面再取用 `backend-dotnet`、`frontend-vue`、
`database-sqlserver` 等對應外掛，最後回到 `dev-flow` 的 `commit` / `review` / `release` 收尾，完工後以 `sa-flow` 的 `qa-verify` 實機驗收。

## 目錄結構

```
.claude-plugin/marketplace.json   # marketplace 清單（外掛名稱、路徑、版本）
plugins/<plugin>/
  .claude-plugin/plugin.json      # 外掛 metadata
  skills/<skill>/SKILL.md         # skills，自動發現
  agents/<agent>.md               # agents，自動發現
  references/ · templates/        # 共用素材，由 skill 以 ${CLAUDE_PLUGIN_ROOT}/ 引用
  CHANGELOG.md                    # 版本紀錄，最新條目須與 plugin.json 版本一致
scripts/ci/validate.py            # 內容驗證（CI 與 pre-commit 共用）
```

開發慣例見 `.claude/rules/`：外掛結構、skill 撰寫規範（SKILL.md 300 行上限、實作邏輯放 `references/`）、
版本號與 CHANGELOG 規則（改 skill／agent／reference 時同一個 commit 內補 CHANGELOG 並 bump 版號）。

### 驗證

`scripts/ci/validate.py` 會檢查版號一致（plugin.json／marketplace.json／README／CHANGELOG）、frontmatter、
交互引用、README 的 skills 與 agents 表，以及外洩樣式（個人路徑、非範例 email、內網 IP）。
GitHub Actions 在每次 push 與 PR 時執行它與各 plugin 的腳本測試。

本機啟用 pre-commit（每個 clone 一次）：

```bash
git config core.hooksPath scripts/hooks
```

pre-commit 另會讀 repo 根目錄的 `.leak-denylist`（已 gitignore、只存在本機），一行一個不得出現的字串，
`regex:` 開頭為正規式；命中即擋下 commit。

## 授權

MIT License — Copyright (c) 2026 Kerry Huang
