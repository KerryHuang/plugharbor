# Changelog

格式：每次改動 `skills/`、`agents/`、`references/` 時，於最上方新增版本條目並同步 bump 版號（規則見 `.claude/rules/version-consistency.md`）。

## [3.1.0] - 2026-10-22

### 新增
- 新 skill `qa-sweep`：批次撈指派給我的待測票，依類別交 `qa-verify`（票面／規格模式）或 `skills/qa-sweep/references/backend-verify.md`（純後端），嚴格 PASS 自動寫回 Done 並通知父票，FAIL 整批預覽後先開 Dev 子票再退回原票；留言首行整行標記做冪等；team 與狀態名取自 `sdlc-linear-teams`，S0 先驗。
- 新 skill `survey-existing-system`：勘察現役系統某段行為，委派 scout／silent-failure-hunter／domain-advisor 蒐證後由主 session 彙整現況分析文件，結尾建議下一步。
- 新 skill `consolidate-docs`：票 Done 後把 `*_{票號}.md` CR 文件經事實驗證（`skills/consolidate-docs/references/verification-rules.md`）合併回主規格、改寫連結、清規格鏈中間產物、重產 SPEC-INDEX；預設 dry-run、不自動 commit。
- 新 agent `silent-failure-hunter`：唯讀獵捕吞例外、忽略回傳、fallback 遮蓋、只 log 不傳播、無界重試五種靜默失敗；`linear-triage`、`survey-existing-system` 派發。
- `sample-verify` 增量重驗：新增 Step 0 與 `skills/sample-verify/references/impl-anchors.md`——每份規格一個錨點檔記規則執行位置、各 repo 比對 commit 與規格內容 hash（blob），下一輪只重驗變動檔；新增 `UNCERTAIN` 類別（看不出意圖不升格 MISSING）、`--full`。
- `qa-verify` 票面模式（`--from-ticket`）：無 FFS 的 Bug 票從票面重現步驟產 TC，報告留在工作區；`--no-comment` 供 `qa-sweep` 呼叫；環境版本閘（前端 meta build sha／後端 tag）、票面指定環境改取「其他環境」帳密。
- `qa-verify` 資料斷言槽：`預期.資料斷言` 寫畫面讀不到的 DB 落地事實，`strip_plan.py` 另產 `db-targets.yml`，runner 跑完由 `qa-fixture` 唯讀查核寫 `db-check.yml`（`_meta.通道` 必填），judge 併入判定。
- `references/doc-boundaries.md`：新增「票↔文件雙向註記」。
- `shared-preludes-details.md` 中間產物表新增「實作錨點」列。

### 變更
- `spec-sampler`：橫切規則（權限、交易、稽核）本組找不到時先查全域 filter／middleware／pipeline 與它對本端點的實際判定；回應對映層不歸 INFRASTRUCTURE；回報新增 UNCERTAIN 與錨點表。
- `qa-verify` 收尾建議下一步新增 `consolidate-docs`；`judge.py`／`validate.py` 新增「等於目標」比對與佔位符期望檢查。

## [3.0.0] - 2026-10-22

### BREAKING
- 承接 2.2.0 的 plugin 改名 `sdlc` → `sa-flow`（skill／agent 引用改為 `sa-flow:<名稱>`）。改名屬不相容變更，依版號規則本版起升 major；2.2.0 條目保留不改寫。

