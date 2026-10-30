---
name: linear-triage
description: "給一張 Linear 票號決定怎麼走：Feature 引導進 SDLC 管線，Bug 依 codebase／docs／DB 找根因，確認後回票並視狀態委派 linear-create 開子票。觸發：「分析這張票」「triage 票」。"
argument-hint: "<票號>"
---

# Linear 票分流派工

> 非 Claude Code（如 Pi）執行時，先讀 `../../references/harness-terms.md`（相對本檔；Claude Code 為 `${CLAUDE_PLUGIN_ROOT}/references/harness-terms.md`，照字面執行可略過），把 Claude 專屬工具與路徑換成對應項。

給定票號，讀票 → 勘察／根因分析 → 報告（含判型）→ 分流。Feature 引導進 SDLC pipeline；Bug 找根因回報。
本 skill 是**薄派工層**，不自己重寫 SDLC 或開票邏輯，全程委派既有 skill，靠確認閘道控制節奏。
**核心順序**：先讀票、追查根因、給出分析報告，判型隨報告一併給使用者確認——**不在勘察前就詢問票類型**。

## 執行通則（全程遵守）

- **過程敘事**：每個階段開始前一句話說明現在要做什麼；查證中的關鍵發現一行即報。禁止連續多個 tool call 之間毫無說明。
- **回合可見性**：使用者**只看得到「以文字收尾的回合」的內文**——回合中段文字（後面還接工具呼叫，
  **含 AskUserQuestion**）不會顯示。**長內容**（分析報告、回票草稿）必須是該回合**最後輸出**，其後不得再接任何工具呼叫，
  結束回合等使用者回應，**下一回合**才進確認閘道。**短確認**（判型、發佈、開票）可直接 `AskUserQuestion`，
  但判斷依據須一行內寫進 question 或 options 的 description，**不可依賴同回合的前置文字**；長結論禁塞 question。
- **互動詢問**：依 `${CLAUDE_PLUGIN_ROOT}/references/shared-preludes.md` §互動詢問規範——
  一律 AskUserQuestion（自由文字輸入除外）、建議選項置首標「（推薦）」、一次一題。

## 輸入參數

```
$ARGUMENTS → <ticket-id>
```

| 參數 | 必填 | 說明 |
|------|------|------|
| `ticket-id` | 是 | Linear 票 ID，例如 `ABC-564` |

---

## 執行流程

### 1. 驗證輸入

若 `$ARGUMENTS` 為空，提示使用者輸入票 ID 並終止。

### 2. 偵測 Linear MCP

使用 `ListMcpResourcesTool` 確認 Linear MCP 可用（名稱含 "linear"）。未找到 → 提示設定 `.mcp.json`，終止。

### 3. 讀取票資訊

- `get_issue` 取得票標題、描述、狀態（state）、team、優先級、parent、既有子票。
- `list_comments` 取得所有 comment（供判斷脈絡與是否已被處理）。

### 3.5 標記處理中（依票種選狀態）

有票號且票**尚未進入工作狀態**（`Backlog` / `Todo` / `Triage`）→ 立即依票種標記：

| 票種 | 標記狀態 | 說明 |
|------|---------|------|
| **PM 根票**（PM team，分析階段） | **In Refinement** | 需求分析／精煉中；**不要**直接標 In Progress——等分析完成且 Dev 票已建立（步驟 11）才轉 `In Progress` |
| 其他票（QA／Dev team …） | **In Progress** | 直接進入處理 |

依序：`list_issue_statuses`（本票 team）找目標狀態的 workflow state ID → `save_issue`（`id`=本票、
`stateId`=目標 ID）更新狀態 → 回報使用者「已將 {票號} 設為 {狀態}」。

**例外（不自動改，保持原狀）**：票已是 `In Refinement` / `In Progress` / `Testing`，或終態 `Done` / `Canceled`（Done/Canceled 由步驟 6 徵詢是否仍分析，避免自動重開結案票）。該 team 找不到目標 state 或更新失敗 → 記錄警告、繼續後續流程，不中斷。

### 4. AI 初判（內部工作假設，**不詢問使用者**）

依票標題、描述、team、label 先形成**工作假設**（判型準則見
`${CLAUDE_PLUGIN_ROOT}/skills/linear-triage/references/triage-flow.md`）：

