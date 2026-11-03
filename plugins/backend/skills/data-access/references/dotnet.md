# 資料存取 .NET 附錄（EF Core + Dapper）

> 給 `data-access` skill 的 .NET 寫法。Part 1 Repository（BaseRepository、SqlGenerator、Expression→SQL），Part 2 Dapper 複雜查詢（CTE 分頁、排序白名單、動態 WHERE）。

## Part 1：Repository 介面與實作



### Instructions

1. 介面定義在 Domain 層：`Domain/Repositories/{Module}/`
2. 實作定義在 Persistence 層：`Persistence/Repositories/{Module}/{Entity}Repos/`
3. 繼承共用基底 `BaseRepository<TEntity, TKey>`（實作 `IBaseRepository<TEntity, TKey>`）
4. 複雜/自訂 SQL 用 Dapper；基本 CRUD 用 EF Core
5. 所有方法支援 `CancellationToken`

> 範例以中性領域 `Order`（訂單）示範，實作時替換為實際 Entity 名。

### Repository 介面範本

```csharp
using MyApp.Domain.Entities.{Module};

namespace MyApp.Domain.Repositories.{Module};

/// <summary>
/// {EntityDesc}儲存庫介面
/// </summary>
public interface I{Entity}Repository : IBaseRepository<{Entity}, string>
{
    /// <summary>
    /// 非同步建立{EntityDesc}
    /// </summary>
    Task<string?> CreateAsync(Create{Entity}Dto entity);

    /// <summary>
    /// 非同步更新{EntityDesc}
    /// </summary>
    Task UpdateAsync(Update{Entity}Dto entity);

    /// <summary>
    /// 非同步刪除{EntityDesc}
    /// </summary>
    Task DeleteAsync(Delete{Entity}Dto entity);

    /// <summary>
    /// 根據 ID 查詢{EntityDesc}
    /// </summary>
    Task<{Entity}?> GetByIdAsync(string id, CancellationToken cancellationToken = default);
}
```

### Repository 實作範本

```csharp
using MyApp.Domain.Dtos.{Module}.{Entity}Dtos;
using MyApp.Persistence.QueryGeneration;

namespace MyApp.Persistence.Repositories.{Module}.{Entity}Repos;

/// <summary>
/// 實作{EntityDesc}資料存取的類別
/// </summary>
public class {Entity}Repository : BaseRepository<{Entity}, string>, I{Entity}Repository
{
    /// <summary>
    /// 初始化 {Entity}Repository 類別的新執行個體
    /// </summary>
    public {Entity}Repository(AppDbContext context, IDbConnection dbConnection)
        : base(context, dbConnection)
    {
    }

    /// <inheritdoc/>
    public override async Task<{Entity}?> GetAsync(string id, CancellationToken cancellationToken)
    {
        return await Context.{Entity}s.FirstOrDefaultAsync(x => x.{Entity}Id == id, cancellationToken);
    }

    /// <inheritdoc/>
    public async Task<string?> CreateAsync(Create{Entity}Dto entity)
    {
        var (sql, parameters) = SqlGenerator.GenerateInsertQuery(entity);
        sql += Environment.NewLine + "SELECT SCOPE_IDENTITY();";
        return await DbConnection.ExecuteScalarAsync<string>(sql, parameters);
    }

    /// <inheritdoc/>
    public async Task UpdateAsync(Update{Entity}Dto entity)
    {
        var (sql, parameters) = SqlGenerator.GenerateUpdateQuery(entity);
        await DbConnection.ExecuteAsync(sql, parameters);
    }

    /// <inheritdoc/>
    public async Task DeleteAsync(Delete{Entity}Dto entity)
    {
        var sql = SqlGenerator.GenerateUpdateQuery<Delete{Entity}Dto>();
        await DbConnection.ExecuteAsync(sql, entity);
    }

    /// <inheritdoc/>
    public async Task<{Entity}?> GetByIdAsync(string id, CancellationToken cancellationToken = default)
    {
        return await Context.{Entity}s
            .Where(x => x.{Entity}Id == id && x.DeleteFlag == false)
            .FirstOrDefaultAsync(cancellationToken);
    }
}
```

### BaseRepository 常見繼承方法

共用基底 `BaseRepository<TEntity, TKey>` 通常已封裝下列方法，子類別直接沿用或 `override`：

| 方法 | 用途 | 回傳類型 |
|------|------|----------|
| `GetAsync(TKey id)` | 根據 ID 取得單一實體 | `Task<TEntity?>` |
| `GetAllAsync()` | 取得所有實體 | `Task<List<TEntity>>` |
| `GetByWhereCondition()` | EF Core 條件查詢 | `IQueryable<TEntity>` |
| `GetSqlByWhereConditionAsync()` | Dapper 條件查詢 | `Task<IEnumerable<TEntity>>` |
| `GetPagedAsync()` | 分頁查詢 | `Task<IPagedResponse<TEntity>>` |
| `CreateAsync()` | 建立實體 | `Task` |
| `Update()` | 更新實體 | `void` |
| `Delete()` | 刪除實體 | `void` |

