---
name: hangfire-job
description: Hangfire 背景作業開發，含 Job 類別建立、DI 註冊、Cron 排程、自動重排範本。Use when 建立新的 Hangfire Job、設定背景排程、需要 Job 開發範本、hangfire job、recurring job、background job、排程作業。
---

# Hangfire Job 開發

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
