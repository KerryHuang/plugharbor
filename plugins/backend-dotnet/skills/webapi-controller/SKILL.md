---
name: webapi-controller
description: 生成 ASP.NET Core WebAPI Controller，含完整 CRUD 端點（GetAll、GetById、GetPaged、Create、Update、Delete）與 API 版本控制。Use when 建立新 API Controller、新增 REST 端點、實作 API versioning、webapi controller、crud controller。
---

# WebAPI Controller 生成

## Instructions

1. 繼承共用基底（如 `APIControllerBase`）以取得 `[Authorize]`、`TraceId` 等共通行為
2. 用 `[Area(ModuleStructure.{Module})]` 設定模組區域
3. 設定 API 版本（如 `[ApiVersion("3.0")]`）
4. 透過 MediatR 發送請求
5. 所有方法標註 `ProducesResponseType`

> 範例以中性領域 `Order`（訂單）示範，實作時替換為實際 Entity 名。

## Controller 範本

```csharp
using MyApp.Domain.Contracts;
using MyApp.Persistence.Models;

namespace MyApp.WebAPI.Controllers.v3.{Module};

/// <summary>
/// {EntityDesc}控制器，處理與{EntityDesc}相關的 API 請求
/// </summary>
[Area(ModuleStructure.{Module})]
[ApiVersion("3.0")]
[Route("api/v{version:apiVersion}/[area]/[controller]")]
[Produces("application/json")]
[ApiController]
public class {Entity}Controller : APIControllerBase
{
    private readonly IMediator _mediator;
    private readonly IMapper _mapper;

    /// <summary>
    /// 初始化 <see cref="{Entity}Controller"/> 類別的新執行個體
    /// </summary>
    public {Entity}Controller(IMediator mediator, IMapper mapper)
    {
        _mediator = mediator;
        _mapper = mapper;
    }

    /// <summary>
    /// 取得所有{EntityDesc}
    /// </summary>
    [HttpGet]
    [ProducesResponseType(typeof(List<Get{Entity}Response>), StatusCodes.Status200OK)]
    [ProducesResponseType(typeof(ExceptionResponseModel), StatusCodes.Status500InternalServerError)]
    public async Task<IActionResult> GetAll([FromQuery] GetFilter{Entity}Request request, CancellationToken cancellationToken)
    {
        var result = await _mediator.Send(request, cancellationToken);
        return Ok(result);
    }

    /// <summary>
    /// 取得單一{EntityDesc}
    /// </summary>
    [HttpGet("{id}")]
    [ProducesResponseType(typeof(Get{Entity}Response), StatusCodes.Status200OK)]
    [ProducesResponseType(typeof(NotFoundResponseModel), StatusCodes.Status404NotFound)]
    [ProducesResponseType(typeof(ExceptionResponseModel), StatusCodes.Status500InternalServerError)]
    public async Task<IActionResult> Get(string id, CancellationToken cancellationToken)
    {
        var request = new Get{Entity}Request { {Entity}Id = id };
        var result = await _mediator.Send(request, cancellationToken);
        return result != null ? Ok(result) : NotFound();
    }

    /// <summary>
    /// 取得分頁{EntityDesc}
    /// </summary>
    [HttpGet("paged")]
    [ProducesResponseType(typeof(IPagedResponse<Get{Entity}Response>), StatusCodes.Status200OK)]
    [ProducesResponseType(typeof(ExceptionResponseModel), StatusCodes.Status500InternalServerError)]
    public async Task<IActionResult> GetPaged([FromQuery] GetPaged{Entity}Request request, CancellationToken cancellationToken)
    {
        var result = await _mediator.Send(request, cancellationToken);
        return Ok(result);
    }

    /// <summary>
    /// 建立{EntityDesc}
    /// </summary>
    [HttpPost]
    [ProducesResponseType(typeof(Get{Entity}Response), StatusCodes.Status201Created)]
    [ProducesResponseType(typeof(ValidationResponseModel), StatusCodes.Status400BadRequest)]
    [ProducesResponseType(typeof(ExceptionResponseModel), StatusCodes.Status500InternalServerError)]
    public async Task<IActionResult> Create([FromBody] Create{Entity}Request request, CancellationToken cancellationToken)
    {
        var creationResult = await _mediator.Send(request, cancellationToken);
        if (creationResult.IsSuccess)
        {
            var getResult = await _mediator.Send(new Get{Entity}Request { {Entity}Id = creationResult.Data ?? "" }, cancellationToken);
            return CreatedAtAction(nameof(Get), new { id = request.{Entity}Id }, getResult);
        }
        return BadRequest(new BadResponseModel(traceId: TraceId) { Message = $"{SharedResources.CreateFailed}{(!string.IsNullOrEmpty(creationResult.Message) ? $", {creationResult.Message}" : "")}" });
    }

    /// <summary>
    /// 更新{EntityDesc}
    /// </summary>
    [HttpPut("{id}")]
    [ProducesResponseType(typeof(Get{Entity}Response), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    [ProducesResponseType(typeof(ValidationResponseModel), StatusCodes.Status400BadRequest)]
    [ProducesResponseType(typeof(NotFoundResponseModel), StatusCodes.Status404NotFound)]
    [ProducesResponseType(typeof(ExceptionResponseModel), StatusCodes.Status500InternalServerError)]
    public async Task<IActionResult> Update(string id, [FromBody] Update{Entity}Request request, CancellationToken cancellationToken)
    {
        if (id != request.{Entity}Id)
        {
            return BadRequest(new BadResponseModel(traceId: TraceId) { Message = "Id mismatch" });
        }

        var result = await _mediator.Send(request, cancellationToken);
        if (!result.IsSuccess)
        {
            return BadRequest(new BadResponseModel(traceId: TraceId) { Message = SharedResources.UpdateFailed + (!string.IsNullOrEmpty(result.Message) ? ", " + result.Message : "") });
        }

        var getRequest = new Get{Entity}Request { {Entity}Id = id };
        var getResult = await _mediator.Send(getRequest, cancellationToken);
        return getResult != null ? Ok(getResult) : NotFound();
    }

    /// <summary>
    /// 刪除{EntityDesc}
    /// </summary>
    [HttpDelete("{id}")]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    [ProducesResponseType(typeof(NotFoundResponseModel), StatusCodes.Status404NotFound)]
    [ProducesResponseType(typeof(ExceptionResponseModel), StatusCodes.Status500InternalServerError)]
    public async Task<IActionResult> Delete(string id, CancellationToken cancellationToken)
    {
        var request = new Delete{Entity}Request { {Entity}Id = id };
        var result = await _mediator.Send(request, cancellationToken);
        return result.IsSuccess ? NoContent() : NotFound(new NotFoundResponseModel(traceId: TraceId) { Message = SharedResources.DeleteFailed + (!string.IsNullOrEmpty(result.Message) ? ", " + result.Message : "") });
    }

    /// <summary>
    /// 取得輕量{EntityDesc}
    /// </summary>
    [HttpGet("light")]
    [ProducesResponseType(typeof(List<GetLight{Entity}Response>), StatusCodes.Status200OK)]
    [ProducesResponseType(typeof(ExceptionResponseModel), StatusCodes.Status500InternalServerError)]
    public async Task<IActionResult> GetLightAll([FromQuery] GetFilter{Entity}Request request, CancellationToken cancellationToken)
    {
        var result = await _mediator.Send(request, cancellationToken);
        var response = _mapper.Map<List<GetLight{Entity}Response>>(result);
        return Ok(response);
    }
}
```

