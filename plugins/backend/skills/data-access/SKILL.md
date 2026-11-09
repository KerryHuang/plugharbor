---
name: data-access
description: 資料存取層：Repository 介面與實作、查詢物件、ORM 與 micro-ORM（如 Dapper）的取捨、參數化查詢、排序白名單、分頁。附 .NET（EF Core＋Dapper）附錄。Use when 建立新 Repository、實作資料存取層、新增自訂查詢方法、複雜 SQL 查詢、分頁、repository pattern、data access layer、dapper query、raw sql。
triggers: ["新增 Repository", "資料存取層", "dapper 查詢", "分頁查詢"]
---

# 資料存取（Repository 與查詢）

## 0. 偵測技術棧與附錄

先看專案的 `*.csproj`（EF Core／Dapper）、`go.mod`、`pyproject.toml`（SQLAlchemy 等）、`package.json`（Prisma／TypeORM）、`pom.xml`、DB 連線字串、migration 目錄，對照下表載入附錄，並在回報第一行寫「附錄：<檔名>」。

| 偵測到 | 附錄 |
|---|---|
| `*.csproj`／`*.sln`（.NET） | `${CLAUDE_PLUGIN_ROOT}/references/stacks/dotnet.md`（共用）＋ `references/dotnet.md`（BaseRepository、SqlGenerator、CTE 分頁、排序白名單） |
| `go.mod`、`pyproject.toml`、node 後端的 `package.json`、`pom.xml` 等 | 目前沒有附錄，走下方退路 |

沒有對應附錄：照本 skill 的通用方法，加上專案既有程式的寫法（先找 2–3 個同類檔當樣板；有裝 workspace 就照 `workspace:convention-first`（可選））。做完問使用者要不要把這次的寫法整理成新附錄 `references/stacks/<stack>.md`，回報寫「附錄：無（照既有程式）」。

## 1. Repository 規則

1. 介面定義在內層（Domain），實作在外層（Infrastructure／Persistence）；Application 只認介面。
2. 共用基底類別封裝常見 CRUD（取單筆、取全部、條件查詢、分頁、新增、更新、刪除）；沒有現成基底，可自建，重點是把兩條存取路徑（ORM、原生 SQL）統一暴露給子類別。
3. 所有方法支援取消。
4. 軟刪除用旗標欄位標記，不實體刪除；**每個自訂查詢都要明確帶刪除條件**。
5. Repository 只管存取，業務規則留在 Application。

## 2. ORM 與 micro-ORM 取捨

| 情境 | 選用 | 理由 |
|------|------|------|
| 單表 CRUD、簡單 JOIN、需要變更追蹤 | ORM | 開發快、型別安全 |
| 多表複雜 JOIN（>3 表）、報表、效能敏感、DB 引擎特定語法 | micro-ORM／手寫 SQL | SQL 形狀可控 |
| 批次大量寫入 | micro-ORM 或批次 API | 避開逐筆追蹤成本 |
| 兩者並存 | 同一連線與交易 | 避免交易不一致 |

灰色地帶（JOIN >3、報表、需 View）→ 派 `lifecycle:architect` 抉擇（可選；沒裝 lifecycle 用 general-purpose agent，prompt 帶「架構顧問，給 2–3 方案與 trade-off」）。派工 prompt 要帶上 §0 載入的附錄絕對路徑（`${CLAUDE_PLUGIN_ROOT}` 展開後），agent 才讀得到；general-purpose 退路也一樣。

## 3. 查詢規則

- **值一律參數化**，禁止字串串接（SQL Injection）。
- **識別符（欄位、排序）無法參數化**：走白名單映射，絕不把使用者字串直接串進 `ORDER BY`。
- 動態 WHERE：用條件清單＋參數集合組裝，不手動串值。
- 回傳專用 DTO，不用動態型別；資料清洗（Trim、正規化）止於 SQL 層。
- 唯讀查詢用無追蹤模式；投影只取要用的欄位；避免 N+1 與迴圈內查詢。
- 複雜 JOIN 優先 micro-ORM，不硬塞給 ORM。

## 4. 分頁

分頁語法依**目標 DB 版本**選擇：

- 窗口函式＋CTE（`ROW_NUMBER`）：相容性最廣，舊版唯一選項。
- `OFFSET／FETCH`（或 `LIMIT／OFFSET`）：語法簡潔，需確認版本支援。

Repository 回傳「總筆數＋當頁項目」，頁碼與每頁筆數由共用分頁基底提供；排序預設值由 Handler 或 Repository 設定。

## 5. 髒讀提示

唯讀報表類查詢可接受髒讀時才使用鎖提示（如 `NOLOCK`），一致性要求高的查詢不用。

## 6. 測試

- Repository 查詢、原生 SQL、DB 引擎特定行為（CTE、定序、分頁語法）必須用**真實 DB** 驗證；記憶體 DB 不驗約束與 SQL（見 `unit-testing` 決策矩陣）。

## 7. 檢查清單

- [ ] 介面在內層、實作在外層
- [ ] 值參數化，排序走白名單
- [ ] 每個自訂查詢帶軟刪除條件
- [ ] 回傳強型別 DTO
- [ ] 分頁語法符合目標 DB 版本
- [ ] 有真實 DB 的測試覆蓋自訂 SQL