> 若專案無現成基底，可將上表方法抽成 `BaseRepository` 泛型基底自建；重點是把 `Context`（EF Core）與 `DbConnection`（Dapper）兩條存取路徑統一暴露給子類別。

### SQL 產生器使用（若專案有 SqlGenerator 工具）

```csharp
// 產生 INSERT 語句
var (sql, parameters) = SqlGenerator.GenerateInsertQuery(entity);

// 產生 UPDATE 語句
var (sql, parameters) = SqlGenerator.GenerateUpdateQuery(entity);

// 參數替換為子查詢
sql = SqlGenerator.ReplaceParameterWithSubquery(sql, "@ParamName", "(SELECT ...)");

// 除錯用完整 SQL
var debugSql = SqlGenerator.BuildDebugSql(sql, parameters);
```

### Expression → SQL（若專案有 SqlExpressionVisitor 工具）

```csharp
// 將 LINQ Expression 轉換為 SQL
var (sql, param) = SqlExpressionVisitor<TEntity>.ToSqlQuery(
    predicate,
    ModuleStructure.{Module}
);

// 執行查詢
var results = await DbConnection.QueryAsync<TEntity>(sql: sql, param: param);
```

### 目錄結構

```
Domain/
└── Repositories/
    └── {Module}/
        └── I{Entity}Repository.cs
Persistence/
└── Repositories/
    └── {Module}/
        └── {Entity}Repos/
            └── {Entity}Repository.cs
```

### 注意事項

1. 使用 `Context` 存取 EF Core `DbContext`
2. 使用 `DbConnection` 存取 Dapper `IDbConnection`
3. 軟刪除用 `DeleteFlag = true` 標記，而非實體刪除
4. 所有方法都應支援 `CancellationToken`

## Part 2：Dapper 複雜查詢



### 選用工具（若專案有輔助類別）

#### SqlGenerator

```csharp
// 自動生成 SELECT（含 Column Mapping）
var sql = SqlGenerator.GenerateSelectQuery<Entity>(module);

// 生成 INSERT 並回傳參數
var (sql, parameters) = SqlGenerator.GenerateInsertQuery(entity);

// 生成 UPDATE
var (sql, parameters) = SqlGenerator.GenerateUpdateQuery(entity);
```

#### SqlExpressionVisitor

```csharp
// LINQ 轉 SQL WHERE（含分頁）
var (sql, parameters) = SqlExpressionVisitor<Entity>
    .ToSqlQuery(predicate, pagedRequest, module);
```

> 沒有上述工具時，直接手寫參數化 SQL 亦可；以下模式不依賴任何專屬工具。

### 分頁模式

Request 繼承共用 `PagedRequest`（`PagesSize`、`CurrentPage`、`SortBy[]`、`SortOrder[]`）。

分頁語法依**目標 SQL Server 版本**選擇：

- **CTE + `ROW_NUMBER()`**：相容性最廣，舊版（SQL Server 2008）唯一選項，新版亦可用。
- **`OFFSET / FETCH`**：SQL Server 2012 以上支援，語法較簡潔。若需相容 2008 則不可用。

下例採 CTE + `ROW_NUMBER()`（最大相容）：

#### CTE + ROW_NUMBER 分頁

```csharp
// RepositorySql — 建構分頁 SQL + 排序白名單
public static (string dataSql, string countSql) BuildPaged{Entity}Sql(
    string? keyword, string[]? sortBy, string[]? sortOrder)
{
    var conditions = new List<string> { "1=1" };
    if (!string.IsNullOrWhiteSpace(keyword))
        conditions.Add("t.Name LIKE '%' + @Keyword + '%'");
    var whereClause = string.Join(" AND ", conditions);

    // 排序白名單映射（防止 SQL Injection）
    var orderByClause = "t.CreatedDate DESC";
    if (sortBy != null && sortBy.Length > 0)
    {
        var orderParts = new List<string>();
        for (var i = 0; i < sortBy.Length; i++)
        {
            var column = sortBy[i]?.ToLowerInvariant() switch
            {
                "createddate" => "t.CreatedDate",
                "name"        => "t.Name",
                "code"        => "t.Code",
                _             => "t.CreatedDate"
            };
            var direction = (sortOrder != null && i < sortOrder.Length
                && sortOrder[i]?.ToUpperInvariant() == "ASC") ? "ASC" : "DESC";
            orderParts.Add($"{column} {direction}");
        }
        orderByClause = string.Join(", ", orderParts);
    }

    var dataSql = $@"
        ;WITH CTE AS (
            SELECT t.*, ROW_NUMBER() OVER (ORDER BY {orderByClause}) AS RowNum
            FROM dbo.TableName t WITH(NOLOCK)
            WHERE {whereClause}
        )
        SELECT * FROM CTE
        WHERE RowNum BETWEEN @Start AND @End";

    var countSql = $@"SELECT COUNT(*) FROM dbo.TableName t WITH(NOLOCK) WHERE {whereClause}";

    return (dataSql, countSql);
}
```