### 新增
- 新 skill `dispatch-worker`：用 herdr 開 pane 跑另一個完整 CLI session（claude／codex）並派工。含 Step 0 開 pane 前數活著的 worker（≥3 先問）、`herdr_layout.py` 依 worker 數重排（主 session 最大、★ 標籤）、claude worker 寫完結果檔後主動 `SendMessage` 回報主 session（要問人前先發「在問」）、`--timeout` 必配 `--wait`、worker context > 250K 時的中途交接（寫 `_handoff` → `/clear` → 接續）、worker 不自刪暫存。
- 新 skill `spec-chain`：跨 session 協調多棒規格鏈（判現況、定路由、派 worker、盯狀態、五項驗收、收工），`_pm-run.json` 執行狀態與 `pm_resume.py` 續跑對帳、`ctx.py` 量 context；驗收第 4 項跑決策傳播機械閘；開票前暫定題先交 `domain-advisor`（`mode: triage`）分流；暫停／恢復／狀態固定做法；`verifying-specs` 棒以 sonnet 起。
- 新 skill `spec-docs`（原排批 3，因 `spec-chain` 驗收依賴而提前）：規格文件分章定向讀寫與 SPEC-INDEX 格式、章節編號檢查。
- 雙顧問討論：同一支 `domain-advisor` 開兩個實例，`lens: business-flow`（業務流程）／`data-boundary`（資料與系統邊界）各自提出爭點後交叉回應，最多 5 輪、主持人依結局表判、交使用者才一次一題問。新增 `references/advisor-discussion.md`、`scripts/advisor_last_reply.py`（＋測試）；`consultant-desk.md` 新增編制選項、「雙顧問討論」與「校準與證據」兩節。
- `domain-advisor` 新增 `discuss-open`／`discuss-reply` 模式與通用校準：通用預設以內的偏離照預設裁定，通用預設以外的偏離才交 PO；補 `Bash`（只做唯讀搜尋）。

### 變更
- `check-decision-propagation.py` 新增 R5（暫定 D 正文要帶「（暫定，D-xxx 待確認）」、定案 D 不殘留）、R6（文件資訊版本＝CHANGELOG 最高版本），並修正 CHANGELOG 在檔頭時正文被整段丟掉的問題；新增 `test_check_decision_propagation.py`。`verifying-specs`、`decision-record.md` 同步說明；`spec-writer` 自檢新增 DP（交件前跑此腳本）。
- `chain-profile.md`：lite 判準 2 不把軟刪除與既定的復活／建新列處置算狀態機；「有疑慮一律 standard」改為點名哪一條由 PO 判一次；票面產出物列了 SAD 不算使用者指定 standard。`requirement` 9.8 同步；SA 票範本的 SAD 列只在 `chain_profile=standard` 時列。
- 互動詢問一次一題的殘留引用一併改掉：`dev-readiness` Task 6 改逐條問、`requirement`、`specify-backend`、`pipeline`、`handoff-protocol`、`boundary-dimensions`、`decision-record` 不再引用「同質獨立裁決可批次」。
- `shared-preludes-details.md`「規格鏈中途裁決」補回寫樣板指路與「決策傳播檢查通過後再開票」。

## [2.2.0] - 2026-10-22

### BREAKING
- **plugin 改名 `sdlc` → `sa-flow`**：目錄 `plugins/sa-flow`、`plugin.json`／`marketplace.json` 的 name、Pi 套件名 `kerryhuang-sa-flow`、README 全數改名；skill／agent 引用由 `sdlc:<名稱>` 改為 `sa-flow:<名稱>`（含 `subagent_type`、斜線指令）。已安裝舊名者須移除 `sdlc` 後重裝 `sa-flow`。
- 專案設定鍵（`sdlc-docs-path`、`sdlc-linear-*` 等）**不改名**，既有專案 `CLAUDE.md` 設定照常生效。
- 版號依指示採 minor bump；改名本身屬不相容變更。

## [2.1.0] - 2026-10-22

### 新增
- `references/analysis-rigor.md`：上游分析下結論前的六條嚴謹度閘（來源查齊、深度到源頭、現況對齊、維度齊全、domain 邊界必叫顧問、證據優先）、結論分級與踩雷細則索引；`shared-preludes.md` 加一節指路，`consultant-desk.md` FRD 例外改指此檔。
- `hooks/agent-model-guard.py`（＋`hooks.json`、測試）：派通用 subagent（general-purpose／Explore／Plan／claude）沒指定 model 時補 `sonnet`；專用 agent、fork、明確指定者不動，解析失敗 fail-open。
- `domain-advisor` 新增 `mode: triage`：規格鏈開票前逐題分流暫定決策（撤題／顧問裁定／交 PO）。

