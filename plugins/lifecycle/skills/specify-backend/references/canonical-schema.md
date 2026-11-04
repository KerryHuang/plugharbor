# Canonical DB Schema 來源（強制指定）

> 此步驟對應 specify-backend SKILL Step 4。所有 DB 欄位定義（型別 / 長度 / nullable）**必須**以 canonical schema 連線實查為準，禁止從特定環境（客戶／正式環境）連線推斷。

## 為什麼需要

不同環境的 DB 可能有少量欄位差異（現場自行擴充過）；schema 規範以**開發團隊維護的 canonical schema**為準。

實例：某份 BFS v1.0 從錯誤連線推斷出 `QTY decimal(8,0)`，實際 canonical schema 為 `decimal(6,0)`，導致規格計算上限錯誤。

---

## Canonical Connection 識別

各專案 canonical schema 連線名稱由**專案層 CLAUDE.md 指定**。若未指定，由 SKILL 用 `AskUserQuestion` 詢問。

建議在專案 CLAUDE.md 以如下形式記錄：

| 連線名稱 | 用途 |
|---|---|
| `{canonical 連線名}` | **canonical schema**（資料結構與欄位描述） |
| `{環境／客戶} Staging` | 實際資料（查樣本資料用，不查 schema） |

> 切連線前先列出可用連線（`list_connections` 或同等功能）對名，連線改名後舊名稱會失效。

---

## SKILL Step 4 強制流程

以下以「唯讀 DB 查詢工具」泛稱專案提供的 DB 查詢能力（不可用則請使用者提供 schema，並在 BFS 標注「欄位定義待實查」）。

### Step 4.0：切換到 canonical connection（前置必做）

切換到 `{canonical 連線名}`。此動作**必須**先於任何查 schema 的呼叫。

### Step 4.1：查詢欄位結構

用唯讀 DB 查詢工具查 `{Table}` 的欄位（型別 / 長度 / nullable / 索引）。

### Step 4.2：在 BFS §5 欄位表加註來源

每個欄位定義表的標題或開頭**必須**加註：

```markdown
> 欄位定義以 **{canonical 連線名}** 連線實查為準（{YYYY-MM-DD}）。
```

---

## 與「查樣本資料」的區別

| 動作 | 用哪個連線 |
|---|---|
| 查 schema（欄位型別 / 長度 / nullable / 索引） | **canonical 連線** |
| 查樣本資料（值的範例、髒值統計、實際內容） | 實際資料連線（如 `{環境} Staging`） |

切換時機：當前已在 canonical → 查樣本資料前切到實際資料連線 → 查完後再切回 canonical 繼續 schema 查詢。

---

## Lint 規則

1. BFS §5 欄位定義表若**未加註來源連線**，視為 WARNING
2. BFS 中欄位型別 / 長度與 canonical schema 實查不符，視為 CRITICAL
3. 多環境差異性欄位（少數情境），需明確標註「依環境而異」並列出已知差異
