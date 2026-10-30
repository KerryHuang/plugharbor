---
name: repository-pattern
description: 生成 Repository 介面與實作，繼承共用 BaseRepository，混用 Dapper 自訂 SQL 與 EF Core CRUD。Use when 建立新 Repository、實作資料存取層、新增自訂查詢方法、repository pattern、data access layer。
---

# Repository Pattern 生成

## Instructions

1. 介面定義在 Domain 層：`Domain/Repositories/{Module}/`
2. 實作定義在 Persistence 層：`Persistence/Repositories/{Module}/{Entity}Repos/`
3. 繼承共用基底 `BaseRepository<TEntity, TKey>`（實作 `IBaseRepository<TEntity, TKey>`）
4. 複雜/自訂 SQL 用 Dapper；基本 CRUD 用 EF Core
5. 所有方法支援 `CancellationToken`

> 範例以中性領域 `Order`（訂單）示範，實作時替換為實際 Entity 名。

## Repository 介面範本

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

## Repository 實作範本

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

## BaseRepository 常見繼承方法

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

## SQL 產生器使用（若專案有 SqlGenerator 工具）

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

## Expression → SQL（若專案有 SqlExpressionVisitor 工具）

```csharp
// 將 LINQ Expression 轉換為 SQL
var (sql, param) = SqlExpressionVisitor<TEntity>.ToSqlQuery(
    predicate,
    ModuleStructure.{Module}
);

// 執行查詢
var results = await DbConnection.QueryAsync<TEntity>(sql: sql, param: param);
```

## 目錄結構

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

## 注意事項

1. 使用 `Context` 存取 EF Core `DbContext`
2. 使用 `DbConnection` 存取 Dapper `IDbConnection`
3. 軟刪除用 `DeleteFlag = true` 標記，而非實體刪除
4. 所有方法都應支援 `CancellationToken`
