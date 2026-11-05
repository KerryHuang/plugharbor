---
name: schema-docs
description: 由 SQL view 檔解析欄位映射、關聯與計算邏輯，產生資料表結構說明文件（Markdown）；方言關鍵字走附錄。Use when 產生資料表描述, 文件化檢視表, 更新 TableDescription, 由 view 產欄位對照.
---

# 產生資料表結構說明文件

從 SQL 檢視表（View）檔案解析欄位映射、關聯關係及計算邏輯，產生標準化的 Markdown 資料表結構說明文件。

**核心原則**：嚴格按主表、關聯表、計算欄位分組，每個欄位都必須正確歸類。

## 0. 偵測技術棧與附錄

先看 view 檔的語法與專案的 DB 線索（`CREATE OR ALTER VIEW`、`WITH(NOLOCK)` → SQL Server；`CREATE OR REPLACE VIEW`、`::` 型別轉換 → PostgreSQL；反引號、`IF(`、`IFNULL(` → MySQL；`strftime(`、`julianday(` → SQLite；連線字串、provider 套件亦同），對照下表載入附錄（讀其「View 計算欄位關鍵字」節），並在回報第一行寫「附錄：<檔名>」。

| 偵測到 | 附錄 |
|---|---|
| SQL Server 語法／連線 | `${CLAUDE_PLUGIN_ROOT}/references/dialects/sqlserver.md` |
| PostgreSQL 語法／連線 | `${CLAUDE_PLUGIN_ROOT}/references/dialects/postgresql.md` |
| MySQL 語法／連線 | `${CLAUDE_PLUGIN_ROOT}/references/dialects/mysql.md` |
| SQLite 語法／連線 | `${CLAUDE_PLUGIN_ROOT}/references/dialects/sqlite.md` |

沒有對應附錄：照本 skill 的通用方法，加上專案既有程式的寫法（先找 2–3 份既有說明文件當樣板；有裝 workspace 就照 `workspace:convention-first`（可選））。做完問使用者要不要把這次的寫法整理成新附錄 `references/dialects/<方言>.md`，回報寫「附錄：無（照既有程式）」。

view 的欄位註解格式（`-- 中文說明 (原始欄位) [關聯表] {選項值}`）由 `schema-conventions` 規範；註解缺漏時，說明欄留白並在回報列出。

## 1. 步驟

### 步驟 1：解析檔案

1. 讀取指定的 view SQL 檔。
2. 從 `FROM` 提取主表名稱（忽略 table hint，如 `WITH(NOLOCK)`）。
3. 從 `JOIN`（多為 `LEFT JOIN`）提取所有關聯表與關聯條件。
4. 從檔案名稱提取功能分類與中文名稱。

### 步驟 2：解析 SELECT 欄位

逐行提取：

- `原始欄位 AS 新欄位名稱` 映射
- 行末註解：`-- 中文說明 (原始欄位) [關聯表] {選項值}`
- 分類註解（如 `-- 訂單`、`-- 時間`）

### 步驟 3：分類欄位

**必須依序分為三類**：

| 類別 | 判斷依據 | 表格欄位 |
|---|---|---|
| 主表欄位 | 來自 FROM 主表 | 原始欄位名稱／新欄位名稱／說明／關聯／範例 |
| 關聯表欄位 | 來自 JOIN 表，按字母排序 | 同上 |
| 計算欄位 | 含附錄列出的計算關鍵字（CASE WHEN、空值處理、日期差等） | 欄位名稱／說明／計算邏輯／範例 |

### 步驟 4：產生 Markdown

```markdown
# 資料表結構說明

## 資料表：{主表名} ({中文說明})

| 原始欄位名稱 | 新欄位名稱 | 說明 | 關聯 | 範例 |
| ------------ | ---------- | ---- | ---- | ---- |

## 資料表：{關聯表名} ({說明})

| 原始欄位名稱 | 新欄位名稱 | 說明 | 關聯 | 範例 |
| ------------ | ---------- | ---- | ---- | ---- |

## 計算欄位

| 欄位名稱 | 說明 | 計算邏輯 | 範例 |
| -------- | ---- | -------- | ---- |
```

### 步驟 5：品質檢查

- [ ] 所有 SELECT 欄位都已轉換
- [ ] 欄位正確分組（主表／關聯表／計算欄位）
- [ ] 關聯關係準確（格式：`表名.欄位`）
- [ ] 計算欄位提取核心邏輯（忽略外層的空值處理與型別轉換包裝）
- [ ] 選項值 `{...}` 包含在說明中

## 2. 注意事項

