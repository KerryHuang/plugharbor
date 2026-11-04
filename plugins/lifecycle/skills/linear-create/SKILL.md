---
name: linear-create
description: "依自然語言描述建立 Linear 票樹（Feature：PM→SA→QA→Dev；Bug：QA→Dev），票面只放重點與規格指路。觸發：「開票」「建票」「我要開一張票」「create ticket」「linear-create」。"
argument-hint: "{自然語言描述}"
model: sonnet
---

# Linear 開票

> 非 Claude Code（如 Pi）執行時，先讀 `../../references/harness-terms.md`（相對本檔；Claude Code 為 `${CLAUDE_PLUGIN_ROOT}/references/harness-terms.md`，照字面執行可略過），把 Claude 專屬工具與路徑換成對應項。

透過自然語言描述自動判斷票類型，互動式引導收集資訊，建立完整票層級結構。
互動詢問一律依 `${CLAUDE_PLUGIN_ROOT}/references/shared-preludes.md` §互動詢問規範（AskUserQuestion＋建議置首＋一次一題）。

**Feature 票樹**：`PRD-123【需求】→ (SPC-xxx【規格】, QAT-456【測試】)`，`QAT-456 → (DEV-789【後端】, DEV-790【前端】← Blocked by DEV-789)`（範例票號前綴 PRD／SPC／QAT／DEV 僅為示意，實際依各 team 的 key）。**相依方向**：blockedBy 掛在有先後關係的**非父子票**之間（前端 ← 後端，含不在本批的既有後端票；來源文件寫明的相依；一次建齊另加第一個 Dev 票 ← SA，見 Step 8.5）；`SA→QA`、`QA→Dev` 的先後靠**父票 rollup**（子票 2/2 才收尾）保證，不掛 blockedBy，QA 無自己的 blockedBy。完整樹狀圖與規則 → `references/ticket-flow.md`。

**Bug 票樹**（無 SA 階段）：根票可為 **QA**（現行 `QA → Dev`）或 **PM**（既有 PM Bug 根票 → `PM → Dev`，**不強制補開 QA 票**），**驗收人＝開票人**；詳見 `references/ticket-flow.md` §Bug 流程。

- **票預設值與描述範本**：見 `references/linear-ticket-defaults.md`
- **工作流程規範**：見 `references/linear-workflow.md`

## 輸入參數

```
$ARGUMENTS → {自然語言描述}
```

| 參數 | 必填 | 格式 | 說明 |
|------|------|------|------|
| 自然語言描述 | 是 | 任意文字 | 描述要建立的功能或問題，AI 自動判斷票類型 |

## 工作流程

### 1-2. 前置檢查

`$ARGUMENTS` 為空 → 提示輸入描述並終止。用 `ListMcpResourcesTool` 確認 Linear MCP 可用（名稱含 "linear"）；未找到 → 提示設定 `.mcp.json`，終止。

### 2.5 讀專案設定（Team 與 Assignee）

讀目標專案根目錄 `CLAUDE.md`（與 `sdlc-docs-path` 同一處）的三個鍵，格式見 `references/linear-ticket-defaults.md` §專案設定：

- `sdlc-linear-teams`：各票種開在哪個 team。SA 可與 PM 同 team——沒有獨立 SA team 時 SA 票開在 PM team，票號前綴跟著 team 走。
- `sdlc-linear-assignees`：Feature QA 票、Dev 後端／前端票的 assignee。
- `sdlc-linear-labels`（選填）：各票種的必要 label。

解析優先序：**專案設定 → defaults 檔裡已替換的值 → 動態解析**（team 用 `list_teams` 讓使用者選；assignee 走 Step 5.5）。設定的 team 名稱不在 `list_teams` 結果裡 → 停下告知使用者，不要猜。狀態 ID 一律依 team 用 `list_issue_statuses` 查，不寫進設定。

### 3. AI 判斷類型 + 確認

分析 `$ARGUMENTS` 判斷 Feature 或 Bug，**必須**使用 `AskUserQuestion` 確認：