| 類型 | 意義 | 勘察方向 |
|------|------|---------|
| **Feature** | 全新功能 | 需求摘要 + 資訊缺口盤點（7a） |
| **CR** | 調整既有功能行為（label 常為「增強／調整」類） | 6.5 三面查證 |
| **Bug** | 既有功能跑出錯誤結果 | 6.5 三面查證 + 7b 根因分析 |

> CR 與 Bug 易混：用 Bug 格式（Steps/Expected/Actual）書寫不代表是 Bug——
> 若本質是「想要不同行為」而非「跑出錯誤結果」，屬 CR。

**此階段不用 AskUserQuestion**——光憑票面資訊判型不可靠，判型結論要等勘察與根因分析
完成後，**隨步驟 8 的報告一併給出**（附判定依據），由使用者在閘道 A（步驟 9）一次確認。
初判只決定勘察起手方向；勘察中發現證據與初判矛盾（如「Bug」實為 by-design → CR），
**隨時改判，以證據為準**。

### 5. session 標題（併入報告輸出）

session 標題建議依格式 `[類型] 票號 標題`（`[Feature]`／`[CR]`／`[Bug]`），於**步驟 8 報告末尾**一併輸出
（屆時判型已隨分析定案），供使用者複製執行，如：「建議將此 session 標題設為（請複製到輸入框執行）：
`/rename [Bug] ABC-489 訂單匯入重複寫入`」。此處不單獨執行、不等待，直接繼續下一步。

### 6. 適狀態前置檢查

讀步驟 3 的 `state` 與既有子票，決定動作（決策表見 references/triage-flow.md）：

| 情境 | 動作 |
|------|------|
| 已有完整子票樹 | 不重複開票；用 `AskUserQuestion` 徵詢（`改用 sa-flow:linear-reply 處理票上問題（推薦）` / `仍要做分析` / `結束`） |
| 狀態為 Done / Canceled | 用 `AskUserQuestion` 徵詢（`結束，不重開結案票（推薦）` / `仍要分析（僅回報、不改票）`） |
| **輸入本身是 Dev 葉票**（Dev team、無子票，非 PM/SA 根票） | 不開「子」票樹；改視需要**建 QA 父票**（Bug/CR 需測試時）或收斂範圍後回票。詳見 references/triage-flow.md §3 |
| 其餘（Backlog/Todo/In Progress…無子票） | 正常進入步驟 7 分流 |

### 6.5 勘察前置：完工度 + 規格佐證 + 資料現況（初判 CR / Bug 必做）

分析或定位**之前三面都要查**才下結論——只查 codebase 會漏掉需求依據與規格衝突：

- **A. docs 規格佐證**（必查，最易被略過）：搜既有規格（FRD/SAD/BFS/FFS/FoxPro 分析；用功能名稱／模組搜，
  檔名常不含票號），對照票要的行為與既有規格是否一致——**CR 牴觸既有規格＝改規格的 CR**（需 PM 確認＋回寫 CR 規格，
  不是默默改碼）；規格把某欄/行為設為 by-design（如 NOT NULL、必填）→ 回報務必點出，別當可隨意移除。
- **B. codebase 完工度**：`git log`（搜票號／關鍵字）+ 讀**現役最新碼**逐項確認實作狀態；**對照票述檔案/行號與
  實際 codebase**——路徑/行號常過時或指錯（例：精簡版在另一個模組，票卻指向完整版），以實際碼為準回票更正。
- **C. 資料庫現況**（資料相關時）：涉及資料值/欄位語意/分布 → 用唯讀 DB 查詢工具（若專案有提供；
  正式資料優先查測試／staging 環境）；沒有該工具則請使用者提供查詢結果或標註「資料面待查」。
  描述與實證不符 → 記入回票報告，不中斷 triage。

下結論前對齊三面：**規格說該怎樣 vs 現役碼做到哪 vs 資料實況**。部分已完工 → 步驟 8 **收斂範圍**為實際剩餘工作；
發現規格衝突 → 標為待 PM 確認，勿逕自宣告「小改」。完整步驟指令（含漏查 docs 而誤判為純前端小改的典型案例）
→ [references/triage-flow.md](references/triage-flow.md) §2.5。

### 7. 分流

#### 7a. Feature / CR（初判）→ 準備 pipeline 引導