## 標準端點對照

| HTTP Method | 端點 | 用途 | 回應類型 |
|-------------|------|------|----------|
| GET | `/` | 取得所有（篩選） | `List<Response>` |
| GET | `/{id}` | 取得單一 | `Response` |
| GET | `/paged` | 取得分頁 | `IPagedResponse` |
| GET | `/light` | 取得輕量全部 | `List<LightResponse>` |
| GET | `/light/{id}` | 取得輕量單一 | `LightResponse` |
| GET | `/light/paged` | 取得輕量分頁 | `IPagedResponse<LightResponse>` |
| POST | `/` | 建立 | `Response` (201) |
| PUT | `/{id}` | 更新 | `Response` |
| DELETE | `/{id}` | 刪除 | NoContent (204) |

## 路由格式

```
api/v{version:apiVersion}/[Area]/[Controller]
```

範例：`api/v1.0/Sales/Order`

## 回應模型

- `BadResponseModel` — 400 Bad Request
- `NotFoundResponseModel` — 404 Not Found
- `ValidationResponseModel` — 400 Validation Error
- `ExceptionResponseModel` — 500 Internal Server Error

## Controller 回應模式

| 動作 | 成功 | 失敗 |
|------|------|------|
| GET /{id} | `Ok(result)` | `NotFound()` |
| GET /Paged | `Ok(result)` | — |
| POST | `CreatedAtAction(nameof(Get), new { id }, re-fetched)` | `BadRequest(new BadResponseModel(TraceId))` |
| PUT | `Ok(re-fetched)` | `BadRequest(new BadResponseModel(TraceId))` |
| DELETE | `NoContent()` | `NotFound(new NotFoundResponseModel(TraceId))` |

POST / PUT 成功後**必須 re-fetch**（再送一次 `GetXxxRequest`）回傳最新完整資料。
**禁止**回傳 raw `ServiceResult` 給前端。

## 分頁參數（繼承 PagedRequest）

| 屬性 | 型別 | 說明 |
|------|------|------|
| `CurrentPage` | int | 頁碼（**非** PageNumber） |
| `PagesSize` | int | 每頁筆數（**非** PageSize） |
| `SortBy` | string[]? | 排序欄位 |
| `SortOrder` | string[]? | 排序方向 |

Response（`IPagedResponse<T>`）欄位：`Items`（**非** Data）、`TotalCount`、`CurrentPage`、`PagesSize`、`TotalPages`

> 上述屬性名（`CurrentPage`/`PagesSize`/`Items`）為範例約定；沿用專案既有 `PagedRequest`/`IPagedResponse` 契約即可，重點是前後端命名一致。

## Request DataAnnotation

**Create Request：**
```csharp
[Key][JsonIgnore] public Guid Id { get; set; } = Guid.NewGuid();   // 伺服端產生
[Display(Name = "欄位名")][Required][MaxLength(N)] public string Field { get; set; }
[JsonIgnore] public DateTime CreatedTime { get; set; } = DateTime.Now;
[JsonIgnore] public DateTime LastModifiedTime { get; set; } = DateTime.Now;
```

**Update Request：**
```csharp
[Key][Required] public string Id { get; set; }                      // 來自路由
[Display(Name = "欄位名")][Required][MaxLength(N)] public string Field { get; set; }
[JsonIgnore] public DateTime LastModifiedTime { get; set; } = DateTime.Now;
```

`[JsonIgnore]` 用於伺服端自產的欄位：Id（Create）、CreatedTime、LastModifiedTime 等。