> 排序欄位**一律走白名單映射**，不可把 `sortBy` 字串直接串進 `ORDER BY`（SQL Injection）。

#### Repository 組裝 PagedResponse

```csharp
public async Task<IPagedResponse<EntityDto>> GetPagedAsync(
    string? keyword, int currentPage, int pagesSize,
    string[]? sortBy, string[]? sortOrder, CancellationToken cancellationToken)
{
    var (dataSql, countSql) = EntityRepositorySql.BuildPagedEntitySql(keyword, sortBy, sortOrder);
    var parameters = new DynamicParameters();
    parameters.Add("Start", (currentPage - 1) * pagesSize + 1);
    parameters.Add("End", currentPage * pagesSize);
    if (!string.IsNullOrWhiteSpace(keyword))
        parameters.Add("Keyword", keyword);

    var totalCount = await DbConnection.ExecuteScalarAsync<int>(countSql, parameters);
    var items = (await DbConnection.QueryAsync<EntityDto>(dataSql, parameters)).ToList();

    return new PagedResponse<EntityDto>(totalCount, currentPage, pagesSize) { Items = items };
}
```

### 標準模式

#### Repository 方法（多表 JOIN）

```csharp
public async Task<IEnumerable<TResult>> GetCustomQueryAsync(
    string condition,
    object parameters)
{
    var sql = $@"
        SELECT a.*, b.Name AS CategoryName
        FROM dbo.TableA a WITH(NOLOCK)
        INNER JOIN dbo.TableB b WITH(NOLOCK) ON a.CategoryId = b.Id
        WHERE {condition}";

    return await DbConnection.QueryAsync<TResult>(sql, parameters);
}
```

#### 參數化查詢

```csharp
// ✅ 正確：使用匿名物件
var result = await DbConnection.QueryAsync<Entity>(sql, new {
    Id = id,
    Status = "A"
});

// ❌ 禁止：字串串接（SQL Injection）
var sql = $"SELECT * FROM T WHERE Id = '{id}'";
```

#### 動態 WHERE

```csharp
var conditions = new List<string> { "1=1" };
var parameters = new DynamicParameters();

if (!string.IsNullOrEmpty(request.Keyword))
{
    conditions.Add("Name LIKE @Keyword");
    parameters.Add("Keyword", $"%{request.Keyword}%");
}

var whereClause = string.Join(" AND ", conditions);
```

### 提示

- 唯讀查詢可用 `WITH(NOLOCK)` 提升讀取效能（接受髒讀的前提下）
- 複雜 JOIN 優先用 Dapper，而非硬塞給 EF Core
- 回傳型別使用專用 DTO，避免 `dynamic`
- 值參數一律走 Dapper 參數；只有識別符（欄位/排序）才用白名單映射拼接

## 常見坑

- **`sortBy` 字串直接串進 `ORDER BY`**
  - 症狀：SQL Injection，或傳入不存在欄位時 500。
  - 原因：識別符無法參數化，直接拼接。
  - 修法：用白名單 `switch` 映射到實際欄位；值一律走 Dapper 參數。
- **在舊版 SQL Server 用 `OFFSET / FETCH`**
  - 症狀：語法錯誤（`Incorrect syntax near 'OFFSET'`）。
  - 原因：該語法需 SQL Server 2012 以上。
  - 修法：目標版本含 2008 時改用 CTE + `ROW_NUMBER()`。
- **`WITH(NOLOCK)` 用在需要一致性的查詢**
  - 症狀：讀到未提交、之後 rollback 的資料，或重複／漏列。
  - 原因：NOLOCK 等同 READ UNCOMMITTED。
  - 修法：只用在接受髒讀的報表／唯讀查詢；一致性要求高的查詢不用。
- **Dapper 回傳 `dynamic` 或整列 `SELECT *` 進 Handler**
  - 症狀：欄位改名後 runtime 才爆；Handler 內到處 `.Trim()`。
  - 原因：沒有專用 DTO，清洗沒止於 SQL 層。
  - 修法：用強型別 DTO；清洗（Trim／正規化）寫在 SQL。
- **軟刪除條件漏寫**
  - 症狀：已刪除的資料又出現在列表。
  - 原因：自訂 SQL 沒帶 `DeleteFlag = 0`，EF 的全域過濾器對 Dapper 無效。
  - 修法：每個自訂 SQL 明確帶刪除條件，寫進 Repository 測試。
