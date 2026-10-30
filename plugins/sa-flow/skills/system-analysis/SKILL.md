---
name: system-analysis
description: "把 FRD 轉成系統分析文件（SAD）：工作流、資訊流、資料流三流分析、重用盤點與邊界清單。觸發：「系統分析」「寫 SAD」。"
argument-hint: "[功能名稱或 FRD 路徑]"
---

# 系統分析

> 非 Claude Code（如 Pi）執行時，先讀 `../../references/harness-terms.md`（相對本檔；Claude Code 為 `${CLAUDE_PLUGIN_ROOT}/references/harness-terms.md`，照字面執行可略過），把 Claude 專屬工具與路徑換成對應項。

以**資深系統分析師（SA，10 年以上企業系統經驗）**角色，從需求文件 (FRD) 出發深入分析現有系統，抽取工作流／資訊流／資料流並規劃實現策略，產出「橋接需求與技術實作」的系統分析文件 (SAD)。

## 輸入參數

```
$ARGUMENTS → [功能名稱或 FRD 路徑]
```

| 參數 | 必填 | 說明 |
|------|------|------|
| `功能名稱或 FRD 路徑` | 否 | 省略時自動偵測當前工作目錄對應的 FRD；找不到則詢問使用者 |

## 前置規範

依 `${CLAUDE_PLUGIN_ROOT}/references/shared-preludes.md`（核心原則：不猜測、Docs 同步、Graphify 查詢〔選配〕）。

## 執行流程

### 1. 定位需求文件

**先讀 `analysis/_context.yml`**（依 `${CLAUDE_PLUGIN_ROOT}/references/shared-preludes.md` Step 0.8）——
功能目錄與 FRD 路徑若已登記，直接使用，不重新搜尋。未登記時才 `find {docs-root} -name "*需求文件*.md" -type f`，並把結果寫入 `_context.yml` 供下游沿用。

**若找不到 FRD**：用 `AskUserQuestion` 詢問（選項同錯誤處理表：`先執行 sa-flow:requirement 寫 FRD（推薦）` / `改用 sa-flow:explore 或 domain-advisor 顧問探索` / `提供 FRD 路徑`）。

### 2. 理解需求意圖

> 讀取既有規格文件一律定向讀取所需章節，不整檔載入。

通讀 FRD，依 `references/frd-extraction-guide.md`（總覽表）
提取功能目標、業務流程、欄位規格、業務規則。**§2.1 使用者故事**的 US-XX、角色欄與操作是全鏈追溯鍵，
作為工作流步驟對應與 API 設計基礎。**§4 畫面設計**提取操作表→API、業務層欄位語意→資訊流、
選項來源→Light API（完整欄位集合另取自 `analysis/db-analysis.yml` 與 `ui-survey.md`）；轉譯方法見該指南。

### 2.5 Graphify 查詢（選配、條件式）
> 參考 `${CLAUDE_PLUGIN_ROOT}/references/graphify-integration.md` — **Query 區塊**（graphify 未安裝時靜默跳過）
### 3. 深入探索現有系統（**三路平行派工**）

> 本步驟是全鏈的勘察主場，三路用**不同工具、寫不同檔**，彼此無共用狀態 →
> **同一批次一次送出三個 tool call**，不要序列跑。**主 session 不自己查 DB、不自己開瀏覽器、不自己掃 codebase。**

| 路 | agent | 蒐什麼 | 寫哪個檔 |
|---|---|---|---|
| **A** | `sa-flow:scout` | 既有程式碼（3.1）＋ 跨模組影響（3.3） | `analysis/reuse-scan.yml` |
| **B** | `sa-flow:scout`（DB 結構模式，需有唯讀 DB 查詢工具） | DB 結構與 FK（3.2） | `analysis/db-analysis.yml` |
| **C** | `sa-flow:browser-surveyor` | 現有畫面與 API（3.4，條件觸發） | `analysis/ui-survey.md` |

