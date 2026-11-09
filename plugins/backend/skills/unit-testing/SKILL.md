---
name: unit-testing
description: 後端單元測試：分析被測類別、設計分支案例、Mock 資料來源決策、AAA 結構、測試價值複審剪枝、個資脫敏。附 .NET（xUnit／Moq）附錄與範本。Use when 新功能測試覆蓋、補測試缺口、TDD 紅燈階段的測試骨架、unit test、單元測試、寫測試、補測試。
triggers: ["寫單元測試", "補單元測試", "unit test", "補測試缺口"]
---

# 後端單元測試

## 0. 偵測技術棧與附錄

先看專案的 `*.csproj`（xUnit／NUnit）、`go.mod`、`pyproject.toml`（pytest）、`package.json`（jest／vitest）、`pom.xml`（JUnit）、既有測試目錄，對照下表載入附錄，並在回報第一行寫「附錄：<檔名>」。

| 偵測到 | 附錄 |
|---|---|
| `*.csproj`／`*.sln`（.NET） | `${CLAUDE_PLUGIN_ROOT}/references/stacks/dotnet.md`（共用）＋ `references/dotnet.md`（xUnit／Moq 慣例、指令）＋ `references/dotnet-templates.md`（測試範本） |
| `go.mod`、`pyproject.toml`、node 後端的 `package.json`、`pom.xml` 等 | 目前沒有附錄，走下方退路 |

沒有對應附錄：照本 skill 的通用方法，加上專案既有程式的寫法（先找 2–3 個同類檔當樣板；有裝 workspace 就照 `workspace:convention-first`（可選））。做完問使用者要不要把這次的寫法整理成新附錄 `references/stacks/<stack>.md`，回報寫「附錄：無（照既有程式）」。

## 1. 原則

1. 單元測試用專案既有測試框架與 mock 工具；斷言風格跟隨專案。
2. 遵循 **AAA**（Arrange-Act-Assert）；一個測試一個斷言概念。
3. 測試命名：方法名表達「方法_情境_預期結果」；顯示名稱是否用繁中跟隨團隊慣例。
4. Mock data 盡量貼近真實資料格式。
5. 只 mock 外部依賴（API、計時器、DB）；測行為，不測實作細節。
6. 測試失敗就修復或移除，**絕不跳過**。

## 2. 流程

### Step 0：Mock Data 來源決策

依優先順序取得真實資料格式：

1. **DB schema／取樣**（若可查）：主鍵格式、外鍵、列舉值分布、欄位型別與長度。
2. **既有測試檔案**（搜尋同類測試）：沿用專案已在用的格式。
3. **合理推測值**（最後手段）。

沒有查 DB 的工具時，在輸出標明「需要 DB 事實：{表名} schema＋幾筆 sample」，由主對話取得後再繼續。**禁止**直接使用真實個資（見第 4 節）。

### Step 1：分析被測類別

1. 讀被測的 Handler／Validator／Repository 原始碼。
2. 識別所有相依介面（建構子注入）。
3. 列出所有邏輯分支（條件、guard、早退）。
4. 確認 Request／Response／Entity 屬性。
5. **有規格書**：逐條提取業務邏輯、驗證規則、guard 條件，每條至少對應 1 個測試。

### Step 2：設計案例

依價值排序：**高價值必測**（業務分支、guard、計算、狀態流轉、跨表連動、驗證）；**低價值可跳**（純映射、純轉發、日誌、純測框架行為）。每個邏輯分支至少一個測試。常見分支：正常路徑、找不到、已刪除、驗證失敗、業務規則、副作用（如有呼叫 commit）。

### Step 3：生成測試

用附錄範本（Command／Query／Update／Delete／Validator／Paged）套入實際名稱。

### Step 4：執行

**預設一律帶篩選條件**，只跑新增／修改的測試＋引用到被改動類別的既有測試。迭代期禁止跑全 suite；全 suite 僅最終回歸（commit 前／CI）跑一次。指令見附錄或專案 README／CI。

### Step 5：結束前測試價值複審（commit／宣告完成前必走）

防止為衝覆蓋率累積的「測框架本身」低價值案例留到 commit。

1. 列出本 session 動過的測試檔（`git diff --name-only HEAD` 篩測試檔）。
2. 對每個新增／修改的案例套用價值矩陣：

   | 斷言對象 | 判定 | 動作 |
   |---------|------|------|
   | 業務規則分支／guard／自動計算／狀態流轉／驗證 | 高價值 | 保留 |
   | 純映射、無邏輯轉發、日誌 | 低價值 | 候選刪除 |
   | 純測框架行為（查詢運算式、ORM predicate、mapper passthrough） | 低價值 | 候選刪除 |
   | 多測試測同一條 predicate 不同切片 | 低價值（重疊） | 刪除最弱者 |

   核心判斷句：「斷言的是業務規則，還是框架照文件運作？」後者刪。
3. 列出低價值候選＋理由（檔案、方法名、對應矩陣哪條）。
4. **徵詢使用者確認後才刪除**，禁止自動刪除。
5. 刪除後重跑篩選確認仍綠、測試數減少。

## 3. 測試類型決策矩陣

| 測試對象 | Mock | 記憶體 DB | 真實 DB |
|---------|------|-----------|---------|
| Handler 業務邏輯 | **首選** | - | - |
| 驗證器 | **首選** | - | - |
| Repository CRUD | - | 可接受 | **首選**（驗 SQL 轉譯） |
| ORM 設定（FK／索引／約束） | - | **禁止**（不驗約束） | **必須** |
| 原生 SQL／micro-ORM 查詢 | - | **禁止** | **必須** |
| DB 引擎特定行為（CTE、定序截斷、字元補齊、分頁語法） | - | **禁止** | **必須** |

涉及引擎特定語法、定序／編碼、ORM 約束、原生 SQL、LINQ→SQL 轉譯正確性時必須用真實 DB。整合測試另走整合測試流程，本 skill 專注單元測試。

## 4. 敏感資料脫敏

Mock data **禁止**真實個資，一律替換為虛構值：

| 資料類型 | 替代值 |
|---------|--------|
| 人名 | 王大明、李小華、張美玲 |
| 公司名稱 | 範例精密、示範實業、台灣製造 |
| 電話 | 02-12345678 |
| Email | test@example.com |
| 地址 | 台北市中正區範例路100號 |
| 統編 | 12345678 |

主鍵、單據編號、品名等非個資欄位可保留真實格式。

## 5. TDD 模式

Red-Green-Refactor 的完整做法見 `workspace:debugging`（可選；沒裝 workspace 就照「先寫失敗測試→最小實作→重構、每階段跑篩選測試」自行進行）。本 skill 提供紅燈階段的測試骨架；測試先行實作可派 `lifecycle:tester`（可選；沒裝 lifecycle 就用 general-purpose agent，prompt 帶「測試工程師，先寫會失敗的測試」）。派工 prompt 要帶上 §0 載入的附錄絕對路徑（`${CLAUDE_PLUGIN_ROOT}` 展開後），agent 才讀得到；general-purpose 退路也一樣。

## Red Flags — STOP

- 「顯示名稱太麻煩，用英文就好」——跟隨團隊慣例，要求繁中就補上
- 「Mock data 隨便填就好」——真實格式能發現更多邊界問題
- 「不用查資料庫，我知道格式」——有工具就先查，格式可能已變更
- 「這個分支不用測」——先確認，每個邏輯分支至少一個測試
- 「測試新加完直接 commit，無複審」——commit 前必走 Step 5
