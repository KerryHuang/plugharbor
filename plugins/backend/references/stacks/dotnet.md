# .NET 附錄（共用）

> backend 各 skill 與 `dev-flow` 通用 agent 共用的 .NET 寫法：專案結構、依賴規則、DI 註冊、各層範本、指令、agent 補充。技術專屬的長範例在各 skill 自己 references 目錄裡的 dotnet.md（見下表）。
> 偵測線索：`*.csproj`／`*.sln`。範例以中性領域 `Order`（訂單）示範，namespace `MyApp.*` 為示意，請對齊專案實際命名。

## 各 skill 的 .NET 附錄索引

| Skill | 附錄 |
|---|---|
| `layered-architecture` | 本檔（下方「Clean Architecture 分層範本」） |
| `cqrs` | `skills/cqrs/references/dotnet.md`（MediatR Handler、Notification、TransactionBehavior） |
| `data-access` | `skills/data-access/references/dotnet.md`（BaseRepository、Dapper 分頁） |
| `domain-model` | `skills/domain-model/references/dotnet.md`（EF Core Entity、Ext 表） |
| `api-endpoint` | `skills/api-endpoint/references/dotnet.md`（Controller、版本控制） |
| `background-job` | `skills/background-job/references/dotnet.md`（Hangfire） |
| `unit-testing` | `skills/unit-testing/references/dotnet.md`、`dotnet-templates.md`（xUnit／Moq） |

# Clean Architecture 分層範本



以四層（Domain / Application / Infrastructure / WebJob）示範；若專案以 WebAPI 為進入層，把 `WebJob` 換成 `WebAPI` 即可，依賴規則不變。

## 分層規則

| 層級 | 專案 | 可依賴 | 禁止依賴 |
|------|------|--------|----------|
| Domain | `.Domain` | 無 | 任何層 |
| Application | `.Application` | Domain | Infrastructure, WebJob |
| Infrastructure | `.Infrastructure` | Domain, Application | WebJob |
| WebJob | `.WebJob` | 全部 | - |

依賴方向一律**由外向內**：外層知道內層，內層不知道外層。Domain 不引用任何框架相依（純 POCO + 介面）。

## 新功能開發順序

```
1. Domain     → Entity + Interface
2. Application → Service
3. Infrastructure → Repository
4. WebJob     → Job / Controller
```

## 快速參考

| 層級 | 路徑 | 內容 |
|------|------|------|
| Domain | `MyApp.Domain/` | Entities, Interfaces |
| Application | `MyApp.Application/` | Services, DTOs |
| Infrastructure | `MyApp.Infrastructure/` | Repositories, DbContext |
| WebJob | `MyApp.WebJob/` | Jobs, Controllers |

## DI 註冊位置

| 類型 | 註冊檔案 |
|------|----------|
| Service | `Application/Extensions/ServiceExtensions.cs` |
| Repository | `Infrastructure/Extensions/DatabaseExtension.cs` |
| Job | `WebJob/Extensions/HangfireExtension.cs` |

## Schema 命名

| Schema | 用途 |
|--------|------|
| `dbo` | 原生/預設資料表 |
| `{ModuleA}` | 模組 A 資料表 |
| `{ModuleB}` | 模組 B 資料表 |

---

## Domain Layer 範本

路徑：`MyApp.Domain/`

### Entity

```csharp
// Entities/Sales/Order.cs
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace MyApp.Domain.Entities.Sales;

[Table("Order", Schema = "Sales")]
public class Order
{
    [Key]
    [StringLength(10)]
    public string Id { get; set; } = null!;

    [StringLength(50)]
    public string? Name { get; set; }

    public DateTime CreatedAt { get; set; }
}
```

### Interface

```csharp
// Interfaces/IOrderRepository.cs
namespace MyApp.Domain.Interfaces;

public interface IOrderRepository
{
    Task<IEnumerable<Order>> GetAllAsync();
    Task<Order?> GetByIdAsync(string id);
    Task AddAsync(Order entity);
    Task UpdateAsync(Order entity);
}
```

---

## Application Layer 範本

路徑：`MyApp.Application/`

### Service Interface

```csharp
// Services/IOrderService.cs
namespace MyApp.Application.Services;

public interface IOrderService
{
    Task ProcessAsync(CancellationToken cancellationToken = default);
}
```

### Service Implementation

```csharp
// Services/OrderService.cs
using Microsoft.Extensions.Logging;
using MyApp.Domain.Interfaces;

namespace MyApp.Application.Services;

public class OrderService : IOrderService
{
    private readonly IOrderRepository _repository;
    private readonly ILogger<OrderService> _logger;

    public OrderService(IOrderRepository repository, ILogger<OrderService> logger)
    {
        _repository = repository;
        _logger = logger;
    }

    public async Task ProcessAsync(CancellationToken cancellationToken = default)
    {
        var data = await _repository.GetAllAsync();
        _logger.LogInformation("處理 {Count} 筆資料", data.Count());
    }
}
```

### DI 註冊

```csharp
// Extensions/ServiceExtensions.cs
services.AddScoped<IOrderService, OrderService>();
```

