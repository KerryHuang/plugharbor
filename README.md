# plugharbor

所有 AI 工作模式的唯一來源：11 個 plugin（工作流、職責＋技術棧附錄、hooks、guard、reviewer、寫作、研究、UI 規範）加上 user 層設定（`setup/`），
同一份內容由 Claude Code、Codex、pi、agy 共用。Claude Code 直接走 marketplace，其他三個由 `setup/install.sh` 註冊與同步。

plugin 分兩層：工具類（toolkit、research、browser-docs、workspace）裝在 user 層，每個專案都有；其餘 7 個是專案層，用 `setup/install-project.sh` 依專案安裝。

## 安裝

新機器一行安裝（clone 到 `~/plugharbor`，再執行 `setup/install.sh`，自動偵測有裝的 CLI）：

```bash
curl -fsSL https://raw.githubusercontent.com/KerryHuang/plugharbor/main/setup/bootstrap.sh | bash
```

只想用 Claude Code 的 plugin、不要 user 層設定：

```bash
claude plugin marketplace add https://github.com/KerryHuang/plugharbor.git
claude plugin install workspace@plugharbor                # user 層
cd <專案> && claude plugin install lifecycle@plugharbor --scope local   # 專案層，只在這個專案啟用
```

安裝後 skills 會自動被發現，用 `/` 或自然語言觸發即可；agents 由主流程按需求派工。
`install.sh` 的行為與 user 層設定見 [setup/README.md](./setup/README.md)，各 CLI 的差異見 [docs/agent-parity.md](./docs/agent-parity.md)。

### 新機器清單

`bootstrap.sh` 只管 plugharbor 本身；認證或機器特定的項目刻意不管，照順序手動做：

1. **前置**：Git（Windows 用 Git for Windows，下列指令在 Git Bash 執行）；Python 3（toolkit 所有 hook 含 guard、pi packages 註冊與 `settings.json` 合併都需要；沒有的話 install.sh 會 WARN，但 hook 會靜默放行、guard 形同沒有，務必先裝）；Node（可選，Codex／pi／agy 的 user 層副本需要）；各 CLI 本身（Claude Code、Codex、pi、agy）自行安裝並登入。
2. **一行安裝**：上面的 `curl … | bash`，裝 user 層 4 個 plugin。可用環境變數 `PLUGHARBOR_SRC` 改 clone 位置、`PLUGHARBOR_PLUGINS="toolkit research"` 改 user 層要裝哪些；`install.sh --check` 只比對不改。
   **專案層**：在常用專案各跑一次 `bash ~/plugharbor/setup/install-project.sh <專案根> lifecycle backend …`（預設只自己用，`--shared` 寫進專案設定與團隊共用）。
3. **其他 marketplace**（Claude Code 登入後）：`claude plugin install superpowers@claude-plugins-official`；其餘依需要。
4. **通用 MCP**（金鑰與登入各自處理，不入版控）：例如 `claude mcp add --scope user chrome-devtools -- npx -y chrome-devtools-mcp@latest`。
5. **終端工具**（macOS，選用）：`brew install herdr`（有裝 herdr，install.sh 會連結側欄 plugin）；用 graphify skill 才需要 `uv tool install graphifyy`。
6. **herdr 設定**：`setup/herdr/config.toml` 不會自動覆蓋，對照後手動改 `~/.config/herdr/config.toml`（`new_cwd` 等各機器不同）。有用 pi 的話，把 `setup/herdr/pi/herdr-tree.ts` 加進 `~/.pi/agent/settings.json` 的 `extensions`。
7. **pi 的 user 層規則**（有用 pi 才需要）：adapter 只產生 `APPEND_SYSTEM.md`，`~/.claude/rules` 要靠外部的 pi-code 套件（其 `claude-rules.ts`）載入。依該套件文件，把 pi-code 加進 `~/.pi/agent/settings.json` 的 `packages`，否則 pi 讀不到 rules。
8. **Codex**：第一次跑完 install 後，在 Codex 執行 `/hooks` 信任新註冊的 hook，否則不會執行。
8. **開發機**（要改 plugin 才需要）：`git config core.hooksPath scripts/hooks`；`.leak-denylist` 從自己的備份放回 repo 根目錄，否則 pre-commit 的外洩掃描少一層。

之後升級：`bash ~/plugharbor/setup/bootstrap.sh`（pull 後重跑 install；版號變了才重裝）。

## 外掛一覽

