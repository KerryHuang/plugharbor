---
name: unit-testing
description: 生成 xUnit 單元測試，涵蓋 CQRS Handler、Validator、Repository。適用於新功能測試覆蓋、TDD 測試先行開發、或補充既有測試缺口。使用 Moq mock 依賴、遵循 AAA 模式，測試方法名用英文、DisplayName 用繁體中文。
---

## Instructions

1. 測試框架用 **xUnit** + **Moq**（mock 依賴）；斷言可用內建 `Assert` 或 FluentAssertions（跟隨專案既有選擇）
2. 遵循 **AAA 模式**（Arrange-Act-Assert）
3. 測試類別命名：`{Handler/Validator/Repository}Tests.cs`
4. 測試方法命名：`{Method}_{Scenario}_{ExpectedResult}`（英文）
5. **建議**為每個 `[Fact]` 加 `[Fact(DisplayName = "繁中描述")]`（跟隨團隊慣例）
6. Mock data 盡量貼近真實資料格式

## 流程

### Step 0：Mock Data 資料來源決策

依優先順序取得真實資料格式：

1. **DB schema / 取樣**（若可查）：取得表結構、主鍵格式、外鍵格式、列舉值分布、欄位型別與長度
2. **既有測試檔案**（Grep 搜尋同類測試）：沿用專案已在用的格式
3. **合理推測值**（最後手段）

**禁止**：直接使用真實個資或敏感資料——一律替換為虛構值（見「敏感資料脫敏」）。

### Step 1：分析被測類別

1. 讀取 Handler / Validator / Repository 原始碼
2. 識別所有相依介面（constructor DI）
3. 列出所有邏輯分支（if/else、guard clause、早退）
4. 確認 Request / Response / Entity 屬性
5. **若有規格書**：逐條提取業務邏輯、驗證規則、Guard 條件，每條規則至少對應 1 個測試

### Step 2：設計測試案例

依測試價值判斷優先級：**高價值必測**（業務分支、Guard、計算、狀態流轉、跨表連動、Validation）；**低價值可跳**（純映射、純轉發、Logger、純測框架行為）。

每個邏輯分支至少一個測試。方法名英文，DisplayName 繁中：

| 分支類型 | 方法名 | DisplayName |
|---------|--------|-------------|
| 正常路徑 | `Handle_ValidRequest_ReturnsSuccess` | `操作_有效請求_回傳成功` |
| 找不到 | `Handle_EntityNotFound_ReturnsNotFound` | `操作_不存在_回傳未找到` |
| 已刪除 | `Handle_EntityDeleted_ReturnsFailure` | `操作_已刪除_回傳失敗` |
| 驗證失敗 | `Validate_EmptyField_ShouldFail` | `驗證_欄位為空_驗證失敗` |
| 業務規則 | `Handle_Condition_Behavior` | `操作_情境_預期結果` |
| 副作用 | `Handle_Success_CallsCommit` | `操作_成功後應呼叫Commit` |

### Step 3：生成測試程式碼

使用 [test-templates.md](references/test-templates.md) 的範本（Command / Query / Update / Delete / Validator / Paged Query / InMemory 基底）。

### Step 4：執行測試

**預設一律帶 `--filter`**，只跑本次新增/修改測試 + reference 到被改動 function/class 的既有測試。迭代期禁止跑全 suite（大型 repo 全跑數分鐘、filtered 數秒）。全 suite 僅最終回歸（commit 前 / CI）跑一次。

```bash
# 迭代期：鎖定新增/受影響範圍
dotnet test --filter "FullyQualifiedName~{TestClassName}" --logger:trx

# 最終回歸（commit 前 / CI）
dotnet test
```

### Step 5：結束前測試價值複審（commit / 宣告完成前必走）

防止 TDD 過程為衝覆蓋率而累積的「測框架本身」低價值案例留到 commit。

1. **列出本 session 動過的測試檔**：`git diff --name-only HEAD -- '**/*Tests.cs'`
2. **對每個新增/修改的 `[Fact]` 套用價值矩陣**：

   | 斷言對象 | 判定 | 動作 |
   |---------|------|------|
   | 業務規則分支 / Guard / 自動計算 / 狀態流轉 / Validation | 高價值 | 保留 |
   | 純映射、無邏輯轉發、Logger | 低價值 | 候選刪除 |
   | 純測框架行為（LINQ Expression、ORM predicate、mapper passthrough） | 低價值 | 候選刪除 |
   | 多測試測同一條 predicate 不同切片 | 低價值（重疊） | 刪除最弱者 |

   核心判斷句：「斷言的是業務規則，還是框架照文件運作？」後者刪。
3. **列出低價值候選 + 理由**（檔案路徑、方法名、對應矩陣哪條）
4. **徵詢使用者確認後才刪除**——禁止自動刪除（使用者可能有 contextual 理由保留）
5. **刪除後重跑 filter 確認綠**，確認測試數減少、其餘仍綠

## 敏感資料脫敏

Mock data 中**禁止**使用真實個資，一律替換為虛構值：

| 資料類型 | 替代值 |
|---------|--------|
| 人名 | 王大明、李小華、張美玲 |
| 公司名稱 | 範例精密、示範實業、台灣製造 |
| 電話 | 02-12345678 |
| Email | test@example.com |
| 地址 | 台北市中正區範例路100號 |
| 統編 | 12345678 |

> 主鍵、單據編號、品名等**非個資欄位**可保留真實格式。

## 測試類型決策矩陣

| 測試對象 | Mock (Moq) | InMemory DB | 真實 DB |
|---------|------------|-------------|---------|
| Handler 業務邏輯 | **首選** | - | - |
| FluentValidation | **首選** | - | - |
| Repository CRUD | - | 可接受 | **首選**（驗 SQL 轉譯） |
| EF Core Configuration（FK/索引/約束） | - | **禁止**（不驗約束） | **必須** |
| 原生 SQL / Dapper 查詢 | - | **禁止** | **必須** |
| DB 引擎特定行為（CTE、定序截斷、字元補齊、分頁語法） | - | **禁止** | **必須** |

**何時必須用真實 DB**：涉及資料庫引擎特定語法、定序/編碼行為、EF Core Configuration 約束、原生 SQL、或 LINQ→SQL 轉譯正確性。整合測試（真實 DB）另走整合測試流程，本 skill 專注單元測試。

## TDD 模式

搭配 `tdd-cycle` skill 執行 Red-Green-Refactor。本 skill 提供 Red Phase 的測試骨架。

## Red Flags — STOP

- 「DisplayName 太麻煩，用英文就好」——跟隨團隊慣例，若團隊要求繁中就補上
- 「Mock data 隨便填就好」——真實格式能發現更多邊界問題
- 「不用查資料庫，我知道格式」——有工具就先查，格式可能已變更
- 「這個分支不用測」——先確認，每個邏輯分支至少一個測試
- 「測試新加完直接 commit，無複審」——commit 前必走 Step 5 價值複審剪枝

## References

- [test-templates.md](references/test-templates.md) — 完整測試範本（Command / Query / Update / Delete / Validator / Paged / InMemory）
