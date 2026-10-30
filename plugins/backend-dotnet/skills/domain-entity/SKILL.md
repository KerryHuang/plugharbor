---
name: domain-entity
description: 生成 EF Core Domain Entity，含 Data Annotations、legacy 欄位名映射、資源檔驗證訊息、nullable 型別對照。Use when 建立新資料庫 Entity、定義 Domain Model、映射舊資料庫欄位、ef core entity、data annotation、entity mapping。
---

# EF Core Domain Entity 生成

## Instructions

1. 用 `[Keyless]` 或 `[Key]` 標記主鍵
2. 用 `[Column("LEGACY_COLUMN")]` 映射舊系統的欄位名稱（屬性名採 C# 慣例、欄位名保留舊命名）
3. 用 `[Display(Name = "中文名稱")]` 提供顯示名稱
4. 加驗證屬性：`Required`、`MinLength`、`MaxLength`、`Unicode`
5. 所有屬性加 XML 文件註解

> 範例以中性領域 `Order`（訂單）示範；驗證訊息透過共用資源類別 `SharedResources` 集中管理（沿用專案既有的 localization 資源即可）。

## Entity 範本

```csharp
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;
using Microsoft.EntityFrameworkCore;

namespace MyApp.Domain.Entities.{Module};

/// <summary>
/// {EntityDesc}
/// </summary>
[Keyless]
public partial class {Entity}
{
    /// <summary>
    /// {EntityDesc}ID
    /// </summary>
    [Display(Name = "{EntityDesc}ID")]
    [Required(ErrorMessageResourceName = "Validation_Required", ErrorMessageResourceType = typeof(Resources.SharedResources))]
    [MinLength(1, ErrorMessageResourceName = "Validation_MinLength", ErrorMessageResourceType = typeof(Resources.SharedResources))]
    [MaxLength(10, ErrorMessageResourceName = "Validation_MaxLength", ErrorMessageResourceType = typeof(Resources.SharedResources))]
    [Unicode(false)]
    [Column("ORDER_NO")]
    public string {Entity}Id { get; set; } = "";

    /// <summary>
    /// 名稱
    /// </summary>
    [Display(Name = "名稱")]
    [Required(ErrorMessageResourceName = "Validation_Required", ErrorMessageResourceType = typeof(Resources.SharedResources))]
    [MaxLength(60, ErrorMessageResourceName = "Validation_MaxLength", ErrorMessageResourceType = typeof(Resources.SharedResources))]
    [Unicode(false)]
    [Column("ORDER_NAME")]
    public string Name { get; set; } = "";

    /// <summary>
    /// 說明
    /// </summary>
    [Display(Name = "說明")]
    [MaxLength(200, ErrorMessageResourceName = "Validation_MaxLength", ErrorMessageResourceType = typeof(Resources.SharedResources))]
    public string? Description { get; set; }

    /// <summary>
    /// 建立日期
    /// </summary>
    [Display(Name = "建立日期")]
    [Column(TypeName = "datetime")]
    public DateTime? CreatedDate { get; set; }

    /// <summary>
    /// 更新日期
    /// </summary>
    [Display(Name = "更新日期")]
    [Column("UTIME", TypeName = "datetime")]
    public DateTime? LastModifiedTime { get; set; }

    /// <summary>
    /// 刪除標記
    /// </summary>
    [Display(Name = "刪除標記")]
    [Required(ErrorMessageResourceName = "Validation_Required", ErrorMessageResourceType = typeof(Resources.SharedResources))]
    [Column("DELETE_FLAG")]
    public bool DeleteFlag { get; set; }

    /// <summary>
    /// 時間戳（樂觀鎖）
    /// </summary>
    [Display(Name = "時間戳")]
    [Column("TIMESTAMP")]
    public byte[]? RecordTimestamp { get; set; }
}
```

## 常用資料類型對照