- **question**：「請確認票類型」
- **header**：「票類型」
- **multiSelect**：false
- **options**：`Feature（PM → SA、QA → Dev）` / `Bug（PM/QA → Dev）`——AI 判定的類型放第一位標「（推薦）」，一行判定理由寫進該選項 description

### 3.6 同族票推導（**必做，在任何發問之前**）

依 `${CLAUDE_PLUGIN_ROOT}/references/shared-preludes.md`「先推導，再詢問」，本 skill 多數設定值**查得到，不必問**：用 `list_issues` 找**同族既有票**（同型功能／同模組的 PM 或 Dev 票），對其中一張 Dev 票 `get_issue`，一次取得整組慣例：

```
list_issues(query="<同型功能關鍵詞>", fields=["id","title","labels","priority","estimate","project","status","dueDate","assignee","team"])
```

**不問**（沿用同族值）：Labels（同 team 組合）、優先級（同族全同一級時沿用；想確認排序意圖才問）、Estimate 級距（當基準，步驟 8 自行判定）、Due date SLA（建立日→到期日天數反推）、標題格式與描述結構（實際寫法沿用，格式仍以範本為權威）、開發範圍（FFS／BFS 是否存在判定）、需求分析狀態（有無 SAD／BFS／FFS 判定）、票類型（使用者描述已指明或由有無 FRD 判定）。**要問**：Project（同族各掛不同專案時無法推導）。

> ⚠ **同族票只供在地化參數，不供格式與結論**——照抄同族票的描述結構，會把它缺定位行、標題重複之類的毛病一起複製過來。

**推導不到才進入下方各步驟發問**；推導得到的，在步驟 8 草稿摘要中列出「依據某某票推導」供覆核。

### 3.5 既有票盤點與結構校正（必做）

開新票前先盤點既有票：有票號 → `get_issue` 讀根票與既有子票；無票號 → `list_issues` 關鍵字搜，避免重複開票。對照應有票樹盤出**缺票**（列入補開）、**內容錯位**（既有 Dev 票內容與職責不符，如前後端問題混寫 → 依對應 Dev 票範本重寫描述）與**缺漏的 blockedBy**（依 8.5）；**修正僅限 Dev 票**，原始 PM/QA 票一律不調整。差異清單併入步驟 8 草稿預覽、步驟 9 一併執行；既有根票存在時本次建票一律掛其下，**不另建新根票**。詳細判準與程序見 `references/ticket-flow.md` §既有票盤點與結構校正。

### 4. 詢問優先級

使用 `AskUserQuestion` 詢問優先級。**預設值依票型，且必須放第一個選項**：Feature 預設 `Normal`（1.Normal 2.High 3.Urgent 4.Low，避免 Urgent 排最前被誤選）；Bug 預設 `Urgent`（1.Urgent 2.High 3.Normal 4.Low）。仍然要問，使用者改選的值優先；建票時 `save_issue` 的 `priority` 值 Urgent=1、High=2、Normal=3、Low=4，一律以本步驟選定值為準。

### 4.4 詢問需求分析狀態（Feature 限定）

初始狀態依「**需求分析是否已完成**」大幅不同（見 `references/linear-ticket-defaults.md` §初始狀態決策）。**必須**使用 `AskUserQuestion` 詢問：

- **question**：「需求分析是否已完成？」
- **header**：「分析狀態」
- **multiSelect**：false
- **options**：
  1. `已完成分析（已在 PM 票內完成）` — **不另開 SA 票**；建 Dev 樹時 PM → `In Progress`、QA/BE = `Todo`、FE = `Todo`/`Blocked By BE`（可開工）
  2. `尚未分析` — 需開 SA 走分析（PM → `In Refinement`、SA → `Todo`），或整棵先 parked 在 `Backlog`

此答案（`analysis_done`）於 Step 4.5、Step 9 決定 SA 是否建立與各票初始狀態。Bug 類型跳過本步驟（無分析階段）。

