# 測試範本參考

> 以下範本以 `{Entity}`（實體名）、`{Module}`（模組名）為佔位符，套用時替換為實際名稱。
> namespace `MyApp.*` 為示意，請對齊專案實際命名。

## Command Handler 測試範本

```csharp
using MyApp.Application.{Module}.{Entity}Service.Commands;
using MyApp.Domain.Repositories.{Module};

namespace MyApp.Application.Tests.{Module}.{Entity}Service.Commands;

public class Create{Entity}HandlerTests
{
    private readonly Mock<I{Entity}Repository> _{entity}RepositoryMock;
    private readonly Mock<IUnitOfWork> _unitOfWorkMock;
    private readonly Create{Entity}Handler _handler;

    public Create{Entity}HandlerTests()
    {
        _{entity}RepositoryMock = new Mock<I{Entity}Repository>();
        _unitOfWorkMock = new Mock<IUnitOfWork>();

        _handler = new Create{Entity}Handler(
            _{entity}RepositoryMock.Object,
            _unitOfWorkMock.Object);
    }

    [Fact(DisplayName = "建立{Entity}_有效請求_回傳成功")]
    public async Task Handle_ValidRequest_ReturnsSuccessResult()
    {
        // Arrange
        _{entity}RepositoryMock.Setup(r => r.GenerateIdAsync(It.IsAny<CancellationToken>()))
            .ReturnsAsync("0000000001");

        var command = new Create{Entity}Command(new Create{Entity}Request
        {
            Name = "範例名稱",
            Date = DateTime.Today
        });

        // Act
        var result = await _handler.Handle(command, CancellationToken.None);

        // Assert
        Assert.True(result.IsSuccess);
        Assert.NotNull(result.Data);
        _unitOfWorkMock.Verify(u => u.CommitAsync(It.IsAny<CancellationToken>()), Times.Once);
    }

    [Fact(DisplayName = "建立{Entity}_例外發生_回傳失敗")]
    public async Task Handle_RepositoryThrowsException_ReturnsFailureResult()
    {
        // Arrange
        var expectedException = new Exception("Database error");
        _{entity}RepositoryMock.Setup(r => r.CreateAsync(It.IsAny<{Entity}>()))
            .ThrowsAsync(expectedException);

        var command = new Create{Entity}Command(new Create{Entity}Request { Name = "範例名稱" });

        // Act
        var result = await _handler.Handle(command, CancellationToken.None);

        // Assert
        Assert.False(result.IsSuccess);
        _unitOfWorkMock.Verify(u => u.CommitAsync(It.IsAny<CancellationToken>()), Times.Never);
    }
}
```

## Query Handler 測試範本

```csharp
public class Get{Entity}HandlerTests
{
    private readonly Mock<I{Entity}Repository> _{entity}RepositoryMock;
    private readonly Get{Entity}Handler _handler;

    public Get{Entity}HandlerTests()
    {
        _{entity}RepositoryMock = new Mock<I{Entity}Repository>();
        _handler = new Get{Entity}Handler(_{entity}RepositoryMock.Object);
    }

    [Fact(DisplayName = "查詢{Entity}_存在_回傳成功含資料")]
    public async Task Handle_Exists_ReturnsSuccessWithData()
    {
        // Arrange
        var entity = new {Entity} { {Entity}Id = "0000000001", DelMark = "" };
        _{entity}RepositoryMock.Setup(r => r.GetAsync("0000000001", It.IsAny<CancellationToken>()))
            .ReturnsAsync(entity);

        // Act
        var result = await _handler.Handle(new Get{Entity}Query("0000000001"), CancellationToken.None);

        // Assert
        Assert.True(result.IsSuccess);
        Assert.NotNull(result.Data);
    }

    [Fact(DisplayName = "查詢{Entity}_不存在_回傳未找到")]
    public async Task Handle_NotFound_ReturnsNotFound()
    {
        // Arrange
        _{entity}RepositoryMock.Setup(r => r.GetAsync("9999999999", It.IsAny<CancellationToken>()))
            .ReturnsAsync(({Entity}?)null);

        // Act
        var result = await _handler.Handle(new Get{Entity}Query("9999999999"), CancellationToken.None);

        // Assert
        Assert.False(result.IsSuccess);
        Assert.Contains("找不到", result.Message);
    }
}
```