本 skill **不自己寫文件**。以票描述為需求輸入：

1. 摘要票需求重點，標示資訊缺口（缺 FRD 要素時建議先 `sa-flow:explore`）。
2. 整理**建議起點與理由**（`requirement` / `requirement --change` / `explore`），寫進
   步驟 8 報告；**此階段不用 AskUserQuestion**——起點選擇待閘道 A 判型確認後於步驟 9
   一併詢問。pipeline 全貌見 `${CLAUDE_PLUGIN_ROOT}/references/pipeline.md`。

> Feature 走完規格（verifying-specs 通過）後才委派 `sa-flow:linear-create` 建子票樹，
> 此時機通常不在本次 triage 內；本 skill 只負責**起步引導**。

#### 7b. Bug → 根因分析（只分析、不改碼、不落檔）

> 前提：已完成步驟 6.5 的 codebase 完工度確認。

1. **AI 自動選戰場**：依票線索判斷要查 codebase / docs / DB，委派對應能力——現役系統行為釐清派
   `sa-flow:scout` 蒐集證據、需逐步除錯推理用 `superpowers:systematic-debugging`（若已安裝）、
   「欄位空了/資料少了但無錯誤」派 `sa-flow:silent-failure-hunter` agent 追被吞掉的錯誤、查實際資料/schema 用唯讀 DB 查詢工具
   （若專案有提供）、純讀碼定位用 Grep/Read/Explore agent。
   完整選擇準則 → references/triage-flow.md §2。
2. 產出根因報告：**根因 + 證據（檔案:行號 / SQL 結果 / 文件）+ 影響範圍 + 建議修法方向**。
   對齊 linear-create Bug Dev 票的三段強制欄位（根因分析 / 程式碼問題定位 / 修改細節），
   讓步驟 11 開票可直接套用。
3. **不修改任何程式碼、不另寫 docs 文件**；分析結論只回票。

### 8. 回報使用者（報告單獨收尾一個回合）

**必須**把分析結論以完整訊息輸出，且**該回合到報告為止**——報告之後不得再接任何工具呼叫
（**含 AskUserQuestion**），否則報告不會顯示（見執行通則「回合可見性」）。報告末尾依序附
session 標題建議（步驟 5 格式）與一句「請確認以上結論，回覆後續行」，然後**結束回合**等使用者回應。

**報告開頭必含「判型結論」**：`{Feature / CR / Bug}` + 一段判定依據（憑什麼判為此型；
與初判不同時說明改判原因）——這是使用者**第一次**看到判型，先前流程不曾詢問。

- **Bug**：接著輸出「根因分析報告」，必含四段（對齊 `sa-flow:linear-create` Bug Dev 票欄位）：
  1. **根因**（機制說明，非現象複述）
  2. **證據**（`檔案:行號` / SQL 結果 / 文件出處）
  3. **影響範圍**
  4. **建議修法方向**
- **Feature / CR**：接著輸出「需求摘要 + 建議起點與理由 + 後續 pipeline 路徑」。

### 9. 確認閘道 A（報告後的下一回合）

> **Guard**：報告必須已在**前一個以文字收尾的回合**完整輸出，才可進本閘道；
> 尚未輸出 → 先依步驟 8 以報告收尾結束回合。

本閘道**一次確認判型與結論**（判型不另設前置閘道）。使用者對報告的回覆若已明確表態
（「正確，回票」「判型應是 CR」「X 有誤要改」…）→ 直接依表態續行，**不再重問**。
未明確表態才用 `AskUserQuestion`：

question 固定為「上方分析報告的判型與結論是否正確？」（**不得**改寫成內含結論的長句）；header「結論確認」；
multiSelect false；options：`是，據此續行（推薦）` / `判型有誤，改為其他類型` / `結論需修正` / `到此結束`。

選「判型有誤」→ 依使用者指正改判，**補跑對應勘察**（如 Feature→Bug 需補 6.5 + 7b 根因）後
重印完整報告再重問；選「結論需修正」→ 依使用者補充修正後**重印完整報告**再重問；
選「到此結束」→ 輸出摘要並終止（不發佈、不開票）。

**Feature / CR 判型確認後**，再用 `AskUserQuestion` 詢問 pipeline 起點：

