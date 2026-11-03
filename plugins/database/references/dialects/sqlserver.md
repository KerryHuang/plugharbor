# SQL Server 方言附錄

適用：連線字串含 `Server=`／`Data Source=` 加 `Initial Catalog`／`Database`；csproj 有 `Microsoft.EntityFrameworkCore.SqlServer`；docker-compose image 為 `mcr.microsoft.com/mssql/server`。本附錄由舊 `database-sqlserver` plugin 搬來，為實戰驗證版。

## 型別對照

| 概念 | SQL Server | PostgreSQL | MySQL | SQLite |
|---|---|---|---|---|
| 32 位元整數 | `int` | `integer` | `int` | `INTEGER` |
| 64 位元整數 | `bigint` | `bigint` | `bigint` | `INTEGER` |
| 布林 | `bit` | `boolean` | `tinyint(1)`（`boolean` 為別名） | `INTEGER`（0／1） |
| 定點小數 | `decimal(p,s)` | `numeric(p,s)` | `decimal(p,s)` | `NUMERIC`（實為浮點或整數，慎用） |
| 浮點 | `float`／`real` | `double precision`／`real` | `double`／`float` | `REAL` |
| 變長 Unicode 字串 | `nvarchar(n)`／`nvarchar(max)` | `varchar(n)`／`text` | `varchar(n)`（utf8mb4）／`text` | `TEXT` |
| 定長字串 | `char(n)`／`nchar(n)` | `char(n)` | `char(n)` | `TEXT` |
| 日期時間 | `datetime2(7)` | `timestamp`／`timestamptz` | `datetime(6)`／`timestamp(6)` | `TEXT`（ISO 8601）或 `INTEGER` |
| 僅日期 | `date` | `date` | `date` | `TEXT` |
| GUID | `uniqueidentifier` | `uuid` | `char(36)`／`binary(16)` | `TEXT`／`BLOB` |
| 二進位 | `varbinary(max)` | `bytea` | `blob`／`longblob` | `BLOB` |
| JSON | `nvarchar(max)`＋`ISJSON` 檢查（新版另有 `json`） | `jsonb` | `json` | `TEXT`（JSON1 函式） |

重點：字串一律用 `nvarchar`（Unicode），除非確定只有 ASCII 且需省空間；日期時間用 `datetime2`，不用舊的 `datetime`（精度 3.33ms、範圍窄）。

## 識別欄／自動遞增

- 主鍵命名 `{TableName}Id`，型別 `int IDENTITY(1,1) NOT NULL`；預期超過 21 億筆用 `bigint IDENTITY(1,1)`。
- `IDENTITY` 不可直接 INSERT 值；需要時 `SET IDENTITY_INSERT [Schema].[T] ON` 並明列欄位，用完立刻 `OFF`。
- 取回新 id 用 `SCOPE_IDENTITY()`，不用 `@@IDENTITY`（會被 trigger 影響）。
- 另有 `SEQUENCE`（`NEXT VALUE FOR`）可跨表共用。
- 主鍵 `CONSTRAINT [PK_TableName] PRIMARY KEY CLUSTERED ([TableId] ASC)`。

## 分頁

```sql
SELECT ... FROM [Sales].[Order]
ORDER BY [CreatedDate] DESC, [OrderId] DESC   -- 必須有 ORDER BY，且含唯一鍵作 tie-breaker
OFFSET @skip ROWS FETCH NEXT @take ROWS ONLY;
```

`TOP (n)` 適合只取前 n 筆；深分頁（OFFSET 很大）改 keyset：`WHERE CreatedDate < @d OR (CreatedDate = @d AND OrderId < @id)`。

## 命名慣例與大小寫

- 物件與欄位用 PascalCase（`WorkstationCode`、`CreatedDate`），以 `[ ]` 括起。
- Schema 對應領域（Sales、Production、HumanResources…），寫成 `[Schema].[Name]`。
- 約束命名：`PK_Table`、`FK_Child_Parent`、`UQ_Table_Col`、`IX_Table_Col`、`DF_Table_Col`、`CK_Table_Rule`。
- View：PascalCase＋`View` 後綴（`SalesOrderView`）。
- 識別字與字串比較是否分大小寫取決於 collation（預設 `*_CI_AS` 不分大小寫）。

## 預設值與約束

```sql
[CreatedDate] datetime2(7) NOT NULL CONSTRAINT [DF_Workstation_CreatedDate] DEFAULT (SYSUTCDATETIME()),
[DeleteFlag]  bit          NOT NULL CONSTRAINT [DF_Workstation_DeleteFlag]  DEFAULT (0),
CONSTRAINT [CK_Order_Qty] CHECK ([Qty] >= 0),
CONSTRAINT [FK_Order_Customer] FOREIGN KEY ([CustomerId]) REFERENCES [Sales].[Customer]([CustomerId])
```

- 預設值約束要自行命名，否則系統產生隨機名稱，日後 DROP COLUMN 前得先查名稱。
- 新增 NOT NULL 欄位到既有資料表：給 `DEFAULT`，或分三步（加 NULL 欄 → 回填 → 改 NOT NULL）。
- 稽核欄：`CreatedDate`、`ModifiedDate`（`datetime2(7)`）；軟刪除 `DeleteFlag bit NOT NULL`。

## 日期時間與時區

- `datetime2` 不含時區；`datetimeoffset` 含位移。建議存 UTC（`SYSUTCDATETIME()`），顯示端轉換。
- `GETDATE()` 回傳 `datetime`（本機時區）；要 `datetime2` 精度用 `SYSDATETIME()`。
- 時區轉換：`dt AT TIME ZONE 'UTC' AT TIME ZONE 'Taipei Standard Time'`（時區名為 Windows 名稱）。
- 日期區間用半開區間 `>= @from AND < @to`，不用 `BETWEEN` 處理 datetime2。