| C# 類型 | SQL Server | 屬性 |
|---------|------------|------|
| `string` | varchar/nvarchar | `[Unicode(false)]` for varchar |
| `int` | int | - |
| `decimal` | decimal | `[Column(TypeName = "decimal(18, 2)")]` |
| `DateTime?` | datetime | `[Column(TypeName = "datetime")]` |
| `bool` | bit | - |
| `byte[]?` | timestamp/rowversion | - |

## 驗證屬性範例

```csharp
// 必填字串
[Required(ErrorMessageResourceName = "Validation_Required", ErrorMessageResourceType = typeof(Resources.SharedResources))]
[MinLength(1, ErrorMessageResourceName = "Validation_MinLength", ErrorMessageResourceType = typeof(Resources.SharedResources))]
[MaxLength(10, ErrorMessageResourceName = "Validation_MaxLength", ErrorMessageResourceType = typeof(Resources.SharedResources))]
public string RequiredField { get; set; } = "";

// 選填字串
[MaxLength(100, ErrorMessageResourceName = "Validation_MaxLength", ErrorMessageResourceType = typeof(Resources.SharedResources))]
public string? OptionalField { get; set; }

// 數值欄位
[Column(TypeName = "decimal(18, 2)")]
public decimal? Amount { get; set; }

// 日期欄位
[Column(TypeName = "datetime")]
public DateTime? EventDate { get; set; }
```

## 關聯欄位命名規則

```csharp
// 外鍵 ID（映射 legacy 欄位名）
[Display(Name = "客戶ID")]
[MaxLength(15, ErrorMessageResourceName = "Validation_MaxLength", ErrorMessageResourceType = typeof(Resources.SharedResources))]
[Unicode(false)]
[Column("CUST_NO")]
public string CustomerId { get; set; } = "";

// 關聯名稱（從其他表帶入，非本表欄位）
/// <summary>
/// 客戶名稱 [Sales].[Customer].[CustomerName]
/// </summary>
[Display(Name = "客戶名稱")]
[MaxLength(15, ErrorMessageResourceName = "Validation_MaxLength", ErrorMessageResourceType = typeof(Resources.SharedResources))]
public string? CustomerName { get; set; }
```

## 目錄結構

```
Domain/Entities/
├── {ModuleA}/        # 模組 A 實體
├── {ModuleB}/        # 模組 B 實體
├── {ModuleC}/        # 模組 C 實體
└── dbo/              # 舊系統原生資料表（保留 legacy 命名）
```

## 擴充表（Ext / Satellite）欄位新增

當**舊系統主表不可新增欄位**（避免影響 legacy 程式或跨系統相依）時，新欄位改放對應的擴充表（如 `OrderExt`、`ProductExt`），與主表以 1:1 主鍵相對。

### 若新欄位需同時被主表 DTO 接收（API binding）

1. **Entity 加欄位 + EF Configuration**：Ext 表 entity + `Configurations/{Entity}ExtConfiguration.cs`
2. **主表 DTO 加 property（不加 `[Column]`）**：以 SqlGenerator 自動跳過無 `[Column]` 的屬性為前提；由 Handler 路由決定寫入哪張表
3. **Handler 注入 `I{Entity}ExtRepository`**：**禁止**在 Handler 內直接注入 `DbContext` 操作 Ext 表
4. **評估副作用**：若欄位切換會觸發其他 entity 建立、重算等副作用 → 建立**專屬 Handler + 獨立 endpoint**（如 `PUT /Order/{id}/flag`），不塞進 Create/Update 主流程
5. **AutoMapper 保護**：`CreateMap<View, 主表 DTO>` 對 Ext 欄位加 `.ForMember(d => d.{欄位}, opt => opt.Ignore())`，防止 system-driven Sync handler 誤 propagate
6. **測試覆蓋**：
   - Handler routing 分支（field `HasValue` / `null`）
   - AutoMapper `AssertConfigurationIsValid` 通過
   - Regression：對 Ext 欄位已設值的資料呼叫主表 update 不爆 SQL