## Update Handler 測試範本

```csharp
public class Update{Entity}HandlerTests
{
    private readonly Mock<I{Entity}Repository> _{entity}RepositoryMock;
    private readonly Mock<IUnitOfWork> _unitOfWorkMock;
    private readonly Update{Entity}Handler _handler;

    public Update{Entity}HandlerTests()
    {
        _{entity}RepositoryMock = new Mock<I{Entity}Repository>();
        _unitOfWorkMock = new Mock<IUnitOfWork>();
        _handler = new Update{Entity}Handler(_{entity}RepositoryMock.Object, _unitOfWorkMock.Object);
    }

    [Fact(DisplayName = "更新{Entity}_有效請求_回傳成功")]
    public async Task Handle_ValidRequest_ReturnsSuccess()
    {
        // Arrange
        var entity = new {Entity} { {Entity}Id = "0000000001", DelMark = "" };
        _{entity}RepositoryMock.Setup(r => r.GetAsync("0000000001", It.IsAny<CancellationToken>()))
            .ReturnsAsync(entity);

        var command = new Update{Entity}Command("0000000001", new Update{Entity}Request { Remark = "測試備註" });

        // Act
        var result = await _handler.Handle(command, CancellationToken.None);

        // Assert
        Assert.True(result.IsSuccess);
    }

    [Fact(DisplayName = "更新{Entity}_已刪除_回傳失敗")]
    public async Task Handle_Deleted_ReturnsFailure()
    {
        // Arrange
        var entity = new {Entity} { {Entity}Id = "0000000001", DelMark = "Y" };
        _{entity}RepositoryMock.Setup(r => r.GetAsync("0000000001", It.IsAny<CancellationToken>()))
            .ReturnsAsync(entity);

        var command = new Update{Entity}Command("0000000001", new Update{Entity}Request());

        // Act
        var result = await _handler.Handle(command, CancellationToken.None);

        // Assert
        Assert.False(result.IsSuccess);
        Assert.Contains("已刪除", result.Message);
    }
}
```

## Delete Handler 測試範本（軟刪除）

```csharp
public class Delete{Entity}HandlerTests
{
    private readonly Mock<I{Entity}Repository> _{entity}RepositoryMock;
    private readonly Mock<IUnitOfWork> _unitOfWorkMock;
    private readonly Delete{Entity}Handler _handler;

    public Delete{Entity}HandlerTests()
    {
        _{entity}RepositoryMock = new Mock<I{Entity}Repository>();
        _unitOfWorkMock = new Mock<IUnitOfWork>();
        _handler = new Delete{Entity}Handler(_{entity}RepositoryMock.Object, _unitOfWorkMock.Object);
    }

    [Fact(DisplayName = "刪除{Entity}_有效請求_回傳成功")]
    public async Task Handle_ValidRequest_ReturnsSuccess()
    {
        // Arrange
        _{entity}RepositoryMock.Setup(r => r.GetAsync("0000000001", It.IsAny<CancellationToken>()))
            .ReturnsAsync(new {Entity} { {Entity}Id = "0000000001", DelMark = "" });

        // Act
        var result = await _handler.Handle(new Delete{Entity}Command("0000000001"), CancellationToken.None);

        // Assert
        Assert.True(result.IsSuccess);
    }

    [Fact(DisplayName = "刪除{Entity}_成功後DelMark設為Y")]
    public async Task Handle_Success_SetsDelMarkToY()
    {
        // Arrange
        var entity = new {Entity} { {Entity}Id = "0000000001", DelMark = "" };
        _{entity}RepositoryMock.Setup(r => r.GetAsync("0000000001", It.IsAny<CancellationToken>()))
            .ReturnsAsync(entity);

        // Act
        await _handler.Handle(new Delete{Entity}Command("0000000001"), CancellationToken.None);

        // Assert
        Assert.Equal("Y", entity.DelMark);
    }
}
```

## Validator 測試範本（FluentValidation）

