# 單元測試 .NET 附錄（xUnit + Moq）

> 給 `unit-testing` skill 的 .NET 寫法。完整測試範本見 [dotnet-templates.md](dotnet-templates.md)（Command / Query / Update / Delete / Validator / Paged Query / GlobalUsings / InMemory 基底）。共用指令與覆蓋率目標見 `${CLAUDE_PLUGIN_ROOT}/references/stacks/dotnet.md`。

## 工具與慣例

1. 測試框架用 **xUnit** + **Moq**（mock 依賴）；斷言可用內建 `Assert` 或 FluentAssertions（跟隨專案既有選擇）
2. 遵循 AAA 模式（Arrange-Act-Assert）
3. 測試類別命名：`{Handler/Validator/Repository}Tests.cs`
4. 測試方法命名：`{Method}_{Scenario}_{ExpectedResult}`（英文）
5. **建議**為每個 `[Fact]` 加 `[Fact(DisplayName = "繁中描述")]`（跟隨團隊慣例）；多參數案例用 `[Theory] + [InlineData]`
6. 測試放在專案測試目錄的對應 `{Commands|Queries}/` 下

## 分支類型對照表

| 分支類型 | 方法名 | DisplayName |
|---------|--------|-------------|
| 正常路徑 | `Handle_ValidRequest_ReturnsSuccess` | `操作_有效請求_回傳成功` |
| 找不到 | `Handle_EntityNotFound_ReturnsNotFound` | `操作_不存在_回傳未找到` |
| 已刪除 | `Handle_EntityDeleted_ReturnsFailure` | `操作_已刪除_回傳失敗` |
| 驗證失敗 | `Validate_EmptyField_ShouldFail` | `驗證_欄位為空_驗證失敗` |
| 業務規則 | `Handle_Condition_Behavior` | `操作_情境_預期結果` |
| 副作用 | `Handle_Success_CallsCommit` | `操作_成功後應呼叫Commit` |

## 測試模式（Mock 重點）

| 測試類型 | Mock 重點 | 驗證重點 |
|---------|----------|---------|
| Command Handler | `IUnitOfWork`、`IRepository` | `AddAsync`／`CommitAsync` 呼叫、副作用 |
| Query Handler | `IQueryRepository`、`I{Entity}Repository` | 回傳值正確性、null 處理 |
| Controller | `IMediator` | HTTP 狀態碼（`OkObjectResult` 等） |
| Validator | 無（直接 new） | `IsValid`、`Errors` 集合 |
| Repository | `AppDbContext`（InMemory）或真實 DB | CRUD 結果、SQL 轉譯 |

## 指令

```bash
# 迭代期：鎖定新增／受影響範圍
dotnet test --filter "FullyQualifiedName~{TestClassName}" --logger:trx

# 最終回歸（commit 前／CI）
dotnet test
```

複審剪枝列本次動過的測試檔：

```bash
git diff --name-only HEAD -- '**/*Tests.cs'
```

## 需要真實 DB 的情境（.NET／EF Core）

| 測試對象 | Mock (Moq) | InMemory DB | 真實 DB |
|---------|------------|-------------|---------|
| Repository CRUD | - | 可接受 | **首選**（驗 SQL 轉譯） |
| EF Core Configuration（FK／索引／約束） | - | **禁止**（不驗約束） | **必須** |
| 原生 SQL／Dapper 查詢 | - | **禁止** | **必須** |
| DB 引擎特定行為（CTE、定序截斷、字元補齊、分頁語法） | - | **禁止** | **必須** |

## 常見坑

- **用 InMemory provider 測 EF Core Configuration 或原生 SQL**
  - 症狀：測試全綠，上線後 FK 違反、SQL 語法錯誤。
  - 原因：InMemory 不驗約束，也不執行 SQL。
  - 修法：這類測試改用真實 DB 做整合測試。
- **Moq 沒設定非同步方法回傳值**
  - 症狀：`NullReferenceException`，堆疊指向被 mock 的 `await`。
  - 原因：未 `Setup(...).ReturnsAsync(...)`，預設回 null Task。
  - 修法：每個被呼叫的非同步依賴都設定 `ReturnsAsync`。
- **`Verify` 驗到實作細節而非行為**
  - 症狀：重構內部呼叫順序測試就紅。
  - 原因：過度驗證 mock 的呼叫次數與順序。
  - 修法：只驗證有業務意義的副作用（如 `CommitAsync` 被呼叫）。
- **迭代期跑全 suite**
  - 症狀：每次驗證數分鐘。
  - 原因：沒帶 `--filter`。
  - 修法：用 `FullyQualifiedName~` 鎖範圍，全 suite 僅最終回歸跑。
