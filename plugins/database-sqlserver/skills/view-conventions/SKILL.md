---
name: view-conventions
description: Use when writing or reviewing SQL Server view (CREATE VIEW) scripts, or user says "檢視表慣例", "view 命名規則", "怎麼建 view", "view convention". Provides a convention framework for view file structure, SELECT column formatting, JOIN style, and naming. 觸發：撰寫 `View/**/*.sql` DDL 時。
---

# 檢視表（View）撰寫慣例

此為一套可調整的慣例框架。專案若已有自訂標準，以專案標準為準；沒有時可直接沿用下列預設。

## 檔案結構

- 以 `SET ANSI_NULLS ON` 和 `SET QUOTED_IDENTIFIER ON` 開頭
- 使用 `CREATE OR ALTER VIEW` 語法

## SELECT 欄位格式

- 第一個欄位前不加逗號，後續欄位以逗號開頭：`,欄位名 AS 英文名`
- 使用 `AS` 映射為 PascalCase 英文名稱
- 使用分類註解分組相關欄位（如 `-- 訂單`、`-- 時間`）

範例：

```sql
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

CREATE OR ALTER VIEW [Sales].[SalesOrderView]
AS
SELECT
    -- 訂單
     ORD_MST.ORD_NO   AS OrderId       -- 訂單編號 (ORD_NO)
    ,ORD_MST.CUST_NO  AS CustomerId    -- 客戶編號 (CUST_NO) [CUST]
    -- 時間
    ,ORD_MST.OK_DATE  AS CompletedDate -- 完成日期 (OK_DATE)
FROM ORD_MST WITH(NOLOCK)
LEFT JOIN CUST WITH(NOLOCK) -- 客戶
    ON ORD_MST.CUST_NO = CUST.CUST_NO
GO
```

## JOIN 慣例

- 所有資料表使用 `WITH(NOLOCK)`
- 在 JOIN 行末加註解說明關聯表用途
- 優先使用 `LEFT JOIN`

## 命名

- View 名稱使用 PascalCase 加 `View` 後綴（如 `SalesOrderView`）
- Schema 須對應領域（如 Sales、Production、HumanResources 等）
