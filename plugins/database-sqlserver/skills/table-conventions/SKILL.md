---
name: table-conventions
description: Use when writing or reviewing SQL Server table (CREATE TABLE) scripts, or user says "資料表慣例", "table 命名規則", "怎麼建表", "table convention". Provides a convention framework for table file structure, column naming, audit columns, and alter scripts. 觸發：撰寫 `Table/**/*.sql` DDL 時。
---

# 資料表（Table）撰寫慣例

此為一套可調整的慣例框架。專案若已有自訂標準，以專案標準為準；沒有時可直接沿用下列預設。

## 檔案結構

- 以 `SET ANSI_NULLS ON` 和 `SET QUOTED_IDENTIFIER ON` 開頭
- 使用 `CREATE TABLE [Schema].[TableName]` 語法
- 主鍵使用 `CONSTRAINT [PK_TableName] PRIMARY KEY CLUSTERED`

範例：

```sql
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [Production].[Workstation]
(
    [WorkstationId]  int IDENTITY(1,1) NOT NULL,
    [WorkstationCode] nvarchar(20)     NOT NULL,
    [CreatedDate]    datetime2(7)      NOT NULL,
    [ModifiedDate]   datetime2(7)      NULL,
    [DeleteFlag]     bit               NOT NULL,
    CONSTRAINT [PK_Workstation] PRIMARY KEY CLUSTERED ([WorkstationId] ASC)
)
GO
```

## 欄位命名

- 使用 PascalCase（如 `WorkstationCode`、`CreatedDate`）
- 主鍵命名：`{TableName}Id`，型別為 `int IDENTITY(1,1)`
- 稽核欄位：包含 `CreatedDate` 和 `ModifiedDate`（`datetime2(7)`）
- 軟刪除使用 `DeleteFlag` 欄位（`bit NOT NULL`）

## Alter 腳本

- 位於 `Table/Alter/` 目錄，命名格式：`{來源資料表}_{YYYYMMDD}.sql`
- 用於修改由外部/既有系統帶入、非本專案 desired-state 管控的資料表

> 若專案的既有資料表沿用來源系統（例如 ERP、legacy 系統）的原始 schema，改動這類表時走 Alter 腳本；本專案自建的表則直接維護 `CREATE TABLE` desired-state 檔。