> ⚠ **A 路的 3.1 與 3.3 必須同一次派工**（都寫 `reuse-scan.yml`，拆兩個 agent 會互相覆蓋，
> 是本步驟唯一的串接理由）；同 session 可平行派多個瀏覽器 agent，各給不同 `isolated_context`。

**沒落檔 = 下游會再查一遍**——`specify-backend`／`dev-readiness`／`verifying-specs` 都直接取用這三份檔。

**三路的完整派工 prompt、抽樣界線、失敗處置** → `references/dispatch-templates.md`
（派工前讀該檔，`{功能目錄}` 一律展開成絕對路徑）。

回報後：**A 路**讀 `reuse-scan.yml` 填 §5 能力結論表與 §7 重用分析（類別名／檔案路徑／行號留
yml 不進正文，變動快於規格生命週期）；**B 路**讀 `db-analysis.yml` 整合 `status_columns`／
`columns[*].semantic` 至 Step 6，欄位描述與證據不符 → 不中斷，SAD 以證據語意為準並標注；**C 路**補充
§4/§5/§6/§7，**寫入前須依 `${CLAUDE_PLUGIN_ROOT}/references/ui-analysis-guide.md` 檔頭對照表轉譯，
不得整段複製**（現況擷取不是分析結論），**不要 Read 截圖進 context**。

三路全齊才進 Step 4；失敗處置見 dispatch-templates.md「匯流與失敗處置」，都不阻斷本 skill（B 路失敗時結論降級並註明）。

> **Step 4~6 觸發式單點諮詢**：一旦命中 domain 訊號（狀態流轉／聚合根歸屬／客戶變體／
> 產品邊界），當場依 `${CLAUDE_PLUGIN_ROOT}/references/consultant-desk.md`
> 派一次單點問，不累積到 Step 8.3；結論記入 `analysis/consultant-notes.md`，Step 8.3 不重問。

### 4. 工作流分析

分析「誰在什麼時候做什麼」與「系統如何支撐」：從 FRD 使用者故事提取所有角色、各角色操作步驟與順序、
每步驟的系統支撐（API／驗證／計算）、人工與系統自動化邊界；每個 US-XX 對應到工作流步驟，確保系統
支撐無遺漏。

涉及狀態（訂單／單據／申請的生命週期）時，**狀態機完整性是 CRITICAL 項**（依
`${CLAUDE_PLUGIN_ROOT}/references/analysis-standards.md`）：狀態圖必須列出所有狀態、合法轉換、
**非法轉換**（含系統回應）、終態後可否操作、**並發狀態衝突**——非僅畫正常路徑，是 §6.6 邊界分析與
BFS §8.4 並發處理的依據。

**產出**：泳道工作流程圖（必畫）+ 角色互動表 + 完整狀態機圖（含非法轉換，若適用）

### 5. 資訊流分析

分析「資料從哪來、經過什麼處理、到哪去」：資料來源（使用者輸入／現有資料表／外部系統／計算產生）、
處理邏輯（驗證→轉換→業務規則→儲存）、資料目標（寫入 DB／回傳前端／觸發通知／傳送外部）、系統整合介面。

**§4 欄位對應**：依 `references/frd-extraction-guide.md`（§B 欄位清單）將 FRD §4 畫面欄位系統性對應至
IF-XX 資訊處理明細，確保沒有畫面欄位遺漏。

**產出**：資訊流向圖（必畫；每個處理節點掛 BR 編號）+ 處理明細表 + 系統整合介面表（若適用）

### 6. 資料流分析

分析「涉及哪些 DB 表、讀寫關係、表間關聯」：列出所有涉及的表並標示讀/寫、ER 圖呈現 FK 關係、
每個操作對應的資料表 CRUD、新增/修改對現有資料的影響評估並標注需新增的 Table/Column（**Migration
預判**）。⚠ 對既有表加欄位前，先確認其他讀寫方（舊系統、報表、外部整合）不會因欄位集合變動而出錯；
有疑慮時預判為新建關聯表，並在 Migration 預判清單寫明理由。

