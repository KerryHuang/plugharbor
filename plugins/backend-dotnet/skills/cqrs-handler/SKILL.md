---
name: cqrs-handler
description: 生成 MediatR CQRS Command/Query Handler，遵循 .NET Clean Architecture。建立 Create/Update/Delete Command 與 Get/GetFilter/GetPaged Query、Notification 事件、以及 TransactionBehavior 交易管線。Use when 新增 MediatR Handler、實作 CRUD 操作、cqrs handler、command handler、query handler、mediatr handler。
---

# CQRS Handler 生成

## Instructions

1. 確定目標模組（如 Sales、Inventory、Catalog、Purchasing 等），依團隊分層命名
2. 依 Clean Architecture 目錄結構建檔：`Application/{Module}/{Entity}Service/`
3. 沿用專案既有的 `ServiceResult`、`IUnitOfWork`、`IMapper`（Result pattern + Unit of Work + 物件映射）
4. 所有類別與方法加上 XML 文件註解
5. 一律以 `CancellationToken` 支援取消操作

> 範例以中性領域 `Order`（訂單）示範，實作時替換為實際 Entity 名。

## Command Handler 範本

```csharp
using MyApp.Persistence.Repositories.{Module}.{Entity}Repos;

namespace MyApp.Application.{Module}.{Entity}Service.Commands;

public class Create{Entity}Handler : IRequestHandler<Create{Entity}Request, ServiceResult>
{
    private readonly ILogger<Create{Entity}Handler> _logger;
    private readonly IMapper _mapper;
    private readonly IUnitOfWork _unitOfWork;
    private readonly I{Entity}Repository _{entity}Repository;

    public Create{Entity}Handler(
        ILogger<Create{Entity}Handler> logger, IMapper mapper,
        IUnitOfWork unitOfWork, I{Entity}Repository {entity}Repository)
    {
        // ... 欄位指派
    }

    public async Task<ServiceResult> Handle(Create{Entity}Request request, CancellationToken cancellationToken)
    {
        try
        {
            var id = await _{entity}Repository.CreateAsync(request);
            await _unitOfWork.CommitAsync(cancellationToken);
            return ServiceResult.Success(data: id ?? request.{Entity}Id);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, ex.Message);
            return ServiceResult.Failure(message: ex.Message);
        }
    }
}
```

## Query Handler 範本（GetFilter）

```csharp
namespace MyApp.Application.{Module}.{Entity}Service.Queries;

public class GetFilter{Entity}Handler : IRequestHandler<GetFilter{Entity}Request, List<Get{Entity}Response>>
{
    private readonly IMapper _mapper;
    private readonly I{Entity}Repository _{entity}Repository;

    // ... 建構函式注入

    public async Task<List<Get{Entity}Response>> Handle(GetFilter{Entity}Request request, CancellationToken cancellationToken)
    {
        var expression = {Entity}FilterExpression.CreateFilterExpression(request);
        var entities = await _{entity}Repository.GetSqlByWhereConditionAsync(expression, ModuleStructure.{Module});
        return _mapper.Map<List<Get{Entity}Response>>(entities);
    }
}
```

## Paged Handler 範本

| 比較 | EF Core 路徑 | Dapper 路徑 |
|------|-------------|-------------|
| Request 繼承 | `{Entity}PagedModel : PagedRequest` | `PagedRequest` |
| 回傳類型 | `IPagedResponse<Get{Entity}Response>` | `IPagedResponse<{Entity}Dto>` |
| 篩選方式 | `FilterExpression` + `GetPagedAsync` | Repository 自訂方法 |
| 排序設定 | 由 Repository 處理 | Handler 設定預設排序 |
| 額外模型 | `{Entity}FilterModel`, `{Entity}PagedModel` | 無（Request 直接帶參數） |

```csharp
// === EF Core 路徑 ===
public class GetPaged{Entity}Request : {Entity}PagedModel, IRequest<IPagedResponse<Get{Entity}Response>> { }

public class GetPaged{Entity}Handler : IRequestHandler<GetPaged{Entity}Request, IPagedResponse<Get{Entity}Response>>
{
    private readonly I{Entity}Repository _{entity}Repository;
    // ... 建構函式注入

    public async Task<IPagedResponse<Get{Entity}Response>> Handle(
        GetPaged{Entity}Request request, CancellationToken cancellationToken)
    {
        var filterModel = new {Entity}FilterModel { /* 從 request 映射 */ };
        var expression = {Entity}FilterExpression.CreateFilterExpression(filterModel);
        return await _{entity}Repository.GetPagedAsync(expression, request);
    }
}

// === Dapper 路徑 ===
public class GetPaged{Entity}Request : PagedRequest, IRequest<IPagedResponse<{Entity}Dto>>
{
    public List<string>? Ids { get; set; }
    public string? Keywords { get; set; }
}

public class GetPaged{Entity}Handler : IRequestHandler<GetPaged{Entity}Request, IPagedResponse<{Entity}Dto>>
{
    // ... 建構函式注入

    public async Task<IPagedResponse<{Entity}Dto>> Handle(
        GetPaged{Entity}Request request, CancellationToken cancellationToken)
    {
        if (request.SortBy == null || request.SortBy.Length == 0)
        {
            request.SortBy = ["{DefaultSortField}"];
            request.SortOrder = ["DESC"];
        }
        return await _{entity}Repository.GetPaged{Entity}Async(
            request.Ids, request.Keywords,
            request.CurrentPage, request.PagesSize,
            request.SortBy, request.SortOrder, cancellationToken);
    }
}
```

