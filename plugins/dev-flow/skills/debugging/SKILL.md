---
name: debugging
description: TDD 系統性除錯——先寫失敗測試重現 bug，追根因、修復、驗證無回歸。Use when 遇到 bug、測試失敗、或非預期行為需要追蹤根因, "除錯", "debug", "重現 bug", "測試失敗", "找根因", "systematic debugging".
---

# 系統性除錯

採 TDD 方式系統性除錯：先用測試重現問題，再改碼，最後用同一測試驗證修復。**沒有可重現的失敗測試就不動手改碼。**

## 除錯流程

### 1. 問題定義

收集資訊：錯誤訊息或非預期行為、重現步驟、預期行為 vs 實際行為。

### 2. 重現問題

建立**失敗測試**把 bug 條件固定下來（以 .NET / xUnit 為例，其他框架比照）：

```csharp
[Fact]
public async Task MethodName_WhenBugCondition_ShouldExpectedBehavior()
{
    // Arrange - 重現 bug 的條件
    var sut = new ServiceUnderTest(mockDependency);

    // Act
    var result = await sut.ProblematicMethodAsync();

    // Assert - 預期的正確行為
    result.Should().Be(expected);
}
```

執行並確認它**失敗**（先看到紅燈才有意義）：

```bash
dotnet test --filter "FullyQualifiedName~BugCondition"
```

### 3. 根因分析

追蹤程式碼路徑：

1. 從失敗點向上追呼叫堆疊。
2. 檢查相關的服務／資料存取實作。
3. 驗證資料查詢邏輯（如適用）。
4. 檢查依賴注入註冊是否正確。

常見根因對照：

| 症狀 | 可能原因 |
|------|---------|
| Null 參考例外 | 依賴未註冊、設定值/連線字串為空 |
| 資料不正確 | 查詢或轉換邏輯錯誤 |
| 輸出未更新 | 狀態變更未觸發、快取未失效 |
| 操作無回應 | 前置條件判斷回傳 false、事件未綁定 |

> 追「為何」到源頭，別在下游改讀另一處資料把症狀遮掉。

### 4. 修復問題

依 Clean Architecture 對症下藥，改在正確的層：

- Domain 邏輯問題 → 修改 Entity / 領域規則
- 應用流程問題 → 修改 Application Service
- 資料存取問題 → 修改 Infrastructure Repository
- 呈現層問題 → 修改 Controller / 視圖模型

### 5. 驗證修復

先跑先前的失敗測試轉綠，再跑全部測試確認**無回歸**：

```bash
dotnet test --filter "FullyQualifiedName~BugCondition"   # 目標測試轉綠
dotnet test                                              # 全體無回歸
```

### 6. 確認建置

```bash
dotnet build
```

## 除錯工具

```bash
# 查看測試詳細輸出
dotnet test --verbosity normal

# 執行特定測試專案
dotnet test tests/{Project}.Application.Tests
```

Mock 呼叫驗證（語法依你採用的 mocking 框架）：

```csharp
// 確認方法被呼叫 / 未被呼叫
await mock.Received(1).MethodAsync(Arg.Any<string>());
mock.DidNotReceive().MethodAsync(Arg.Any<string>());
```

## 檢查清單

- [ ] 建立失敗測試重現問題
- [ ] 識別根因（追到源頭，非表象）
- [ ] 修復程式碼（改在正確的層）
- [ ] 目標測試通過
- [ ] 全體測試無回歸
- [ ] 建置成功
