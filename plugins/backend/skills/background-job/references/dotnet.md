# 背景作業 .NET 附錄（Hangfire）

> 給 `background-job` skill 的 .NET 寫法：Job 類別、DI 註冊、Cron 排程、自動重排。



> 範例以中性領域 `Order`（訂單）示範。`IJob`、`[ManagementPage]`、`[HangfireLog]` 為專案自訂的介面/屬性（可選）；沒有時直接用純類別 + `[DisplayName]`/`[Description]` 即可。

## Job 類別範本

```csharp
using Hangfire;
using Hangfire.Console;
using Hangfire.Server;
using MyApp.Application.Services;
using MyApp.WebJob.Attributes;

namespace MyApp.WebJob.Jobs;

[ManagementPage(MenuName = "Sales Job", Title = nameof(OrderJob))]
[HangfireLog]
public class OrderJob : IJob
{
    private readonly IOrderService _service;
    private readonly ILogger<OrderJob> _logger;

    public OrderJob(IOrderService service, ILogger<OrderJob> logger)
    {
        _service = service;
        _logger = logger;
    }

    [DisplayName("01.訂單處理作業")]
    [Description("工作說明")]
    public async Task ExecuteAsync(PerformContext context, IJobCancellationToken token)
    {
        context.WriteLine("開始執行...");

        await _service.ProcessAsync(context);

        context.WriteLine("執行完成");
    }
}
```

## DI 註冊

在 `HangfireExtension.cs` 註冊：

```csharp
services.AddScoped<OrderJob>();
```

## 排程設定

```csharp
// 每分鐘執行
RecurringJob.AddOrUpdate<OrderJob>(
    "order-job",
    job => job.ExecuteAsync(null!, JobCancellationToken.Null),
    "* * * * *");

// 每小時執行
RecurringJob.AddOrUpdate<OrderJob>(
    "order-job",
    job => job.ExecuteAsync(null!, JobCancellationToken.Null),
    "0 * * * *");

// 每日凌晨執行
RecurringJob.AddOrUpdate<OrderJob>(
    "order-job",
    job => job.ExecuteAsync(null!, JobCancellationToken.Null),
    "0 0 * * *");
```

## 自動重新排程模式

執行完成後動態註冊下次執行（適合間隔不固定或需依結果決定下次時間的作業）：

```csharp
public async Task ExecuteAsync(PerformContext context, IJobCancellationToken token)
{
    try
    {
        await _service.ProcessAsync(context);
    }
    finally
    {
        // 1 分鐘後再次執行
        _backgroundJobClient.Schedule<OrderJob>(
            job => job.ExecuteAsync(null!, JobCancellationToken.Null),
            TimeSpan.FromMinutes(1));
    }
}
```

## MenuName 分類（管理頁面分組，可選）

| MenuName | 用途 |
|----------|------|
| Sales Job | 銷售相關作業 |
| Sync Job | 資料同步處理 |
| Maintenance Job | 維護作業 |

## 常見坑

- **Singleton 持有 Scoped 服務**
  - 症狀：Job 執行時 `Cannot consume scoped service from singleton`，或 DbContext 狀態殘留。
  - 原因：Job 類別以錯誤生命週期註冊。
  - 修法：Job 與其相依一律 `AddScoped`，註冊在 `HangfireExtension.cs`。
- **自動重排放在會 throw 的路徑外**
  - 症狀：一次失敗後排程永遠停止；或 `finally` 重排造成錯誤時狂跑。
  - 原因：重排邏輯與錯誤處理未區分。
  - 修法：決定「失敗是否仍重排」並寫明；失敗重排要加延遲，不要立即重排。
- **recurring job id 重複**
  - 症狀：兩個 Job 只剩一個在跑。
  - 原因：`AddOrUpdate` 以 id 覆蓋。
  - 修法：每個 Job 用唯一 id（如 `order-job`）。
- **`PerformContext` 傳 null 以外的值**
  - 症狀：排程註冊的 expression 序列化失敗。
  - 原因：註冊時傳了實際物件。
  - 修法：註冊時一律 `null!` 與 `JobCancellationToken.Null`，執行時由 Hangfire 注入。