### 4.5 詢問建票範圍（Feature 限定）

Feature 採**分階段開票**。**必須**使用 `AskUserQuestion` 詢問本次要建立的票範圍（選項依 Step 4.4 `analysis_done` 調整；狀態結果見 `references/linear-ticket-defaults.md` §Feature 情境對照）：

- **question**：「本次要建立哪些票？」
- **header**：「建票範圍」
- **multiSelect**：false
- **options**：
  1. `只開 PM 票（需求提出）` — 只開 PRD-xxx，單開 → `Backlog`；下游之後再補
  2. `開 PM + SA 票（啟動分析）`（`analysis_done=尚未` 時）— PM → `In Refinement`、SA → `Todo`；QA/Dev 之後再補
  3. `建 Dev 樹（QA + Dev）`（`analysis_done=已完成` 時）— 不開 SA；PM（既有則**更新**、或同批新建）→ `In Progress`，QA/BE = `Todo`、FE = `Todo`/`Blocked By BE`
  4. `一次建齊` — PM/QA/Dev（＋視 analysis_done 決定 SA）全部建立：
     - `analysis_done=已完成` → 不開 SA；PM `In Progress`、QA `Todo`、BE `Todo`、FE `Todo`/`Blocked By BE`（可開工）
     - `analysis_done=尚未` → **詢問是否建 SA**：建 SA → PM `In Refinement`、SA `Todo`、QA/BE/FE `Backlog`（並對第一個 Dev 票掛 `blocked by SA`）；不建 SA → 全部 `Backlog`

Bug 類型跳過 4.4 / 4.5。根票依步驟 3.5 盤點結果：**既有 PM/QA Bug 根票 → 直接在其下開 Dev 票（不強制補開 QA）**；無既有根票 → 新建 QA 根票 + Dev。狀態：QA（若建）`Todo`、BE `Todo`、FE `Todo`/`Blocked By BE`；**驗收人＝根票開票人**（既有根票 assignee 不動）。後續 Step 5（Labels）、Step 9（建票）依選定範圍與 `analysis_done` 動態調整。

### 5. 詢問 Labels（依 Team 分開，**僅對 Step 4.5 選定範圍內的 Team**）

對每個將建立的 Team 呼叫 `list_issue_labels`（傳 `teamId`）取得該 Team 完整 Labels 列表。各 Team **必要 Label** 取自專案設定 `sdlc-linear-labels`（格式見 `references/linear-ticket-defaults.md` §Labels 預設規則）；未設定的票種沒有必要 Label，由使用者從清單自選（可跳過）。

對每個 Team，**必須**使用 `AskUserQuestion`（不可用純文字 prompt 模擬）：question「【{Team 名稱}】請選擇要套用的 Labels」／header `{Team} Labels`／multiSelect＝true／options 列出該 Team 全部可用 Labels，有設定必要 Label 的，放最前並於後方加「（必要）」，使用者未勾選時自動補上，不再詢問。

Bug 類型：僅詢問本次實際要新建票的 Team（QA 根票不新建則跳過 QA）；既有 PM/QA 根票不改 label，一律跳過 PM Labels 詢問。

### 5.5 Assignee 解析（fallback：專案設定與 defaults 都沒有時）

Step 2.5 的 `sdlc-linear-assignees` 沒有該票種，且 `references/linear-ticket-defaults.md` 的 assignee 仍是佔位符（`{SA_assignee}` 等未替換），對該票種改為動態解析：
`list_users` 依該票種 Team 過濾（MCP 不支援 teamId filter 就取全體後自行篩）→ `AskUserQuestion`
「【{Team}】請選擇 {票種} Assignee」（單選，主要負責人置首標「（推薦）」）→ 選定 id 暫存，同票種不再問。
PM 票（Feature）與 QA 票（Bug）固定 `"me"` 不適用；佔位符已替換者直接用設定值；
`list_users` 失敗 → 改回 `"me"` 並於結果報告標註需手動指派。