```csharp
using FluentValidation.TestHelper;

public class Create{Entity}RequestValidatorTests
{
    private readonly Create{Entity}RequestValidator _validator = new();

    // 基礎有效請求（用 record with 語法建立變體）
    private static readonly Create{Entity}Request _validRequest = new()
    {
        {Entity}Id = "0000000001",
        Name = "範例名稱",
        Date = DateTime.Today
    };

    [Fact(DisplayName = "驗證_有效請求_驗證通過")]
    public void Validate_ValidRequest_ShouldPass()
    {
        var result = _validator.TestValidate(_validRequest);
        result.ShouldNotHaveAnyValidationErrors();
    }

    [Fact(DisplayName = "驗證_必填欄位為空_驗證失敗")]
    public void Validate_EmptyRequiredField_ShouldFail()
    {
        var request = _validRequest with { {Entity}Id = "" };
        var result = _validator.TestValidate(request);
        result.ShouldHaveValidationErrorFor(x => x.{Entity}Id);
    }

    [Fact(DisplayName = "驗證_數值超出範圍_驗證失敗")]
    public void Validate_ValueOutOfRange_ShouldFail()
    {
        var request = _validRequest with { Rate = -1m };
        var result = _validator.TestValidate(request);
        result.ShouldHaveValidationErrorFor(x => x.Rate);
    }
}
```

## Paged Query 測試範本

```csharp
public class GetPaged{Entity}HandlerTests
{
    private readonly Mock<IMapper> _mapperMock;
    private readonly Mock<I{Entity}Repository> _{entity}RepositoryMock;
    private readonly GetPaged{Entity}Handler _handler;

    public GetPaged{Entity}HandlerTests()
    {
        _mapperMock = new Mock<IMapper>();
        _{entity}RepositoryMock = new Mock<I{Entity}Repository>();
        _handler = new GetPaged{Entity}Handler(_mapperMock.Object, _{entity}RepositoryMock.Object);
    }

    [Fact(DisplayName = "分頁查詢{Entity}_有效請求_回傳分頁結果")]
    public async Task Handle_ValidRequest_ReturnsPagedResponse()
    {
        // Arrange
        var request = new GetPaged{Entity}Request { CurrentPage = 1, PageSize = 10 };

        var pagedResult = new PagedResponse<{Entity}>(2, 1, 10)
        {
            Items = new List<{Entity}>
            {
                new() { {Entity}Id = "0000000001", Name = "項目一" },
                new() { {Entity}Id = "0000000002", Name = "項目二" }
            }
        };

        var expectedResponse = new PagedResponse<Get{Entity}Response>(2, 1, 10)
        {
            Items = new List<Get{Entity}Response>
            {
                new() { {Entity}Id = "0000000001", Name = "項目一" },
                new() { {Entity}Id = "0000000002", Name = "項目二" }
            }
        };

        _{entity}RepositoryMock.Setup(repo => repo.GetPagedAsync(
                It.IsAny<string>(), It.IsAny<Dictionary<string, object>>(),
                request.CurrentPage, request.PageSize))
            .ReturnsAsync(pagedResult);
        _mapperMock.Setup(m => m.Map<PagedResponse<Get{Entity}Response>>(pagedResult))
            .Returns(expectedResponse);

        // Act
        var result = await _handler.Handle(request, CancellationToken.None);

        // Assert
        Assert.NotNull(result);
        Assert.Equal(2, result.TotalCount);
        Assert.Equal(2, result.Items.Count);
    }
}
```

## GlobalUsings.cs 範本

```csharp
global using AutoMapper;
global using Microsoft.EntityFrameworkCore;
global using Microsoft.Extensions.Logging;
global using Moq;
global using System.Linq.Expressions;
global using Xunit;
```

## 測試基底類別（InMemory Database）

特定場景需要 InMemory Database 時使用此基底類別（注意：InMemory provider 不驗證 DB 約束，涉及約束/原生 SQL 請改用真實 DB 整合測試）。

```csharp
using Microsoft.EntityFrameworkCore;

public abstract class SimpleTestBase : IDisposable
{
    protected readonly AppDbContext Context;

    protected SimpleTestBase()
    {
        var options = new DbContextOptionsBuilder<AppDbContext>()
            .UseInMemoryDatabase(databaseName: Guid.NewGuid().ToString())
            .Options;

        Context = new AppDbContext(options);
    }

    public virtual void Dispose()
    {
        Context.Dispose();
        GC.SuppressFinalize(this);
    }
}
```