**產出**：資料表清單 + ER 圖（必畫）+ CRUD 對應表 + 影響評估表 + Migration 預判清單

> **注意**：ER 圖使用 Mermaid `erDiagram` 語法，**禁止**使用 `PK_FK` 複合角色（Mermaid 不支援），
> 正確寫法：`uniqueidentifier EntityId PK "FK to OtherTable"`

### 6.5 邊界與例外路徑分析

完成三流分析後，**系統性盤點 FRD 業務層未涵蓋的系統層邊界**——SA 橋接需求與實作最易遺漏的責任。逐一
檢視 `${CLAUDE_PLUGIN_ROOT}/references/boundary-dimensions.md` 的 **B1–B10／B13／M1–M4**（B11/B12 待
FFS 存在才驗；`dev-readiness` 用同一份編號覆核，這裡漏的就是那裡退回的缺口），每維度都要有結論，
「不適用」也算。涉及新舊系統共用表時，另查共存期的語意分裂，偏離共用口徑者寫入風險表。
`_context.yml` 的 `chain_origin: foxpro`（舊系統移植鏈）時，（四類偏離與三要件定義見 `${CLAUDE_PLUGIN_ROOT}/references/legacy-parity.md`）
邊界盤點的結論優先取舊系統現行行為；舊系統沒有、也非平台必要的邊界寫「不處理（parity）」，不新增規則。功能含多筆查詢時要拍板**排序策略**（後端或
前端排序、可否切換、白名單欄位；有分頁一律後端排序為預設）——契約層問題，SA 不定 BFS／FFS 就各自
臆測，判準見 `${CLAUDE_PLUGIN_ROOT}/references/sort-order-standards.md`。逐類盤點方法與輸出格式 →
`references/boundary-analysis-guide.md`。

**產出**：邊界與例外清單（寫入 SAD §6.6；**規則超過 8 條時必附決策樹圖**）+ 回補 §2.3 狀態機的非法轉換與並發衝突。下游 BFS §7（驗證）/ §8（例外）/ §8.4（並發）依此承接，避免 RD 臆測。

### 7. 現有系統重用分析

整理步驟 3 探索的結果，評估可重用性（現有 API／資料模型／資料存取元件／Light API 各標「直接使用 / 需擴充 / 需新建」）。

**§4 選項來源推導**：依 `references/frd-extraction-guide.md`（§C 需選項清單的欄位）逐一識別 Light API 需求；判準是**來源欄**（參照主檔 → 需 Light API；固定清單 → 不需），避免遺漏選單來源。

**產出**：SAD §5 **一張能力結論表**（能力｜既有可用／需擴充／需新建｜備註；明細 ref `analysis/reuse-scan.yml`）+ **Light API 需求清單**（參照實體 / 已存在 / 需新建）

### 7.5 功能代碼盤點查核（條件式）

需求涉及**新頁面**或**既有頁面的權限行為**時執行，依 `${CLAUDE_PLUGIN_ROOT}/references/program-code-inventory.md`
（Step A 查代碼、無碼則 Step B 暫編＋撞碼驗證）；未設定盤點路徑且搜尋不到 → 靜默跳過。產出：每個頁面
的判定（已有代碼→沿用並記代碼／無碼→暫編碼＋撞碼驗證結果／不需代碼→理由），填入 SAD。

> ⚠️ 既有代碼優先於新編——重複編碼會造成權限分裂。**不得**憑印象斷定「沒有代碼」，必須實查盤點文件。

### 8. 提出技術方案

基於以上分析，**提出 2-3 個技術方案**（方案描述：資料表策略、API 粒度、重用 vs 新建；各附優點／缺點／
適用條件），給出**明確推薦**與理由，附**初步 API 端點建議表**（HTTP 方法｜路由｜對應 US｜說明）。
**SAD §6.1 只列有分歧的方案取捨**，實作優先順序由 RD 決定，不寫。