### 6. 詢問 Project（可選）

`list_projects` 取進行中（非 canceled／completed／paused）且 `targetDate` 未設或 ≥ 今天的專案；
無符合者直接跳過不問。有 → `AskUserQuestion`「請選擇要關聯的 Project（可跳過）」（單選；
label 含「{名稱}（截止：{targetDate 或「無」}）」，最相關者置首標「（推薦）」，末項 `不關聯 Project`）。
選定的 Project 套用至**所有**建立的票。

### 7. 詢問開發範圍

使用 `AskUserQuestion` 詢問（1. 僅後端 2. 僅前端 3. 前端 + 後端）——依需求／根因內容預判範圍，預判項放第一位標「（推薦）」＋一行理由。

### 8. 生成各票描述草稿

#### 內容來源

1. **搜尋已完成的文件**（FRD／SAD／BFS／FFS 與其 CR 變體；路徑從 `{docs-root}`〔專案 CLAUDE.md 的 `sdlc-docs-path`〕往下找）。讀取**一律定向**：各票種只讀下表列出的取材章，不整檔載入。使用者指定或需求出處的設計／計畫文件，另讀其相依表或相依章節全段；連同 Step 3.5 已取得的根票與既有 Dev 票描述，供 8.5 推導相依。
2. 若找到文件，在對應票描述中**附上文件路徑**
3. 範本取用：**先讀 `references/linear-ticket-defaults.md` 檔頭的章節索引**，再 `sed -n '/^## {票種}描述範本/,/^## .*描述範本/p'` 只取該票種段；無已完成文件時按該段從自然語言生成

#### 各票描述

| 票種 | 取材章（定向讀取，只讀這些） | 範本參考 | 須附文件路徑 |
|------|------------------------------|----------|:---:|
| PM 票（Feature） | FRD §0／§1／§2；畫面指向 FFS §2 或原型 | §PM 票描述範本 | FRD |
| SA 票（Feature） | FRD §0；三流各一句，明細在 SAD | §SA 票描述範本 | FRD、SAD |
| QA 票 | FRD §2 → 單一 E2E 情境表（含資料落地與回歸點） | §QA 票描述範本 | FRD |
| Dev 後端票 | BFS §0／§6 端點總覽／§5.4；契約與規則以「規格明細」指路 | §Dev 後端票描述範本 | BFS、SAD |
| Dev 前端票 | FFS §2 頁面總覽與操作表／§6 端點；欄位群以「規格明細」指路 | §Dev 前端票描述範本 | FFS、BFS |

**票描述原則**：票面只放「要交付什麼、對齊哪條需求、去哪查明細」，規格明細用「文件 §章節」指路不抄進票；AC ≤5 條對齊 US／BR；QA 票只寫 E2E 情境表；Bug 票必附程式碼定位三段；技術中立。完整六條與定位行、參考文件表格式見 `references/linear-ticket-defaults.md` §票描述原則。

草稿除新建票外，**須含步驟 3.5 盤出的校正項**：各既有 Dev 票的修正前後重點對照（含 blockedBy）、補開票清單；並依 `references/linear-ticket-defaults.md` §Estimate（Story Points）預設規則對**每張 Dev 票**判定估點（Fibonacci 1/2/3/5/8/13/21，前後端各自估），於草稿摘要一併列出（**不另行詢問**，要改在草稿確認時提出；≥13 標「建議拆票」）。

### 8.5 相依推導（必做，併入草稿確認）

先後依賴一律寫成 `blockedBy`（`relatedTo` 只表示相關，可並存但不能代替），不留在描述文字裡——Linear 只有 blockedBy 會在 blocker 完成時推 unblock 通知（依賴只寫在描述文字、或只掛 relatedTo 的票，blocker 完成時都沒有人被通知）。逐張票問「它開工前要等誰完成」：

