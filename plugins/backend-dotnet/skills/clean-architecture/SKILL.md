---
name: clean-architecture
description: Clean Architecture 四層（Domain / Application / Infrastructure / WebJob）分層開發，含各層檔案建立、依賴規則與程式碼範本。Use when 新增功能、建立實體、定義介面、實作服務/Repository、遵循分層架構規範、clean architecture、layered architecture、分層開發。
---

# Clean Architecture 分層開發

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
