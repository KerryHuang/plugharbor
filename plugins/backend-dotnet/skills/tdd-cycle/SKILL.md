---
name: tdd-cycle
description: 執行 Red-Green-Refactor 測試先行循環。適用於任務標記 [TDD]、使用 --tdd 參數、或實作複雜業務邏輯需要測試先行開發時。搭配 unit-testing skill 生成測試骨架。
---

## 流程概覽

```
Red (寫失敗測試) → Green (最小實作) → Refactor (重構) → 重複
```

## Phase 1：Red — 寫失敗測試

1. **分析需求**：從規格書（若有）提取測試案例
   - 逐條對應業務規則：業務邏輯 → 分支/計算/狀態流轉測試；驗證規則 → FluentValidation 測試；Guard/前置條件 → guard clause 測試
   - 依測試價值判斷優先級，**高價值先行**（業務分支、Guard、計算、狀態流轉、Validation）
   - 每條規則至少 1 個測試，DisplayName 標註規則來源
2. **建立測試類別**（放在專案測試目錄的對應 `{Commands|Queries}/` 下）
3. **使用 `unit-testing` skill** 生成測試骨架
4. **執行驗證**（只跑本測試類別）：

   ```bash
   dotnet test --filter "FullyQualifiedName~{TestClass}"
   ```

5. **確認失敗**：測試必須失敗（紅燈）——編譯失敗也算預期紅燈

輸出：

```
[RED] 測試 {TestName} 已建立
[RED] 執行結果：失敗 ✓（預期行為）
[RED] 失敗原因：{原因}
→ 進入 Green Phase
```

## Phase 2：Green — 最小實作

原則：**只寫通過測試的最小程式碼**，不追求完美、不過度設計，允許暫時的「醜」程式碼。

1. **建立實作檔案**（若不存在）
2. **寫最小程式碼**通過測試
3. **執行驗證**：`dotnet test --filter "FullyQualifiedName~{TestClass}"`
4. **確認通過**（綠燈）

輸出：

```
[GREEN] 實作 {ClassName} 已建立
[GREEN] 執行結果：通過 ✓
→ 進入 Refactor Phase
```

## Phase 3：Refactor — 重構

原則：**不改變外部行為**，改善可讀性、移除重複、提取方法。

1. **識別重構機會**：重複程式碼、過長方法、命名不清
2. **執行重構**
3. **執行驗證**：`dotnet test --filter "FullyQualifiedName~{TestClass}"`
4. **確認仍通過**（綠燈）

輸出：

```
[REFACTOR] 重構完成：{重構描述}
[REFACTOR] 執行結果：通過 ✓
→ 循環完成，可進入下一個測試案例
```

## 循環完成報告

```markdown
## TDD 循環報告

| 階段 | 狀態 | 說明 |
|------|------|------|
| Red | ✅ | 測試 {TestName} 建立並失敗 |
| Green | ✅ | 實作 {ClassName} 通過測試 |
| Refactor | ✅ | {重構描述} |

### 建立的檔案
- 測試：`{TestFilePath}`
- 實作：`{ImplFilePath}`

### 下一步
- [ ] 繼續下一個測試案例
- [ ] 最終回歸：`dotnet test`（commit 前跑一次全 suite）
```

## 整合

- **測試範本 / 骨架**：使用 `unit-testing` skill
- **測試命名**：方法名 `Method_Scenario_ExpectedResult`（英文），屬性 `[Fact(DisplayName = "繁中描述")]`（跟隨團隊慣例）
- **收尾**：完成所有循環後，走 `unit-testing` skill 的 Step 5 測試價值複審剪枝，再 commit
