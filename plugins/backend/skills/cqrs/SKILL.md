---
name: cqrs
description: CQRS 用例拆分：Command／Query Handler、Notification 事件、交易管線、分頁查詢與回傳規則。附 .NET（MediatR）附錄。Use when 新增 Handler、實作 CRUD 操作、cqrs、command handler、query handler、mediator、notification、交易管線、transaction behavior。
triggers: ["command handler", "query handler", "新增 Handler", "CQRS"]
---

# CQRS 用例（Command／Query）

## 0. 偵測技術棧與附錄

先看專案的 `*.csproj`（是否引用 MediatR）、`go.mod`、`pyproject.toml`、`package.json`、`pom.xml`、既有 Handler／UseCase 目錄，對照下表載入附錄，並在回報第一行寫「附錄：<檔名>」。

| 偵測到 | 附錄 |
|---|---|
| `*.csproj`／`*.sln`（.NET，MediatR） | `${CLAUDE_PLUGIN_ROOT}/references/stacks/dotnet.md`（共用）＋ `references/dotnet.md`（Handler 範本、Notification、TransactionBehavior） |
| `go.mod`、`pyproject.toml`、node 後端的 `package.json`、`pom.xml` 等 | 目前沒有附錄，走下方退路 |

沒有對應附錄：照本 skill 的通用方法，加上專案既有程式的寫法（先找 2–3 個同類檔當樣板；有裝 workspace 就照 `workspace:convention-first`（可選））。做完問使用者要不要把這次的寫法整理成新附錄 `references/stacks/<stack>.md`，回報寫「附錄：無（照既有程式）」。

## 1. 核心做法

1. 確定目標模組，沿用專案分層與命名。
2. **寫入（Command）與讀取（Query）分開**：Command 改狀態、回傳結果物件；Query 不改狀態、只回資料。
3. 一個 Request 對一個 Handler；Handler 只編排（驗證 → 載入 → 領域規則 → 儲存），不在裡面寫 SQL 或 HTTP。
4. 沿用專案既有的結果型別（Result pattern）、工作單元（Unit of Work）、物件映射，不自創。
5. 所有非同步方法支援取消（cancellation token 一類機制）。

## 2. 回傳類型規則

| 操作類型 | 回傳 |
|---------|------|
| Command | 結果物件（成功／失敗＋訊息＋可選資料） |
| Get Single | 可為空的單一物件 |
| GetFilter | 清單 |
| GetPaged | 分頁回應物件（項目、總筆數、目前頁、每頁筆數） |
| Notification | 無回傳 |

失敗用結果物件回報，不在 Handler 內裸拋給呼叫端。

## 3. 分頁查詢

- 所有分頁 Request 繼承共用分頁基底（頁碼、每頁筆數、排序欄、排序方向）。
- 單表／簡單 JOIN：ORM＋篩選條件物件，由 Repository 分頁。
- 多表複雜 JOIN：手寫 SQL，排序走白名單，Handler 設預設排序（見 `data-access`）。

## 4. Notification（事件）

Command 完成後有多個副作用（審計、Email、庫存調整）或跨模組通知時用事件（一對多）；單一後續操作且強耦合就直接呼叫。

- 定義事件 → 在**儲存成功之後**發布 → 訂閱者各自處理。
- 交易內禁發布事件、禁外部 I/O（HTTP／檔案／MQ）。

## 5. 交易模式選用

多筆寫入需原子性時先選模式（**禁止**跨連線／分散式交易範圍，不可控）：

| 情境 | 做法 |
|------|------|
| 一般 CRUD 多寫入需原子性（多數情境） | Request 標記為「需交易」，由管線 Behavior 自動包裹 |
| 需中途控制（分段 commit、條件式 rollback、交易內重試、自訂隔離等級） | 不標記，Handler 內顯式自管 |
| 交易內呼叫其他存取路徑（如 ORM＋micro-ORM 混用） | 共用同一連線與交易，不要各開各的 |

交易 Behavior 的四要點：

- runtime 檢查 marker（泛型約束攔不住 marker），未標記直通。
- 結果物件為失敗時也要 rollback（不只例外）；自訂回應型別代表失敗必須 throw。
- rollback 失敗只記警告、保留原始例外（容忍伺服器端已中止的交易）。
- 巢狀請求自動加入現有交易，由最外層擁有 commit／rollback。

## 6. 常見管線 Behavior

| Behavior | 用途 |
|----------|------|
| Logging | 記錄 Request 進出 |
| Validation | 自動驗證 |
| Transaction | 交易管理 |
| Performance | 慢請求警告 |

新增 Behavior 時確認順序（驗證 → 交易 → 日誌等）。

## 7. 領域判斷走服務介面

單號產生、租戶／公司別判斷、組態等領域邏輯，Handler 一律**注入服務介面**，禁止在 Handler 內直查設定表。

## 8. 檔案結構（示意）

```
{Module}/{Entity}Service/
├── Commands/        Create／Update／Delete 各一組 Request＋Handler
├── Queries/         Get／GetFilter／GetPaged 各一組 Request＋Handler
├── Notifications/   選擇性：事件＋訂閱者
├── Models/          Response、分頁／篩選模型
├── Mappers/
├── DataValidation/
└── Helpers/         篩選條件建構
```

## 9. 檢查清單

- [ ] Command／Query 分離，Query 沒改狀態
- [ ] 回傳類型符合上表
- [ ] 多寫入已選定交易模式，事件在儲存成功後發布
- [ ] 領域判斷走服務介面
- [ ] 有對應測試（見 `unit-testing`）
