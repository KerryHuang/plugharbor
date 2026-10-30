---
name: dapper-query
description: 生成 Dapper 複雜查詢，含參數化查詢、多表 JOIN、CTE + ROW_NUMBER 分頁、排序白名單防注入。Use when 撰寫複雜 SQL 查詢、建立 Repository 的 Dapper 方法、處理 EF Core 難以有效處理的查詢、dapper query、複雜 join、raw sql 分頁。
---

# Dapper 複雜查詢

## 選用工具（若專案有輔助類別）

### SqlGenerator

```csharp
// 自動生成 SELECT（含 Column Mapping）
var sql = SqlGenerator.GenerateSelectQuery<Entity>(module);

// 生成 INSERT 並回傳參數
var (sql, parameters) = SqlGenerator.GenerateInsertQuery(entity);

// 生成 UPDATE
var (sql, parameters) = SqlGenerator.GenerateUpdateQuery(entity);
```

### SqlExpressionVisitor

```csharp
// LINQ 轉 SQL WHERE（含分頁）
var (sql, parameters) = SqlExpressionVisitor<Entity>
    .ToSqlQuery(predicate, pagedRequest, module);
```

> 沒有上述工具時，直接手寫參數化 SQL 亦可；以下模式不依賴任何專屬工具。

## 分頁模式

Request 繼承共用 `PagedRequest`（`PagesSize`、`CurrentPage`、`SortBy[]`、`SortOrder[]`）。

分頁語法依**目標 SQL Server 版本**選擇：

- **CTE + `ROW_NUMBER()`**：相容性最廣，舊版（SQL Server 2008）唯一選項，新版亦可用。
- **`OFFSET / FETCH`**：SQL Server 2012 以上支援，語法較簡潔。若需相容 2008 則不可用。

下例採 CTE + `ROW_NUMBER()`（最大相容）：

### CTE + ROW_NUMBER 分頁

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

### Repository 組裝 PagedResponse

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

## 標準模式

### Repository 方法（多表 JOIN）

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

### 參數化查詢

```csharp
// ✅ 正確：使用匿名物件
var result = await DbConnection.QueryAsync<Entity>(sql, new {
    Id = id,
    Status = "A"
});

// ❌ 禁止：字串串接（SQL Injection）
var sql = $"SELECT * FROM T WHERE Id = '{id}'";
```

### 動態 WHERE

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

## 提示

- 唯讀查詢可用 `WITH(NOLOCK)` 提升讀取效能（接受髒讀的前提下）
- 複雜 JOIN 優先用 Dapper，而非硬塞給 EF Core
- 回傳型別使用專用 DTO，避免 `dynamic`
- 值參數一律走 Dapper 參數；只有識別符（欄位/排序）才用白名單映射拼接