| 外掛 | 版本 | 內容 |
|------|------|------|
| [lifecycle](./plugins/lifecycle/README.md) | 2.0.1 | 軟體交付生命週期——需求探索、規格、票務、實作、發版、QA 實機驗收、操作手冊與會議記錄；規模可調（lean／full），票務工具可換（Linear／GitHub／Jira） |
| [workspace](./plugins/workspace/README.md) | 1.5.1 | git 與工作區工具＋輕量開發核心——commit、worktree、分支清理、暫存檔、context 治理、除錯、審查、品質檢查、跨平台、無人值守 |
| [backend](./plugins/backend/README.md) | 1.0.3 | 後端——分層架構、CQRS、資料存取、領域模型、API 端點、背景作業、單元測試；附 .NET 附錄 |
| [frontend](./plugins/frontend/README.md) | 1.0.2 | 前端——架構分層、元件邏輯抽取、i18n、執行期除錯；附 Vue 附錄 |
| [database](./plugins/database/README.md) | 1.0.2 | 資料庫——schema 慣例、migration、ORM 同步、資料表說明；附 SQL Server／PostgreSQL／MySQL／SQLite 方言與 EF Core 附錄 |
| [ui-ux](./plugins/ui-ux/README.md) | 1.0.2 | UI/UX 設計知識庫與畫面規範——風格系統、版面、互動慣例、設計新畫面、唯讀審查；受眾（如兒童）規範以附錄載入 |
| [desktop](./plugins/desktop/README.md) | 1.0.1 | 桌面應用——MVVM、建置與發佈；附 Avalonia 附錄 |
| [toolkit](./plugins/toolkit/README.md) | 0.18.0 | 通用 hooks 與分層 guard、設定健檢與 agent 派工 skills（派工路由與額度改派）、reviewer agents——桌面通知、session 自動命名、AskUserQuestion 品質檢查、糾正回饋收集、context 提醒、失敗迴圈提醒、git 紅線攔截 |
| [research](./plugins/research/README.md) | 0.5.1 | 探索與研究——graphify 知識圖譜、ai-radar AI 情報雷達（週版＋工作日消化採納待辦的每日版）、plugin-harvest 吸收外部 plugin 做法 |
| [blog](./plugins/blog/README.md) | 0.1.0 | 部落格寫作流程——收素材、寫白話初稿、上線前檢查 |
| [browser-docs](./plugins/browser-docs/README.md) | 0.3.3 | 瀏覽器實機操作與文件轉檔——Chrome 實機驅動與畫面勘察、截圖標註與脫敏、PDF 轉檔與擬真度驗證 |

### skills 與 agents

| 外掛 | skills | agents |
|------|--------|--------|
| lifecycle | `consolidate-docs` `demo-video` `dev-feedback` `explore` `implement` `interview-prep` `meeting-minutes` `operation-manual` `plugin-healthcheck` `prototype-html` `qa-verify` `release` `spec` `spec-chain` `spec-check` `survey-existing-system` `ticket-create` `ticket-ops` `ticket-reply` `ticket-report` `triage` `write-doc` | `architect` `debugger` `developer` `domain-advisor` `manual-explorer` `manual-reviewer` `manual-writer` `qa-fixture` `qa-planner` `qa-runner-ui` `report-writer` `reviewer` `scout` `silent-failure-hunter` `spec-sampler` `spec-writer` `tester` |
| workspace | `commit` `review` `debugging` `quality-check` `convention-first` `agent-orchestration` `context-hygiene` `worktree` `triage-branch-cleanup` `submodule-relay` `tmp-scratch` `dual-tool-mirror` `cross-platform` `unattended` | — |
| backend | `layered-architecture` `cqrs` `data-access` `domain-model` `api-endpoint` `background-job` `unit-testing` | — |
| frontend | `frontend-architecture` `component-logic` `i18n` `runtime-debug` | — |
| database | `schema-conventions` `migration` `orm-sync` `schema-docs` | — |
| ui-ux | `ui-ux-pro-max` `designing-ui` `auditing-ui` | — |
| desktop | `mvvm` `build-publish` | — |
| toolkit | `agent-dispatch` `agent-mesh-check` `config-doctor` `context-diet` `feedback-review` `handoff` `retrospective` `tidy-memory` `transcribe` | `claudemd-reviewer` `hook-reviewer` `rule-reviewer` `skill-reviewer` `subagent-reviewer` |
| research | `ai-radar` `graphify` `plugin-harvest` | — |
| blog | `blog-capture` `publish-check` `write-post` | — |
| browser-docs | `annotate-screenshot` `live-drive` `pdf-converter` | `browser-surveyor` `doc-fidelity-reviewer` |

## 典型動線

需求進來 → `lifecycle` 的 `explore` → `spec` → `spec-check` → `ticket-create`（經 `ticket-ops` 換成專案的票務工具）；
進實作由 `lifecycle` 的 `implement` 起頭（規劃與執行交給 superpowers，建議安裝），技術層面再取用 `backend`、`frontend`、
`database`、`desktop` 等職責外掛（自動載入專案技術棧的附錄），最後以 `workspace` 的 `commit`／`review` 與 `lifecycle` 的 `release` 收尾，完工後以 `lifecycle` 的 `qa-verify` 實機驗收。規模預設 lean（一份規格、一張票），設 `scale: full` 走 FRD→SAD→BFS→FFS 與四角色票樹。

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