question「要從哪個起點接續？」；header「起點」；options：`從 sa-flow:requirement 開始（已有需求輪廓）` /
`從 sa-flow:requirement --change 開始（CR）` / `先 sa-flow:explore 釐清（需求尚淺）` / `只做分流，稍後自行接續`。

依選擇提示對應指令後，續步驟 10 回票。

### 10. 回票（預覽 → 閘道 B → 發佈）

沿用 `sa-flow:linear-reply` 的預覽機制：先把回票 comment **草稿全文**輸出並**以草稿收尾
結束該回合**（同步驟 8 的回合可見性規則），使用者回應後下一回合再確認（回覆已明確表態
則不重問）；未表態用 `AskUserQuestion`：

question「是否確認發佈此回覆到 Linear？」；header「發佈確認」；options：`是，發佈` / `否，取消發佈`。

選「是」→ 呼叫 `save_comment`（`issueId` = 本票）發佈；選「否」→ 跳過發佈，續步驟 11 詢問。

### 11. 適狀態開票

依步驟 6 適狀態結果決定**開票方向**，再用 `AskUserQuestion` 詢問：

| 輸入票型 | 開票方向 |
|----------|----------|
| PM/SA 根票（Feature/CR，規格已產出） | 委派 `sa-flow:linear-create` 建**子**票樹（PM→SA→QA→Dev） |
| Bug 根票（QA 級或新票） | 委派 `sa-flow:linear-create` 建 QA→Dev 修復子票（帶入根因三段） |
| **Dev 葉票**（Dev team，需測試） | 建 **QA 父票**（`save_issue` 建 QA 票 → 再 `save_issue` 設本票 `parentId` = QA 票） |

question「是否要依上述方向開票？」；header「開票」；options：`是，開票（推薦）` / `否，稍後自行處理`。

選「是」→ 子票樹走 `sa-flow:linear-create`（把本票資訊與 Bug 根因報告作描述輸入）；
建 QA 父票走 Linear MCP（QA team、QA label〔取自 `sdlc-linear-labels`，未設定則問使用者〕＋沿用本票其餘 label、Bug QA 範本、
assignee 依慣例、適當 state）。Feature/CR 規格未產出 → 提示「待 verifying-specs 通過後再開」。
選「否」→ 提示後續可執行 `sa-flow:linear-create`。

**PM 根票狀態收尾**：開票成功且票樹已含 Dev 票 → 把 PM 根票從 `In Refinement` 改為
`In Progress`（分析結束、進入開發追蹤）。規格未產出／未開票 → 維持 `In Refinement`。

> ⚠️ re-parent 副作用：設 `parentId` 後 Linear team 自動化可能改動本票 assignee/state，
> 開票後**核對並回報**，必要時更正（如前端票誤指後端負責人）。

### 12. 輸出處理摘要

固定輸出八個欄位，缺一不可：票號/標題、判型、session 標題建議、完工度、分析結論、Linear 回票狀態、
開票狀態、建議下一步。範本 → [references/triage-flow.md](references/triage-flow.md)「輸出範本」。

---

## 錯誤處理

| 錯誤情境 | 處理方式 |
|---------|---------|
| 票 ID 不存在 | 顯示 Linear 錯誤訊息，終止 |
| Linear MCP 未設定 | 提示設定 `.mcp.json`，終止 |
| 判型無法確定 | 於步驟 8 報告中如實列出兩種可能與各自依據，請使用者於閘道 A 裁決 |
| Bug 根因無法定位 | 回報已排查範圍與最可能方向，不杜撰；步驟 11 開票時填「最可能位置 + 排查方向」 |
| 使用者反映「沒看到結論／報告」 | 立即依步驟 8 格式**完整輸出報告全文並以報告收尾結束回合**；不得在同回合接 AskUserQuestion、不得只重發問題 |
| save_comment 失敗 | 顯示錯誤，保留分析結論供使用者手動貼上 |

---

## 使用範例

```bash
linear-triage ABC-489
linear-triage ABC-564
```

## 細節參考

- 判型準則 / Bug 戰場選擇準則 / 適狀態決策表：`references/triage-flow.md`
- 完整 SDLC pipeline 與銜接點：`${CLAUDE_PLUGIN_ROOT}/references/pipeline.md`
- 開票票樹與描述範本：`sa-flow:linear-create`