**NFR → 約束與風險（必填）**：FRD §6 每項非功能性需求（效能／並發／資料量／權限／稽核）逐項寫成**約束
（目標值）＋已知現況＋陷阱**，填入 **SAD §6.5**；並發／權限的行為約束與 §6.6 邊界分析相互呼應。
**不寫手段**（索引、鎖、連線池、快取、查詢寫法）——那是 Dev 定，需留痕時寫 `decisions.md` TD。

### 8.3. 顧問桌審查（鏈上主場）

SAD 是**整條規格鏈的顧問桌主場**（依 `${CLAUDE_PLUGIN_ROOT}/references/consultant-desk.md` 執行，
唯一定義處，不重列編制與流程）——此時證據最足（Step 3 勘察 + Step 4-8 三流與方案），問題最具體。
**Step 4~6 已單點問過的點不重問**，全問過則降為快速複核；仍需釐清或無法裁決 → 併入 8.5 確認門一次
問完；結論留痕 `analysis/consultant-notes.md` + SAD 記一行，下游據此判定不重開桌。

### 8.5. 確認門

**確認前**，將步驟 4-8 結果寫入 `{功能目錄}/analysis/_sad-draft.md`（暫存），供修正時 selective reload
而不重跑平行 Agent。確認**必分兩回合**（**回合可見性**——長摘要塞進 `AskUserQuestion` 或同回合先印
再問，使用者都看不到）：先以文字完整輸出分析摘要（工作流重點、方案比較、推薦方案與理由）並以此收尾、
不接工具呼叫；下一回合才視使用者是否已表態決定續行或改用 `AskUserQuestion`（依前置規範互動詢問規範，
附 `方向需修正` 選項）。確認方向正確後才繼續 Step 9；有修正時只更新 `_sad-draft.md` 受影響段落後重新確認。

### 8.6 決策紀錄落檔（寫檔前必做）

把 Step 8.5 確認門**已呈現、使用者已表態**的方案比較，依 `${CLAUDE_PLUGIN_ROOT}/references/decision-record.md`
（append 協定與欄位規則的唯一定義處）append 到 `{功能目錄}/decisions.md`（全鏈唯一決策落點，`階段` 填
`SAD`）。**不新增分析步驟、不多問任何問題**——只把已算出的東西落檔。Step 8.3 顧問桌對 domain 邊界／
狀態機歸屬的裁示也要記（`拍板` 填 `顧問`、`依據` 指向 `analysis/consultant-notes.md`）；SAD `§D` 只列
編號與一句結論。⚠️ 8.5 的內容寫在暫存的 `_sad-draft.md`——**本步驟是唯一讓決策存活到 BFS／FFS 的機制**。

### 8.7 去重與體積（**交給 agent，此處只備輸入**）

去重閘、SPEC-INDEX、必畫圖檢查、正文預算（30KB）與超標拆附錄，全部由 `spec-writer` 在 Step 10 自檢
（其 L2~L4 ＋ 正文預算 `<law>`）。主 session 只做一件事：把 `spec-dedup-and-budget.md`「各文件套用值」的
SAD 列整列取出，Step 10 派工時當 `boundary_row` 傳給 agent。**SAD 特有去重判準寫進 brief：不同視角的
圖不算重複**——泳道與資訊流圖 ≠ FRD 業務流程圖，不要為了去重刪掉。

### 9. 疑問點總清查（寫文件前必做）

在開始撰寫文件前，依 `references/pre-write-checklist.md` 逐一檢查各面向是否仍有未解決的疑問；全部解決後才進入步驟 10 撰寫文件。

### 10. 撰寫系統分析文件（**派 `spec-writer`，主 session 不寫正文**）

完整派工 prompt → [sad-dispatch.md](references/sad-dispatch.md)。