- 忽略被註解掉的欄位（`-- ,欄位名稱`）。
- 布林型計算欄位（型別轉換包 `CASE WHEN`）：提取 `CASE WHEN` 條件作為計算邏輯。
- 同一表格的多個別名（如 `SEMP`、`PEMP`）統一處理。
- 範例欄位保持空白。
- 沒有原始欄位（直接來自關聯表的欄位）：原始欄位名稱使用關聯表的欄位名稱。
- 多表同名欄位：優先主表；來自關聯表則在說明標註來源表。
- 複雜計算：提取核心條件作為計算邏輯，忽略外層包裝函式。

## 3. 轉換規則

### 規則 1：欄位映射

`ORD_MST.ORD_NO AS OrderId` → 原始欄位名稱 `ORD_NO`，新欄位名稱 `OrderId`。

### 規則 2：說明文字

`-- 訂單編號 (ORD_NO)` → 說明 `訂單編號`，並確認原始欄位 `ORD_NO`。

### 規則 3：關聯關係

A. JOIN 語句：

```sql
LEFT JOIN CUST -- 客戶
    ON ORD_MST.CUST_NO = CUST.CUST_NO
```

提取：關聯表 `CUST`，關聯欄位 `CUST_NO`。

B. 註解中的關聯標記：`-- 客戶編號 (CUST_NO) [CUST]` → 關聯 `CUST.CUST_NO`。

C. 外鍵關聯格式：`-- 業務人員編號 [EMP].[EMP_NO]` → 關聯 `EMP.EMP_NO`。

### 規則 4：分組

1. 主表：FROM 的主要表格。
2. 關聯表：JOIN 出現的表格，按字母順序。
3. 計算欄位：含計算邏輯的欄位（關鍵字見方言附錄）。

### 規則 5：布林型計算欄位

```sql
,ISNULL(CONVERT(BIT, CASE WHEN ORD_MST.STATUS_FLG = 'C' THEN 1 ELSE 0 END), 0) AS IsCanceled
```

說明 `已取消`；計算邏輯 `ORD_MST.STATUS_FLG = 'C'`。（此例為 SQL Server 寫法，其他方言見附錄。）

### 規則 6：額外資訊

- 大括號內的選項值：`-- 訂單狀態代碼 (STATUS_FLG) {未結=O,結案=Y,暫停=P,作廢=C}`，說明須包含完整選項內容。
- 方括號內的業務描述：`-- 文件編號 [外部系統訂單編號]`，說明須包含完整描述。

## 4. 轉換範例

**基本欄位**：`ORD_MST.ORD_NO AS OrderId -- 訂單編號 (ORD_NO)`

| 原始欄位名稱 | 新欄位名稱 | 說明 | 關聯 | 範例 |
| ------------ | ---------- | ---- | ---- | ---- |
| ORD_NO | OrderId | 訂單編號 | | |

**含關聯**：`ORD_MST.CUST_NO AS CustomerId -- 客戶編號 (CUST_NO) [CUST]`

| 原始欄位名稱 | 新欄位名稱 | 說明 | 關聯 | 範例 |
| ------------ | ---------- | ---- | ---- | ---- |
| CUST_NO | CustomerId | 客戶編號 | CUST.CUST_NO | |

**含選項值**：`ORD_MST.TYPE1 AS OrderTypeName -- 訂單類型名稱 (TYPE1) {標準/急件}`

| 原始欄位名稱 | 新欄位名稱 | 說明 | 關聯 | 範例 |
| ------------ | ---------- | ---- | ---- | ---- |
| TYPE1 | OrderTypeName | 訂單類型名稱 {標準/急件} | | |

**計算欄位**：`,ISNULL(CONVERT(BIT, CASE WHEN ORD_MST.STATUS_FLG = 'C' THEN 1 ELSE 0 END), 0) AS IsCanceled -- 已取消`

| 欄位名稱 | 說明 | 計算邏輯 | 範例 |
| -------- | ---- | -------- | ---- |
| IsCanceled | 已取消 | ORD_MST.STATUS_FLG = 'C' | |

**直接來自關聯表、無原始欄位**：`,SOT.OrderTypeCode -- 訂單類型代碼` → 原始欄位名稱 `OrderTypeCode`。

**複雜計算**：

```sql
,CASE WHEN ORD_MST.STATUS_FLG != 'Y' OR ORD_MST.OK_DATE IS NULL THEN NULL
 ELSE DATEDIFF(DAY, GETDATE(), ORD_MST.OK_DATE) END AS RemainingDays
```

計算邏輯 `DATEDIFF(DAY, GETDATE(), ORD_MST.OK_DATE)`（核心表達式，忽略外層包裝）。