---

## Infrastructure Layer 範本

路徑：`MyApp.Infrastructure/`

### Repository (Dapper)

```csharp
// Persistence/Repositories/OrderRepository.cs
using Dapper;
using Microsoft.Data.SqlClient;
using Microsoft.Extensions.Configuration;
using MyApp.Domain.Entities.Sales;
using MyApp.Domain.Interfaces;

namespace MyApp.Infrastructure.Persistence.Repositories;

public class OrderRepository : IOrderRepository
{
    private readonly string _connectionString;

    public OrderRepository(IConfiguration configuration)
    {
        _connectionString = configuration.GetConnectionString("DefaultConnection")!;
    }

    public async Task<IEnumerable<Order>> GetAllAsync()
    {
        using var connection = new SqlConnection(_connectionString);
        return await connection.QueryAsync<Order>(
            "SELECT * FROM Sales.[Order]",
            commandTimeout: 300);
    }

    public async Task<Order?> GetByIdAsync(string id)
    {
        using var connection = new SqlConnection(_connectionString);
        return await connection.QueryFirstOrDefaultAsync<Order>(
            "SELECT * FROM Sales.[Order] WHERE Id = @Id",
            new { Id = id });
    }

    public async Task AddAsync(Order entity)
    {
        using var connection = new SqlConnection(_connectionString);
        await connection.ExecuteAsync(
            "INSERT INTO Sales.[Order] (Id, Name, CreatedAt) VALUES (@Id, @Name, @CreatedAt)",
            entity);
    }

    public async Task UpdateAsync(Order entity)
    {
        using var connection = new SqlConnection(_connectionString);
        await connection.ExecuteAsync(
            "UPDATE Sales.[Order] SET Name = @Name WHERE Id = @Id",
            entity);
    }
}
```

### EF Core Configuration

```csharp
// Persistence/Data/Configurations/OrderConfiguration.cs
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using MyApp.Domain.Entities.Sales;

namespace MyApp.Infrastructure.Persistence.Data.Configurations;

public class OrderConfiguration : IEntityTypeConfiguration<Order>
{
    public void Configure(EntityTypeBuilder<Order> builder)
    {
        builder.ToTable("Order", "Sales");
        builder.HasKey(e => e.Id);
        builder.Property(e => e.Id).HasMaxLength(10).IsUnicode(false);
        builder.Property(e => e.Name).HasMaxLength(50);
    }
}
```

### DI 註冊

```csharp
// Extensions/DatabaseExtension.cs
services.AddScoped<IOrderRepository, OrderRepository>();
```

---

## WebJob Layer 範本

路徑：`MyApp.WebJob/`（Hangfire Job 進入層；WebAPI 專案則改為 Controller）

```csharp
// Jobs/OrderJob.cs
using Hangfire;
using Hangfire.Server;
using MyApp.Application.Services;
using MyApp.WebJob.Attributes;

namespace MyApp.WebJob.Jobs;

[ManagementPage(MenuName = "Sales Job", Title = nameof(OrderJob))]
[HangfireLog]
public class OrderJob : IJob
{
    private readonly IOrderService _service;

    public OrderJob(IOrderService service) => _service = service;

    [DisplayName("01.訂單處理作業")]
    [Description("工作說明")]
    public async Task ExecuteAsync(PerformContext context, IJobCancellationToken token)
    {
        await _service.ProcessAsync();
    }
}
```

> Hangfire Job 的建立、排程與自動重排範本見 `hangfire-job` skill。

---

# 其他 .NET 慣例

## 慣例搜尋指令（寫新元件前先找樣板）

```bash
Grep "class .*Handler" --type cs           # 找同類 Handler 樣板
Grep "class .*Repository" --type cs        # 找同類 Repository 樣板
Grep "IEntityTypeConfiguration<" --type cs # 找同類 Entity Configuration 樣板
```

## 框架與資料存取紀律

- **EF Core Configuration**：位置跟隨專案既有（如 `Domain/Data/Configurations/`）；唯讀查詢預設 `AsNoTracking()`；投影查詢避免拉整列；`Include` 避免 N+1；Migration 檔不手改，對 SQL 形狀沒把握先看實際產出的查詢。
- **async**：async 一路 async 到底，不 `.Result`／`.Wait()`（死鎖風險）；DbContext 是 Scoped，別被 Singleton 持有；Nullable 開啟的專案不用 `!` 壓警告，處理真正的 null 流。
- **Pipeline Behavior 註冊**：`cfg.AddBehavior(typeof(IPipelineBehavior<,>), typeof(NewBehavior<,>));`，確認在既有 Behavior 順序中的位置（驗證 → 交易 → 日誌等）。
- **現代 C#（.NET 8+）**：file-scoped namespace、record type；`IDisposable` 正確實作。
- **N+1 與非同步最佳化範例**：