## Notification Handler 範本

當 Command 完成後需觸發多個副作用（Email、庫存調整、審計日誌等），使用 Notification（一對多）。

```csharp
// 1. 定義 Notification（事件）
namespace MyApp.Application.{Module}.{Entity}Service.Notifications;

public record {Entity}CreatedNotification(
    string {Entity}Id, string OperatorId, DateTime CreatedAt
) : INotification;

// 2. 定義 Handler（訂閱者）
public class Audit{Entity}CreatedHandler : INotificationHandler<{Entity}CreatedNotification>
{
    private readonly ILogger<Audit{Entity}CreatedHandler> _logger;
    // ... 建構函式注入

    public Task Handle({Entity}CreatedNotification notification, CancellationToken cancellationToken)
    {
        _logger.LogInformation("{EntityDesc}建立: {Id}", notification.{Entity}Id);
        return Task.CompletedTask;
    }
}

// 3. 在 Command Handler 中發布
await _unitOfWork.CommitAsync(cancellationToken);
await _mediator.Publish(new {Entity}CreatedNotification(id, operatorId, DateTime.UtcNow), cancellationToken);
```

## 交易模式選用（TransactionBehavior 管線）

寫 Handler 涉及多筆寫入需原子性時，先選模式（**禁止** `TransactionScope`，跨連線/分散式交易不可控）：

| 情境 | 做法 |
|------|------|
| 一般 CRUD 多寫入需原子性（多數情境） | Request 標記 `ITransactionalRequest`，交易由 `TransactionBehavior` MediatR pipeline behavior 自動包裹 |
| 需中途控制交易（分段 commit、條件式 rollback、交易內重試、自訂 isolation） | **不標** marker，handler 內顯式 `Database.BeginTransactionAsync()` 自管 |
| 交易內呼叫 Dapper（不論上述哪種） | **免傳** `transaction:` 參數——由連線裝飾器自動掛上當前交易（EF 或 raw） |

實作 `TransactionBehavior` 的四要點：

- **runtime marker 檢查**（`where TRequest : notnull` + `request is not ITransactionalRequest` 直通）——open generic 註冊下泛型約束無法攔 marker
- **`ServiceResult { IsSuccess: false }` 也要 rollback**（不只 exception）；自訂 Response 型別若代表失敗**必須 throw**，否則會被誤 commit
- **SafeRollback** 容忍伺服器端已中止的 zombie 交易（rollback 失敗只 LogWarning，保留原始例外）
- **巢狀 Send 自動 join**（偵測 `CurrentTransaction` 已存在），由最外層擁有 commit/rollback

> 交易 behavior 的禁忌：交易內禁 `Publish`、禁外部 I/O（HTTP/檔案/MQ）、鎖窗口設 timeout、共用連線禁 raw `BeginTransaction()`。

### 常見 MediatR Behaviors

| Behavior | 用途 |
|----------|------|
| `LoggingBehavior` | 記錄 Request 進出 |
| `ValidationBehavior` | FluentValidation 自動驗證 |
| `TransactionBehavior` | 交易管理（`ITransactionalRequest` marker） |
| `PerformanceBehavior` | 慢請求警告 |

## 檔案結構

```
{Module}/{Entity}Service/
├── Commands/
│   ├── Create{Entity}Request.cs / Create{Entity}Handler.cs
│   ├── Update{Entity}Request.cs / Update{Entity}Handler.cs
│   └── Delete{Entity}Request.cs / Delete{Entity}Handler.cs
├── Queries/
│   ├── Get{Entity}/         (Request + Handler)
│   ├── GetFilter{Entity}/   (Request + Handler)
│   └── GetPaged{Entity}/    (Request + Handler)
├── Notifications/            ← 選擇性
│   ├── {Entity}CreatedNotification.cs
│   └── Audit{Entity}CreatedHandler.cs
├── Models/
│   ├── Get{Entity}Response.cs / GetLight{Entity}Response.cs
│   ├── {Entity}PagedModel.cs          ← EF Core 路徑
│   └── {Entity}FilterModel.cs         ← EF Core 路徑
├── Mappers/
│   └── {Entity}Mapper.cs
├── DataValidation/
│   └── GetPaged{Entity}RequestValidator.cs
└── Helpers/
    └── {Entity}FilterExpression.cs    ← EF Core 路徑
```

## Handler 內注入領域服務

Handler 需要單號產生、公司別/租戶判斷等領域邏輯時，一律**注入領域服務介面**，不在 Handler 內直查資料表。

```csharp
// 範例：注入單號產生服務
private readonly ISerialNumberService _serialNumberService;

var no = await _serialNumberService.GenerateNextAsync("Order", "OrderNo");

// 範例：注入租戶/公司別服務做條件邏輯
private readonly ITenantService _tenantService;

if (await _tenantService.IsAsync("TenantA"))
{
    // 特定租戶專屬邏輯
}
```

> 領域判斷（公司別、租戶、組態）統一透過服務介面，**禁止**在 Handler 內直接查設定表。

## 回傳類型規則

| 操作類型 | 回傳類型 |
|---------|---------|
| Commands | `ServiceResult` 或 `ServiceResult<T>` |
| Get Single | `T?` (nullable) |
| GetFilter | `List<T>` |
| GetPaged | `IPagedResponse<T>` |
| Notification | `void`（INotification 無回傳值） |