### 變更
- **問題漏斗：實證 → 顧問 → 使用者**（`shared-preludes` 常駐卡與 details）：每題先用一手證據驗證問題本身，證據推翻前提就撤題；實證後仍要判斷的交 domain 顧問；兩層都解不了才問使用者，題目附「已查過什麼、顧問怎麼看」。推導來源補第 ④ 項「現行 codebase」。
- **平台／UI 慣例以現行 codebase 為準**：分頁、格式、對話框、匯出列印、錯誤與空狀態照既有先例直接定案、附檔案路徑，不提問、不記暫定。
- **規格鏈中途裁決：暫定不停下，開票前集中問**（details 新節）；`decision-record.md` 決策表加 `狀態` 欄（`定案`／`暫定`）、「暫定決策」與「引用他鏈決策」兩節，`拍板` 欄新增 `證據`。
- **互動詢問一律一次一題**：移除「同質獨立裁決批次表決」；新增第 5 條「題目自明」（自帶背景、白話先行代碼放括號、選項寫後果、一題一件事）。
- `dispatch-conventions.md`：§四翻案級斷言採信前自己 grep；§五 agent 紀律（不刪暫存、只用清單內工具、找檔先看頂層、長 python 先落檔、SQL 帶 `DB_NAME()` 與 `TOP N`）；主 session 長 python 同樣落檔。`spec-writer`／`report-writer` 加不刪暫存與無 `Edit` 的寫法。
- `skill-design.md`：平行派工第 5 件事（fork skill 前景派發）、「skill 要主動提議，不靠使用者記得時機」、「攔截／確認類 hook 除了 exit 2 任何失敗都是放行」。
- 流程型 skill 結尾補「完成後依動線用 AskUserQuestion 建議下一步」：`qa-verify`、`foxpro-analyzer`、`meeting-minutes`、`interview-prep`。
- `verify-against-source.md` 新增「缺席長得像成功」；`analysis-standards.md` 新增「集合性質不能逐列篩選」。
- 模型與上限：`spec-writer` opus→sonnet、`verifying-specs` 釘 `model: sonnet`（不隨主 session 漂移）；`qa-runner-ui` maxTurns 150→350、`manual-explorer` 150→300，`scout` 新設 100、`spec-sampler` 新設 80（依實測用量約 2 倍）。
- `verifying-specs`：修正棒逐條對 `file:line` 親手改、不派 subagent 整章重寫；單文件 `--full`／`--recheck` 連續第三輪就停。

## [2.0.0] - 2026-10-01

### BREAKING
- `specify` 拆為 `specify-backend`（BFS）與 `specify-frontend`（FFS）。
- `linear-ticket-defaults.md`、`linear-workflow.md` 移至 `skills/linear-create/references/`。

### 架構
- 主 session 統整派工、`spec-writer` agent 落檔、每棒載入 `references/shared-preludes.md`。
- 勘察產物共用 `{功能目錄}/analysis/`；依功能規模走完整鏈或 lite 鏈（`chain-profile.md`）。

### 新增
- skills：explore、interview-prep、dev-readiness、qa-verify、live-drive、operation-manual、linear-triage、linear-reply、linear-illustrate、linear-daily-report、linear-weekly-report、issue-triage、dev-feedback、meeting-minutes、sample-verify、pdf-converter、write-doc。
- agents：spec-writer、domain-advisor、scout、report-writer、spec-sampler、doc-fidelity-reviewer、browser-surveyor、qa-planner、qa-runner-ui、qa-fixture、manual-explorer、manual-writer、manual-reviewer。
- references：legacy-parity、decision-record、boundary-dimensions、verify-against-source、spec-dedup-and-budget 等。
- Pi harness 對照（`references/harness-terms.md`、`package.json`）與 `scripts/test_harness_neutral.py`。

### 變更
- Linear team／label／assignee 改由專案 `CLAUDE.md` 設定或執行時查詢，不再寫死。
- 選配整合（Linear、chrome-devtools、唯讀 DB、Graphify）不可用時降級或跳過。

> 2.0.0 之前的版本未逐版記錄。