```csharp
// ❌ N+1
foreach (var e in entities)
    var cat = await ctx.Categories.FirstOrDefaultAsync(c => c.Id == e.CategoryId);

// ✅ Include / AsNoTracking / 投影
var entities = await ctx.Entities.Include(x => x.Category).AsNoTracking().ToListAsync();
var light    = await ctx.Entities.Select(x => new { x.Id, x.Name }).ToListAsync();

// ❌ 阻塞
var r = _repo.GetAsync(id).Result;
// ✅ async / 並行獨立操作
var r = await _repo.GetAsync(id);
await Task.WhenAll(_repo.GetAsync(id1), _repo.GetAsync(id2));
```

## 審查補充（reviewer 用）

- 架構：Domain 無外部依賴、Application 只依賴 Domain、Presentation 不直接依賴 Persistence。
- 資料存取：唯讀用 `AsNoTracking()`；Dapper 用強型別 DTO（非 `dynamic`）；SQL 清洗止於 SQL 層，Handler 不再 `.Trim()`；Entity → Response 走 Mapper Profile，不在 Handler 手寫逐欄位映射。
- CQRS：Query 不改狀態；Request 有 FluentValidation 驗證。
- 現代 .NET：Nullable 不用 `!` 壓警告；無 `.Result`／`.Wait()`；`IDisposable` 正確實作。
- API：Controller 繼承共用基底、HTTP 狀態碼正確、無業務邏輯在 Controller、有授權檢查。
- 測試：xUnit + Moq；注意「純測框架行為」的低價值案例（見 `unit-testing` 價值矩陣）。

## 測試與診斷指令

```bash
# 迭代期：鎖定新增／受影響範圍（預設一律帶 --filter）
dotnet test --filter "FullyQualifiedName~{TestClassName}" --logger:trx
# 最終回歸（commit 前／CI）
dotnet test
dotnet test --verbosity normal                 # 詳細輸出
dotnet test tests/{Project}.Application.Tests  # 指定測試專案
dotnet build                                   # 建置驗證
dotnet build --no-incremental                  # 診斷建置問題
dotnet format --verify-no-changes              # 格式檢查
dotnet list package --outdated                 # 過時套件
dotnet list package --vulnerable               # 安全弱點
```

TDD（Red-Green-Refactor）每個階段的驗證都是上面的 `--filter` 指令：Red 看到失敗（編譯失敗也算紅燈）、Green 與 Refactor 看到通過；最後 commit 前跑一次全 suite。Mock 呼叫驗證依專案採用的 mocking 框架語法（NSubstitute：`await mock.Received(1).MethodAsync(Arg.Any<string>())`；Moq：`mock.Verify(...)`）。

建置／測試常見模式：編譯錯誤（`CS8602` 缺 null 檢查、Nullable 警告、型別不符、缺泛型約束）；測試失敗（非同步時序、Mock 設定錯誤、DB 狀態、外部服務連線、背景工作失敗）；分析器警告（未使用變數／using、潛在記憶體洩漏、不安全型別轉換、同步阻塞非同步）。

除錯用的策略性日誌：

```csharp
_logger.LogDebug("開始處理請求 - Id: {Id}", request.Id);
_logger.LogDebug("查詢結果 - 找到 {Count} 筆", results.Count);
_logger.LogWarning("異常狀況 - 預期: {Expected}, 實際: {Actual}", expected, actual);
```

## 測試覆蓋率目標（參考）

| 層 | 目標 |
|----|------|
| Domain 邏輯 | 90%+ |
| Application 服務／Handler | 85%+ |
| Persistence Repository | 75%+ |
| Utilities／純函式 | 95%+ |

覆蓋率是參考不是教條，優先覆蓋高價值路徑。

## 分支安全

實作或提交前確認目前分支，禁止在 `main`／`develop` 上直接實作功能。

## 常見坑

- **Scoped 服務被 Singleton 持有**
  - 症狀：`Cannot consume scoped service from singleton`，或 DbContext 狀態殘留、資料過期。
  - 原因：DbContext／Repository 是 Scoped，註冊時生命週期用錯。
  - 修法：相依鏈統一 Scoped；Singleton 需要時改注入 `IServiceScopeFactory`。
- **`.Result`／`.Wait()` 阻塞非同步**
  - 症狀：請求卡死（死鎖）、執行緒耗盡。
  - 原因：同步等待 async 方法。
  - 修法：一路 `await`；入口改 async。
- **Presentation 直接依賴 Persistence／Infrastructure**
  - 症狀：換資料存取實作時 Controller 也要改；專案參照出現反向箭頭。
  - 原因：圖方便跳過 Application 層。
  - 修法：Controller 只送 MediatR 請求或呼叫 Application Service；用專案參照檢查依賴方向。
- **迭代期跑全 suite**
  - 症狀：每次驗證數分鐘。
  - 原因：沒帶 `--filter`。
  - 修法：迭代期鎖定新增／受影響測試，全 suite 僅 commit 前或 CI 跑一次。
- **手改 Migration 檔**
  - 症狀：snapshot 與實際 schema 不一致，下次 migration 產生多餘變更。
  - 原因：直接編輯已產生的 Migration。
  - 修法：改 Entity Configuration 後重新產生 Migration。