1. **前端等後端**：前端票依賴的後端票，不論是同批新建還是既有後端票（Step 3.5 盤到、使用者描述或來源文件點名的票），都掛 `blockedBy`。有後端 blocker 未 Done／Canceled 時，前端原本會是 `Todo` 的情境改為 `Blocked By BE`（無此 state 則 `Todo`）；`Backlog` 情境維持 `Backlog`，blockedBy 照掛。後端票已 Done 或 Canceled → 不掛。
2. **來源文件的相依**：Step 8 讀到的來源（設計／計畫／規格文件、根票與既有 Dev 票描述）用相依表或文字（如「依賴 WS2、WS3」）描述的先後關係，逐條翻成對應票之間的 `blockedBy`（被依賴的一方是 blocker）；對不到票的相依列為待確認，不可略過。
3. **一次建齊・含 SA**：第一個 Dev 票（後端優先）另掛 `blockedBy` = SA 票。
4. 父子之間不掛（`SA→QA`、`QA→Dev` 靠父票 rollup）；QA 永不掛。

草稿摘要附**相依表**（每張票：blockedBy 哪幾張、依據是同批後端／既有票號／文件章節），連同草稿用 `AskUserQuestion` 呈現；確認後的相依表無自我依賴、無循環，才寫 ticket-plan。

### 9. 建票（**派 subagent，主 session 不呼叫 `save_issue`**）

把確認後的草稿寫成 ticket-plan 檔，派 subagent 照檔建票，只收回票號表——每呼叫一次 `save_issue` 都要重讀主 session 整份 context，逐張跑會放大成本。ticket-plan 格式、派工樣板、建票規則（票源 flag、SLA、estimate fallback、狀態 ID）→ `${CLAUDE_PLUGIN_ROOT}/skills/linear-create/references/create-dispatch.md`。subagent 必須遵守四條規則，主 session 只看回報表的備註欄核對，不要再逐張 `get_issue`：描述最後一行的票源 flag、Dev 票與 Bug 樹 QA 票的 dueDate、Dev 票的 estimate（寫不進去要備註）、狀態用 ID 指定（`Blocked By BE` 查不到時 fallback 成 `Todo`）。回報表的 blockedBy 欄要與 ticket-plan 逐張一致，不一致就當建票失敗處理。

寫 ticket-plan 時由主 session 決定每張票的 state、priority（**一律**用步驟 4 選定的值）、estimate（僅 Dev 票，取步驟 8 判定值）、projectId（步驟 6 有選才帶）：

> **初始狀態（★ 依分析階段）**：由 Step 4.4 `analysis_done` + Step 4.5 建立範圍決定——單開／未分析 parked → `Backlog`；未分析要往下開 SA 分析 → PM `In Refinement`、SA `Todo`、Dev parked；**分析完成建 Dev → PM `In Progress`**（既有 PM 則更新）、QA/BE `Todo`、FE `Todo`/`Blocked By BE`；**Bug** 無分析階段，QA/BE `Todo`、FE `Todo`/`Blocked By BE`（依 8.5 第 1 條；`list_issue_statuses` 找 ID）。完整情境對照表見 `references/linear-ticket-defaults.md` §初始狀態決策。

### 10. 輸出結果

回報須含四段：票層級結構、票資訊表（只列本次建立的票，狀態依 §初始狀態決策對照）、已校正票／到期日／Points 註記、下一步（依情境提示交接動作）。票號和 URL 一律取自 Step 9 subagent 回報表，**不要**自己再 `get_issue` 查。完整格式與範例 → `references/ticket-flow.md`「開票完成報告範本」。

## 錯誤處理

建票失敗 → 顯示錯誤，列出已成功票 ID；Labels 取得失敗 → 跳過 Labels 步驟（其餘錯誤情境見上方對應步驟）。

## 使用範例

```bash
linear-create 新增訂單報價功能，需要前後端支援      # Feature
linear-create 訂單查詢頁面篩選條件無效              # Bug
```

完整開發流程 → `${CLAUDE_PLUGIN_ROOT}/references/upstream-workflow.md`。
