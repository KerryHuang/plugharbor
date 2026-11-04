# 現有實作掃描指引（後端）

> 此步驟對應 specify-backend SKILL Step 4.1.5。產出必須整合進 BFS 的 **§A 既有實作快照（Codebase Snapshot）** 章節，作為規格內容的客觀基準。

## 目的

在撰寫規格書前，**以實際 codebase 為基準**確認：
1. 既有路由與命名慣例（避免規格寫出不存在的路由）
2. 既有 Handler mapping 完整邏輯（給 PG 對照修改點）
3. 同類 Handler / 同模式檔名（避免漏掉相關修改範圍）

避免「規格憑想像寫，RD 看不懂 / 開發到一半才發現規格錯」。

---

## Step 4.1.5a：路由清單（強制必做）

### 觸發條件
所有 BFS 撰寫一律執行。

### 搜尋指令

對每個 BFS 將涉及的 Controller，逐一執行 Grep 取得既有路由：

```bash
# 依專案語言／框架，對涉及的 Controller／路由檔抓路由宣告（以下為示意）
Grep "{路由宣告關鍵字，如 Route|Get|Post|Put|Delete}" path=.../{Controller 檔}
```

### 必產出內容

落 `analysis/reuse-scan.yml` 的 `routes:`（含 Controller 路徑、行號、Action、完整路由、`scanned_at`）。
**BFS §A.1 只寫結論**（每個 §6 端點是「已存在不變動／需擴充／需新增」），不複製明細表：

| 行號 | Action | 完整路由（含 Area / Controller prefix） |
|---|---|---|
| 27 | `{Controller 層級路由宣告}` | （Controller 層級 prefix） |
| 145 | `{POST 宣告}` | `POST /api/{version}/{module}/SalesOrder` |
| 296 | `{POST 宣告，子路由 {id}/BatchItems}` | `POST /api/{version}/{module}/SalesOrder/{id}/BatchItems` |
| 597 | `{POST 宣告，子路由 items/copy-from-template}` | `POST /api/{version}/{module}/SalesOrder/{salesOrderId}/items/copy-from-template` |

### Lint 規則

1. BFS §6.1 端點總覽中**任何「既有不變動」路由必須在路由清單中找到匹配**；若找不到，視為 CRITICAL，停止撰寫並重新搜尋
2. 從路由清單**歸納 Controller 命名風格**（PascalCase Action `Light` `Paged` vs kebab-case sub-resource `items/copy-from-template`），新增 Action 必須沿用同 Controller 既有風格

---

## Step 4.1.5b：既有 Handler mapping 完整對照（條件式）

### 觸發條件
本次 ticket 涉及「修改既有 Handler 的欄位 mapping / Bug Fix」時**強制必做**。

判別關鍵字：
- 規格描述含「修正 / Bug / 對齊 / 一致 / fix」+「mapping / 欄位 / 對應」
- 涉及 Copy／Sync／Create-From-X 類 Handler

### 搜尋指令

```bash
# 1. 定位 Handler 完整檔案
Read path=.../Handler/{HandlerName}

# 2. 找出實際 mapping 方法（通常名為 Create{Entity}FromXxx 或 MapToXxx）
Grep "{建構 DTO 的語法關鍵字}" path=.../{HandlerName}
```

### 必產出內容

落 `analysis/reuse-scan.yml` 的 `handler_mappings:`，列每個既有 mapping **完整 N 欄位**（不可省略）並標示本次修改點。
**BFS 不再設附錄 D**——逐欄 mapping 是勘察證據不是規格；BFS §6 只寫「這個端點的 Response 要有哪些欄位」：

| # | DTO 屬性 | 既有來源 | 本次處理 |
|---|---|---|---|
| 1 | `Id` | 新生成 | 不動 |
| 8 | `Spec` | `source.Spec ?? ""` | 🔴 修改：... |
| 10 | `CategoryId` | `source.CategoryId` | 🔴 移除 |
| 15 | `IsActive` | `true`（硬編） | 🔴 改為依 `source.Status` 轉換 |
| ... | ... | ... | 不動 |

### Lint 規則

1. BFS §6.X 提到「修正既有寫入邏輯」但 `reuse-scan.yml` **未列既有 mapping 完整對照**，視為 CRITICAL
2. 「不動」的欄位必須**全數列出**（不可寫「其餘沿用」省略），讓 PG 對照修改範圍時 100% 明確

---

## Step 4.1.5c：跨 Handler 一致性掃描（條件式）

### 觸發條件
本次 ticket 涉及「兩入口」「多入口」「一致性」「Bug Fix」時**強制必做**。

判別關鍵字：
- 規格描述含「訂單端 / 庫存端」「兩個入口」「三入口」「Excel + Copy」
- 涉及 master 資料的複製 / 同步邏輯
- 涉及「一致性」「對齊」「behaviors match」

### 搜尋指令

```bash
# 同名 / 同模式 Handler 掃描（檔名樣式依專案慣例）
Glob "**/Copy*Handler*"
Glob "**/Sync*Handler*"

# 同 master 來源的相關 Handler
Grep "{MasterEntity}Repository|{MasterEntity}View" -l

# 同 Action 名稱的所有 Controller（如 copy-from-template 可能存在於多個 Controller）
Grep "{action-name}" path=.../Controllers/ -l
```

### 必產出內容

落 `analysis/reuse-scan.yml` 的 `write_paths:`。**BFS §A.2 只寫結論**（同類寫入路徑幾條、本次修哪幾條、排除項與原因——那是業務範圍決策，留在規格書）：

| Handler 路徑 | 寫入目標表 / DTO | 與本 ticket 的關係 |
|---|---|---|
| `CopyTemplateItemsToOrderHandler` | OrderItem / `CreateOrderItemDto` | ✅ 本 ticket 修正範圍 |
| `CopyTemplateItemsToQuoteHandler` | QuoteItem / `CreateQuoteItemDto` | ✅ 本 ticket 修正範圍 |
| `CopyQuoteItemsToOrderHandler` | OrderItem | ❌ 不同邏輯（報價→訂單），不在範圍 |

### Lint 規則

1. 若掃描出**多條同類寫入路徑**但 BFS 只列其中一條為修正範圍，**必須**以 `AskUserQuestion` 跟 PM 確認其他是否在範圍內，結論記於 BFS §A.2「排除項與原因」
2. 不可預設「PM 沒提就不在範圍」— 因為 PM 通常不了解 codebase 有幾支 Handler

---

## 整體產出規則

`reuse-scan` 產出 = BFS **§A 既有實作快照** 章節內容：

```markdown
## §A 既有實作快照（Codebase Snapshot）

> 本章節由 specify-backend Step 4.1.5 產出，作為規格客觀基準。

### A.1 既有路由清單
（Step 4.1.5a 產出）

### A.2 影響範圍結論（若觸發）
（Step 4.1.5c 的結論：同類寫入路徑幾條、本次修哪幾條、排除項與原因）

### A.3 重用結論
| 能力 | 結論 |
|------|------|
| {查詢／寫入／計算等能力描述} | 既有可用 / 需擴充 / 需新建 |
```

**規則**：規格書中每項**能力**必須明確標注「既有可用 / 需擴充 / 需新建」，不可留空。

> ⚠️ **標的是「能力」不是「類別」**：寫「品項查詢能力：既有可用」，
> 不寫「ItemQueryHandler：延用」。類別名與路徑留在 `reuse-scan.yml`——
> 用哪個類別、怎麼擴充是 RD 的決定，且類別名變動快於規格生命週期。
