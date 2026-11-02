# sa-flow

Claude Code 外掛，涵蓋**軟體開發生命週期的上游與驗收**：需求探索、需求文件、系統分析、前後端規格、開發就緒度、規格驗證、開票，以及待測票批次驗收（實機驗收由 `delivery-flow:qa-verify` 執行）。

規格書一律**技術中立**：只寫行為、契約、資料語意、權限邊界與上線風險；框架、快取、鎖、佇列等手段層由開發者決定，規格中遇到手段層問題一律寫成 TD 技術決策留置。

## 安裝

```bash
# 1. 註冊 marketplace（一次性）
claude plugin marketplace add https://github.com/KerryHuang/kerryhuang-plugins.git

# 2. 安裝外掛（建議搭配 superpowers）
claude plugin install sa-flow
claude plugin install superpowers
```

## 依賴的 plugin

4.0.0 起，通用工具已抽到其他 plugin，裝 sa-flow 需一併安裝：

- `delivery-flow`：`qa-verify`、`report-writer`、`interview-prep`、`ticket-daily-report` 等
- `browser-docs`：`browser-surveyor`、`live-drive`、`pdf-converter`、`annotate-screenshot`
- `toolkit`：`agent-dispatch`（herdr 派工）、`retrospective`

`plugin.json` 的 `dependencies` 欄位宣告這三個名稱（Claude Code 會一併安裝）；Codex 與 pi 沒有對應欄位，需自行安裝，`setup/install.sh` 會裝全部 plugin。

## 專案設定

在專案根目錄的 `CLAUDE.md` 加入以下設定鍵，全部選填：

```markdown
sdlc-docs-path: ../docs
sdlc-linear-teams: PM=<team>, SA=<team>, QA=<team>, Dev=<team>
sdlc-linear-assignees: QA=<email>, backend=<email>, frontend=<email>
sdlc-linear-labels: PM=<label>, SA=<label>, QA=<label>, backend=<label>, frontend=<label>
sdlc-program-code-inventory: system/feature-inventory.md
sdlc-spec-rules-since: 2026-10-01
```

| 設定鍵 | 用途 | 未設定時 |
|---|---|---|
| `sdlc-docs-path` | 規格文件根目錄（文中稱 `{docs-root}`） | 專案內 `docs/` |
| `sdlc-linear-teams`／`-assignees`／`-labels` | 各票種開在哪個 team、指派給誰、必帶哪些 label | 執行時以 Linear MCP 查詢並讓你選 |
| `sdlc-program-code-inventory` | 功能代碼盤點文件位置（權限控管用） | 跳過功能代碼查核 |
| `sdlc-spec-rules-since` | 畫面規格新規範的生效日，早於此日且本次未觸及的畫面降為 INFO | 全部文件都適用 |

設定鍵沿用 `sdlc-` 前綴：外掛 2.2.0 由 `sdlc` 改名為 `sa-flow` 時刻意不改鍵名，既有專案的 `CLAUDE.md` 不用跟著改。

## 前置需求