<law>
**`analysis/_sad-draft.md` 就是 brief 的載體。** 8.5 確認門已經把步驟 4-8 的分析結果
寫進去了，**不要再重打一份綱要**——主 session 寫的是分析摘要（短，是思考的產物），
agent 依它生成正文（長）。這個分工是本 skill context 隔離的核心。
</law>

`extra_checks` 帶兩條 SAD 專屬硬閘（理由見 sad-dispatch.md）：

| # | 檢查 | 寫錯的後果 |
|---|------|---|
| **ER** | ER 圖禁用 `PK_FK` 複合角色 | Mermaid 不支援，圖直接渲染失敗 |
| **SM** | 有狀態機時，§2.3 必須標**非法轉換與並發衝突** | 只畫正常路徑，`dev-readiness` 的 B4 會整批退回，這一棒白做 |

Step 7.5 有產出時，brief 須載明每個頁面的代碼判定（沿用／新編＋撞碼驗證結果／不需代碼＋理由），
作為 BFS／FFS 的依據。**儲存位置**：專案既有文件目錄慣例；無慣例則預設
`{docs-root}/{模組名稱}/{功能名稱}/{功能名稱}_系統分析文件.md`。

### 11. 判讀複核（**只做 agent 做不到的**）

L9/L10/L14/L15/L16 已由 agent 的 L1~L5 自檢涵蓋，**不要重跑**。本步驟只做三件 agent 做不到的事：
**A** 與 FRD 的追溯完整性（§2.1 每個 US-XX 都對應到工作流步驟、§4 畫面欄位都對應到 IF-XX、§4 每個按鈕都對應到 API 端點建議表——agent 只
定向讀了 FRD 部分章節）；**B** 三份勘察 yml 的新鮮度（`scanned_at` 是否早於本次分析依據的現況——agent
讀 yml 無法察覺其本身已過期）；**C** 抽驗 agent 的自檢結論，尤其 SM 狀態機完整性。

<law>
**不要照單全收 agent 的「自檢全過」**（理由與通用盲區見 `${CLAUDE_PLUGIN_ROOT}/references/dispatch-conventions.md` §四）。
抽驗重點：SM 自己看一次狀態圖——「非法轉換」很容易被寫成一句話帶過，而不是實際畫進圖裡。
</law>

未定案的點自己裁決或問使用者（補完回派 `mode: change`）；需要補勘察的**回頭派 Step 3 對應的那一路 agent**，不要自己去查。

### 12. 報告完成

輸出完成摘要：文件路徑、功能名稱、技術可行性、實現複雜度、可重用/需新建資源數量、風險項目數。

**下一步**：SAD → BFS 是 `${CLAUDE_PLUGIN_ROOT}/references/handoff-protocol.md` 定義的**硬性停點**
（技術方案要人拍板，選錯後面全白做）——**不自動接棒**，以 Step 8.5 確認過的方案為前提，等使用者指示後才續行：

1. `sa-flow:specify-backend {功能描述}` 建立 BFS → 之後可一路自動接棒到 `verifying-specs`
2. 單獨驗 SAD（可選）：`sa-flow:verifying-specs {SAD 路徑}`

## 錯誤處理

| 錯誤情境 | 處理方式 |
|---------|---------|
| FRD 找不到（無參數也找不到） | `AskUserQuestion`：(1) 先執行 `sa-flow:requirement`（推薦）(2) 改用 `sa-flow:explore` 或直接派 `domain-advisor`（consult 模式）(3) 提供 FRD 路徑。無 FRD 不續寫 SAD |
| 唯讀 DB 查詢工具不可用 | 記錄警告，跳過 §3.2，以程式碼分析為主 |
| `scout` 回傳空結果 | 標記「未找到相關元件」，續行，SAD 中標注需新建 |
| 使用者在確認門（8.5）要求修正 | 更新對應分析步驟後重新呈現摘要，再次確認 |

完整開發流程詳見 `${CLAUDE_PLUGIN_ROOT}/references/upstream-workflow.md`。
