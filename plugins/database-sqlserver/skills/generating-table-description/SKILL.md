---
name: generating-table-description
description: Use when generating table description documentation from SQL view files. Use when user says "產生資料表描述", "文件化檢視表", "更新 TableDescription", "由 view 產欄位對照". Use when user wants to document view-to-table field mappings for a SQL Server database.
---

# 產生資料表結構說明文件

## 概述

從 SQL 檢視表（View）檔案解析欄位映射、關聯關係及計算邏輯，產生標準化的 Markdown 資料表結構說明文件。

**核心原則：** 嚴格按照主表、關聯表、計算欄位分組。每個欄位都必須正確歸類。

## 步驟

### 步驟 1：解析檔案

1. 讀取指定的檢視表 SQL 檔案
2. 從 `FROM` 語句提取主表名稱
3. 從 `LEFT JOIN` 語句提取所有關聯表及其關聯條件
4. 從檔案名稱提取功能分類和中文名稱

### 步驟 2：解析 SELECT 欄位

逐行解析，提取：
- `原始欄位 AS 新欄位名稱` 映射
- 行末註解：`-- 中文說明 (原始欄位) [關聯表] {選項值}`
- 分類註解（如 `-- 訂單`、`-- 時間`）

### 步驟 3：分類欄位

**必須按以下順序分為三類：**

| 類別 | 判斷依據 | 表格欄位 |
|------|----------|----------|
| **主表欄位** | 來自 FROM 主表 | 原始欄位名稱 / 新欄位名稱 / 說明 / 關聯 / 範例 |
| **關聯表欄位** | 來自 LEFT JOIN 表，按字母排序 | 原始欄位名稱 / 新欄位名稱 / 說明 / 關聯 / 範例 |
| **計算欄位** | 含 CASE WHEN / CONVERT(BIT / ISNULL / DATEDIFF | 欄位名稱 / 說明 / 計算邏輯 / 範例 |

### 步驟 4：產生 Markdown

輸出格式：

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
- [ ] 欄位正確分組（主表/關聯表/計算欄位）
- [ ] 關聯關係準確（格式：`表名.欄位`）
- [ ] 計算欄位提取核心邏輯（忽略 ISNULL/CONVERT 包裝）
- [ ] 選項值 `{...}` 包含在說明中

## 注意事項

- 忽略被註解的欄位（`-- ,欄位名稱`）
- 布林型計算欄位（`CONVERT(BIT, CASE WHEN ...)`）：提取 `CASE WHEN` 條件作為計算邏輯
- 同一表格的多個別名（如 `SEMP`, `PEMP`）需統一處理
- 範例欄位保持空白

## 完整轉換規則

### 規則 1：欄位映射提取

從 SELECT 語句中提取 `原始欄位 AS 新欄位名稱` 的映射關係：
- **來源**：`ORD_MST.ORD_NO AS OrderId`
- **提取**：原始欄位名稱 = `ORD_NO`，新欄位名稱 = `OrderId`

### 規則 2：說明文字提取

從註解中提取欄位說明：
- **格式**：`-- 訂單編號 (ORD_NO)`
- **提取**：說明 = `訂單編號`，原始欄位確認 = `ORD_NO`

### 規則 3：關聯關係提取

**A. JOIN 語句**

```sql
LEFT JOIN CUST WITH(NOLOCK) -- 客戶
    ON ORD_MST.CUST_NO = CUST.CUST_NO
```
提取：關聯表 = `CUST`，關聯欄位 = `CUST_NO`

**B. 註解中的關聯標記**

```sql
-- 客戶編號 (CUST_NO) [CUST]
```
提取：關聯 = `CUST.CUST_NO`

**C. 外鍵關聯格式**

```sql
-- 業務人員編號 [EMP].[EMP_NO]
```
提取：關聯 = `EMP.EMP_NO`

### 規則 4：表格分組規則

1. **主表**：FROM 語句中的主要表格
2. **關聯表**：LEFT JOIN 中出現的表格，按字母順序排列
3. **計算欄位**：包含 CASE WHEN、CONVERT、ISNULL 等計算邏輯的欄位

### 規則 5：特殊欄位處理

**A. 計算欄位識別關鍵字**：`CASE WHEN`、`CONVERT(BIT,`、`ISNULL(`、`DATEDIFF(`

**B. 布林型計算欄位**

```sql
,ISNULL(CONVERT(BIT, CASE WHEN ORD_MST.STATUS_FLG = 'C' THEN 1 ELSE 0 END), 0) AS IsCanceled
```
- **說明**：已取消
- **計算邏輯**：`ORD_MST.STATUS_FLG = 'C'`

### 規則 6：額外資訊處理

**A. 大括號內的選項值**

```sql
-- 訂單狀態代碼 (STATUS_FLG) {未結=O,結案=Y,暫停=P,作廢=C}
```
說明須包含選項值的完整內容。

**B. 方括號內的關聯說明**

```sql
-- 文件編號 [外部系統訂單編號]
```
說明須包含業務描述的完整內容。

## 詳細轉換範例

**範例 1 — 基本欄位轉換**

SQL：`ORD_MST.ORD_NO AS OrderId -- 訂單編號 (ORD_NO)`

| 原始欄位名稱 | 新欄位名稱 | 說明 | 關聯 | 範例 |
| ------------ | ---------- | ---- | ---- | ---- |
| ORD_NO | OrderId | 訂單編號 | | |

**範例 2 — 含關聯資訊的欄位**

SQL：`ORD_MST.CUST_NO AS CustomerId -- 客戶編號 (CUST_NO) [CUST]`

| 原始欄位名稱 | 新欄位名稱 | 說明 | 關聯 | 範例 |
| ------------ | ---------- | ---- | ---- | ---- |
| CUST_NO | CustomerId | 客戶編號 | CUST.CUST_NO | |

**範例 3 — 含選項值的欄位**

SQL：`ORD_MST.TYPE1 AS OrderTypeName -- 訂單類型名稱 (TYPE1) {標準/急件}`

| 原始欄位名稱 | 新欄位名稱 | 說明 | 關聯 | 範例 |
| ------------ | ---------- | ---- | ---- | ---- |
| TYPE1 | OrderTypeName | 訂單類型名稱 {標準/急件} | | |

**範例 4 — 計算欄位**

SQL：`,ISNULL(CONVERT(BIT, CASE WHEN ORD_MST.STATUS_FLG = 'C' THEN 1 ELSE 0 END), 0) AS IsCanceled -- 已取消`

| 欄位名稱 | 說明 | 計算邏輯 | 範例 |
| -------- | ---- | -------- | ---- |
| IsCanceled | 已取消 | ORD_MST.STATUS_FLG = 'C' | |

## 常見問題

**沒有原始欄位的情況**：對於直接來自關聯表的欄位，原始欄位名稱使用關聯表的欄位名稱：

```sql
,SOT.OrderTypeCode -- 訂單類型代碼
```
原始欄位名稱 = `OrderTypeCode`

**複雜的計算邏輯**：提取核心條件作為計算邏輯，忽略 ISNULL、CONVERT 等包裝函數：

```sql
,CASE WHEN ORD_MST.STATUS_FLG != 'Y' OR ORD_MST.OK_DATE IS NULL THEN NULL
 ELSE DATEDIFF(DAY, GETDATE(), ORD_MST.OK_DATE) END AS RemainingDays
```
計算邏輯 = `DATEDIFF(DAY, GETDATE(), ORD_MST.OK_DATE)`

**多表同名欄位**：優先使用主表的欄位；若來自關聯表則在說明中標註來源表。