| 需要 | 用在哪 | 沒有時 |
|---|---|---|
| Python 3（`python3` 或 `python`） | verifying-specs、spec-chain 等 skill 附的腳本 | 用到腳本的步驟會失敗 |
| [herdr](https://herdr.dev)（終端 agent 多工器） | `spec-chain`、顧問討論的 pane 模式（經 `toolkit:agent-dispatch`） | `spec-chain` 改成單 session 逐棒接手（見 `references/handoff-protocol.md`）；顧問討論改用 subagent 模式 |
| Linear MCP | `linear-*`、`qa-sweep`、各規格 skill 的開票與回票 | 開票、回票步驟跳過 |
| `chrome-devtools` MCP | `specify-frontend`、`requirement` 等派 `browser-docs:browser-surveyor` 勘察畫面，以及 `delivery-flow:qa-verify` 的實機驗收 | 實機步驟跳過，改用靜態證據 |
| 唯讀 DB 查詢 MCP | 規格與驗收時查 schema、抽樣實際資料 | 改讀程式碼與文件，結論標為未對過實際資料 |
| Graphify | 先查文件圖譜索引再讀原文 | 直接搜尋文件 |

除了 Python 3，其他都是選配：偵測不到就降級或跳過，不會中斷流程。

## 技能一覽

### 規格鏈

| 技能 | 用法 | 產出 |
|---|---|---|
| **explore** | `/sa-flow:explore [功能描述]` | 探索摘要（六維引導問答） |
| **requirement** | `/sa-flow:requirement [--change] {需求描述}` | FRD／CR-FRD |
| **system-analysis** | `/sa-flow:system-analysis [功能名稱或 FRD 路徑]` | SAD（工作流、資訊流、資料流） |
| **specify-backend** | `/sa-flow:specify-backend [--change] {功能描述}` | BFS／CR-BFS |
| **specify-frontend** | `/sa-flow:specify-frontend [--change] {功能描述}` | FFS／CR-FFS |
| **dev-readiness** | `/sa-flow:dev-readiness [功能目錄]` | 就緒度報告：對抗式找出邊界缺口並回寫規格 |
| **verifying-specs** | `/sa-flow:verifying-specs [文件] [--cross] [--recheck] [--quick\|--full]` | 驗證報告 |
| **spec-chain** | `/sa-flow:spec-chain [票號或功能描述]` | 跨 session 協調整條規格鏈：判現況、派 herdr worker、逐棒驗收（需 herdr） |
| **spec-docs** | 由其他 skill 引用 | 規格文件分章定向讀寫、SPEC-INDEX 格式與檢查 |

### Linear

| 技能 | 用法 | 說明 |
|---|---|---|
| **linear-create** | `/sa-flow:linear-create {描述}` | 建立票樹（Feature：PM→SA→QA→Dev；Bug：QA→Dev） |
| **linear-triage** | `/sa-flow:linear-triage <票號>` | 判型：Feature 引導進規格鏈，Bug 找根因 |
| **linear-reply** | `/sa-flow:linear-reply <票號>` | 回覆票上未答留言並回寫規格 |
| **dev-feedback** | `/sa-flow:dev-feedback [--apply] {票號}` | 開發端對票面的回饋，回頭修正 plugin |

### 實機與驗收

| 技能 | 用法 | 說明 |
|---|---|---|
| **qa-sweep** | `/sa-flow:qa-sweep [票號] [--dry-run]` | 批次撈指派給我的待測票，交 `delivery-flow:qa-verify`（FFS §8 先依 `references/ffs8-to-acceptance.md` 轉檔）或後端驗證後寫回狀態、通知父票或開 Dev 子票 |
| **sample-verify** | `/sa-flow:sample-verify <規格> [原始碼範圍] [--full]` | 抽樣原始碼驗證規格覆蓋度；有實作錨點檔時只重驗變動處 |
| **survey-existing-system** | `/sa-flow:survey-existing-system [app 路徑或行為範圍]` | 勘察現役系統某段行為，產出現況分析文件 |

### 文件工具

| 技能 | 用法 | 說明 |
|---|---|---|
| **write-doc** | `/sa-flow:write-doc [路徑]` | 把口述或既有內容落檔 |
| **consolidate-docs** | `/sa-flow:consolidate-docs [--apply] [子目錄]` | 票 Done 後把票號後綴的 CR 文件驗證後合併回主規格（預設 dry-run） |
| **foxpro-analyzer** | `/sa-flow:foxpro-analyzer {檔案路徑}` | FoxPro 舊系統分析，起頭的鏈套用 parity 模式 |

### 自我進化

| 技能 | 用法 | 說明 |
|---|---|---|
| **plugin-healthcheck** | `/sa-flow:plugin-healthcheck [--fix]` | 對照 Claude Code 官方規範的健康檢查 |

## 架構

- **主 session 統整派工**：蒐證、撰寫、審查都派給專責 agent，主 session 只做決策與驗收（`references/dispatch-conventions.md`）。
- **spec-writer 落檔**：FRD／SAD／BFS／FFS 由 `spec-writer` agent 依範本、證據檔與已拍板決策寫入。
- **雙顧問討論**：流程與資料邊界互相牽制時，同一支 `domain-advisor` 以 `business-flow`／`data-boundary` 兩個視角開場後交叉辯論，最多 5 輪收斂（`references/consultant-desk.md`、`references/advisor-discussion.md`）。
- **共用前置規則**：每一棒都先載入 `references/shared-preludes.md`（問題漏斗：實證→顧問→使用者、一次一題且題目自明、不猜測、分析嚴謹度閘、權威來源優先序、技術中立）。
- **暫定決策**：規格鏈中途的裁決題採建議選項當暫定、不停下來問，開票前先交顧問分流再集中問（`references/decision-record.md`「暫定決策」）。
- **分析產物共用**：勘察結果落在 `{功能目錄}/analysis/`，下游先讀再補缺，不重複蒐證。
- **chain profile**：依功能規模走完整鏈或 lite 鏈，小功能不付大功能的流程稅（`references/chain-profile.md`）。

Agents：spec-writer、domain-advisor、scout、spec-sampler、silent-failure-hunter。

## 完整流程

```
[ sa-flow:explore ] 或 [ superpowers:brainstorming ]
         ↓
[ sa-flow:requirement ]        → FRD
         ↓
[ sa-flow:system-analysis ]    → SAD
         ↓
[ sa-flow:specify-backend ]    → BFS
         ↓
[ sa-flow:specify-frontend ]   → FFS
         ↓
[ sa-flow:dev-readiness ]      → 就緒度報告
         ↓
[ sa-flow:verifying-specs ]    → 驗證報告
         ↓
[ sa-flow:linear-create ]      → Linear tickets
         ↓
[ superpowers:writing-plans ] → 實作 → 審查
         ↓
[ ffs8-to-acceptance ]        → 驗收案例檔（FFS §8 轉中性格式）
         ↓
[ delivery-flow:qa-verify ]    → 驗收報告
         ↓
[ sa-flow:consolidate-docs ]   → CR 文件併回主規格
```

功能調整（CR）從 `requirement --change` 開始，接 `specify-backend --change`、`specify-frontend --change`，其餘相同。各棒的前置條件與交棒規則見 `references/pipeline.md` 與 `references/handoff-protocol.md`。

## 範本

| 範本 | 檔案 |
|---|---|
| FRD／CR-FRD | `templates/frd.md`、`templates/cr-frd.md` |
| SAD | `templates/sad.md` |
| BFS／CR-BFS | `templates/bfs.md`、`templates/cr-bfs.md` |
| FFS／CR-FFS | `templates/ffs.md`、`templates/cr-ffs.md` |

完整範例在 `templates/examples/`。

## 其他 harness

skills 以 Claude Code 用語撰寫。在 Pi 等其他 harness 執行時，先讀 `references/harness-terms.md` 做工具與路徑對照；`package.json` 是 Pi 的套件清單。`scripts/test_harness_neutral.py` 會擋下沒有對照的 Claude 專屬用語。

## 授權

MIT 授權 — Copyright (c) 2026 Kerry Huang