## 說明（comment／extended property）怎麼寫

SQL Server 用 extended property（`MS_Description`）：

```sql
EXEC sys.sp_addextendedproperty @name = N'MS_Description', @value = N'工作站',
     @level0type = N'SCHEMA', @level0name = N'Production',
     @level1type = N'TABLE',  @level1name = N'Workstation';
EXEC sys.sp_addextendedproperty @name = N'MS_Description', @value = N'工作站代碼',
     @level0type = N'SCHEMA', @level0name = N'Production',
     @level1type = N'TABLE',  @level1name = N'Workstation',
     @level2type = N'COLUMN', @level2name = N'WorkstationCode';
```

已存在改用 `sp_updateextendedproperty`。View 的欄位說明常直接寫在 SELECT 行末註解（見下節）。

## migration 工具

- EF Core：見 `${CLAUDE_PLUGIN_ROOT}/references/orm/ef-core.md`。
- 純 SQL：desired-state 的 `Table/**/*.sql`、`View/**/*.sql`（view 用 `CREATE OR ALTER VIEW`）；外部系統帶入的表用 `Table/Alter/{來源資料表}_{YYYYMMDD}.sql`。
- 其他：DACPAC／SSDT、Flyway、DbUp。
- 腳本冪等：`IF OBJECT_ID('Schema.Table', 'U') IS NOT NULL`、`IF COL_LENGTH('Schema.Table','Col') IS NULL`。

## Table 檔案結構與範例

- 以 `SET ANSI_NULLS ON`、`SET QUOTED_IDENTIFIER ON` 開頭（各自 `GO` 分批）。
- 使用 `CREATE TABLE [Schema].[TableName]`；主鍵 `CONSTRAINT [PK_TableName] PRIMARY KEY CLUSTERED`。

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

Alter 腳本：位於 `Table/Alter/`，命名 `{來源資料表}_{YYYYMMDD}.sql`，用於修改由外部／既有系統（ERP、legacy）帶入、非本專案 desired-state 管控的表；本專案自建的表直接維護 `CREATE TABLE` desired-state 檔。

## View 檔案結構與範例

- 開頭同 table；使用 `CREATE OR ALTER VIEW`。
- SELECT：第一個欄位前不加逗號，後續欄位逗號開頭；`AS` 映射為 PascalCase 英文名；用分類註解（`-- 訂單`、`-- 時間`）分組。
- JOIN：所有資料表加 `WITH(NOLOCK)`；JOIN 行末註解關聯表用途；優先 `LEFT JOIN`。

```sql
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

注意：`WITH(NOLOCK)` 等同 READ UNCOMMITTED，可能讀到未提交、重複或遺漏的資料；僅適合報表類 view，對一致性要求高的改用 `READ_COMMITTED_SNAPSHOT`。

## View 計算欄位關鍵字（供 schema-docs 解析）

`CASE WHEN`、`CONVERT(BIT,`、`ISNULL(`、`DATEDIFF(`。布林型計算欄位 `ISNULL(CONVERT(BIT, CASE WHEN ... THEN 1 ELSE 0 END), 0)`：計算邏輯取 `CASE WHEN` 條件；`DATEDIFF(DAY, GETDATE(), X)` 取函式本身。`WITH(NOLOCK)` 是 table hint，解析 FROM／JOIN 表名時忽略。

## 常見坑

- **Invalid column name 'XXX'**
  - 症狀：migration 或腳本在 `ALTER TABLE ... ADD` 後接 `UPDATE`，報欄位不存在。
  - 原因：同一批次內 DDL 後接 DML，編譯階段欄位尚未存在。
  - 修法：DML 包 `EXEC('...')` 延遲編譯：
    ```sql
    ALTER TABLE T ADD NewCol char(10) NULL;
    EXEC('UPDATE T SET NewCol = ''x'' WHERE NewCol IS NULL');
    ```
- **Cannot find the object "Schema.Table"**
  - 症狀：新環境套用 migration 失敗。
  - 原因：腳本假設舊表存在（表由外部系統建立）。
  - 修法：用 `IF OBJECT_ID('Schema.Table', 'U') IS NOT NULL` 守衛。
- **IDENTITY_INSERT 錯誤**
  - 症狀：`Cannot insert explicit value for identity column`。
  - 原因：直接 INSERT 值給 IDENTITY 欄。
  - 修法：`SET IDENTITY_INSERT ... ON` 並明列欄位清單，結束後 `OFF`（同一 session 同時只能對一張表開）。
- **datetime 精度／範圍不符**
  - 症狀：`datetime2` 轉 `datetime` 溢位或毫秒被截。
  - 原因：舊 `datetime` 範圍 1753 起、精度 3.33ms。
  - 修法：統一用 `datetime2(7)`，比對時兩邊同型別。
- **字串比對結果與預期不同**
  - 症狀：`WHERE Name = N'x'` 筆數不如預期，或索引沒被用到。
  - 原因：collation 不分大小寫／重音；字面值缺 `N` 前綴造成隱含轉換。
  - 修法：Unicode 欄位字面值加 `N''`；需精確比對時指定 `COLLATE`。
- **驗 DDL 語法丟給唯讀查詢工具**
  - 症狀：「唯讀」工具實際執行了含 DDL 的批次。
  - 原因：工具不一定擋 DDL。
  - 修法：驗語法只送純 SELECT，DDL 在測試環境人工執行。
