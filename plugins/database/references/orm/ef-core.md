# EF Core 附錄（migration、scaffold、entity 設定）

適用：csproj 有 `Microsoft.EntityFrameworkCore*`、專案有 `Migrations/` 目錄與 `*ModelSnapshot.cs`、`DbContext` 類別。由舊 `database-sqlserver` 的 `ef-migration`、`migration-troubleshoot`、`syncing-db-entities` 搬來，為實戰驗證版（以 SQL Server 為主，其他 provider 差異另註）。

## Provider 套件

| 資料庫 | 套件 | efcpt provider 參數 |
|---|---|---|
| SQL Server | `Microsoft.EntityFrameworkCore.SqlServer` | `mssql` |
| PostgreSQL | `Npgsql.EntityFrameworkCore.PostgreSQL` | `postgres` |
| MySQL | `Pomelo.EntityFrameworkCore.MySql` | `mysql` |
| SQLite | `Microsoft.EntityFrameworkCore.Sqlite` | `sqlite` |

## 共用參數

依專案調整 project 路徑與 sln 名稱；以下範例以 `$EF_ARGS` 代替：

```bash
EF_ARGS="--project src/YourApp.Domain --startup-project src/YourApp.Domain"
```

## 自訂 Design-time Factory 的 CLI args（選用）

若專案實作了 `IDesignTimeDbContextFactory` 並支援從 CLI 覆寫連線，可透過 `dotnet ef ... -- --key value` 傳入（官方保證 `-- ` 之後 forward 給 factory）。常見設計：

| 參數 | 用途 |
|------|------|
| `--environment <name>` | 決定 `appsettings.{env}.json`，預設 `Development` |
| `--mssqlHost <host>` | 注入 MSSQL Host |
| `--mssqlPort <port>` | 注入 MSSQL Port |
| `--mssqlUserId <user>` | 注入 MSSQL 使用者 |
| `--mssqlPassword <pw>` | 注入 MSSQL 密碼 |
| `--mssqlDatabase <db>` | 注入 MSSQL 資料庫 |

（其他資料庫把 `mssql` 換成對應前綴，視專案 factory 而定。）

**Config 優先序（後者覆蓋前者）**：`appsettings.json` → `appsettings.{env}.json` → CLI args → 對應 env var。若專案無此類 factory，直接用 `appsettings.{env}.json` 或 `--connection` 標準機制即可。

## Migration 指令

### 建置專案

```bash
dotnet build YourApp.sln -c Release --no-restore
```

### Timestamp 順序檢查（建立前強制）

`dotnet ef migrations add` 前必跑，防止本地落後遠端後建出時間戳更早的 migration（會造成套用順序錯亂）：

```bash
git fetch origin
LATEST_MERGED=$(git ls-tree -r origin/develop --name-only \
  | grep -E '^src/YourApp\.Domain/Migrations/[0-9]{14}_.*\.cs$' \
  | sort | tail -1)
echo "origin/develop 最新 migration: $LATEST_MERGED"
date -u +'%Y%m%d%H%M%S'   # 對照即將產生的 timestamp prefix
```

新建 migration 的 14 位 timestamp 前綴**必須晚於** `$LATEST_MERGED`。若本地時鐘晚於 UTC、或 rebase 後遠端有新 migration → 先 `git pull --rebase` 再 `dotnet ef migrations add`。Build pass 不證明順序對（編譯不檢查 timestamp），此檢查是獨立驗證。

### 建立（add）

```bash
dotnet ef migrations add {MigrationName} $EF_ARGS --context AppDbContext
```

命名慣例：`Add{Entity}Table`、`Update{Entity}{Field}`、`Remove{Entity}`、`Add{Entity}{Index}Index`、`Alter{Entity}{Field}`。

add 後驗證：

```bash
ls src/YourApp.Domain/Migrations/ | grep -E '^[0-9]{14}_' | sort | tail -3
```

新檔 timestamp 應為清單最後一筆，且晚於 `$LATEST_MERGED`。Migration 位置：`src/YourApp.Domain/Migrations/`，檢查 `Up()` / `Down()` 正確性。

### 列出／產生 SQL 腳本

```bash
dotnet ef migrations list $EF_ARGS
dotnet ef migrations script $EF_ARGS --output Migrations/{MigrationName}.sql          # 增量
dotnet ef migrations script --idempotent $EF_ARGS --output {MigrationName}.sql       # 冪等，生產部署用
dotnet ef migrations script {from} {to} $EF_ARGS --output rollback.sql               # 指定區間（回滾腳本）
```

### 套用

```bash
dotnet ef database update $EF_ARGS
dotnet ef database update {MigrationName} $EF_ARGS     # 特定 migration
```

### 回復／移除

```bash
dotnet ef database update {PreviousMigrationName} $EF_ARGS   # 回復到指定 migration
dotnet ef database update 0 $EF_ARGS                         # 回復所有
dotnet ef migrations remove $EF_ARGS                         # 移除未套用的 migration
```

### 驗證資料庫狀態

```bash
dotnet ef dbcontext info $EF_ARGS
```

### 切換目標資料庫（單次指令暫時覆寫，不碰 appsettings）

方式 A — 自訂 factory CLI args（專案 factory 支援時）：

```bash
dotnet ef migrations list $EF_ARGS -- \
  --mssqlHost <host> --mssqlPort <port> \
  --mssqlUserId <user> --mssqlPassword <pw> \
  --mssqlDatabase <db>
```

方式 B — env var override（適合自動化腳本）：

```bash
export MSSQL__Host=<host> MSSQL__Port=<port> MSSQL__UserId=<user> \
       MSSQL__Password=<pw> MSSQL__ApplicationDatabase=<db>
dotnet ef migrations list $EF_ARGS
unset MSSQL__Host MSSQL__Port MSSQL__UserId MSSQL__Password MSSQL__ApplicationDatabase
```

方式 C — 標準 EF 連線覆寫：`dotnet ef database update $EF_ARGS --connection "<connection string>"`。

禁用：直接改 `appsettings.Development.json` 再還原（易忘記還原造成污染）。長期切換才改 appsettings。

### 取得「目前連線資訊」的來源（依優先順序）

1. CLI args／`--connection`（本次指令明確傳入）。
2. `MSSQL__*` env var（`env | grep MSSQL__`）。
3. `dotnet ef dbcontext info $EF_ARGS` 輸出的 `ConnectionString`。
4. `appsettings.{env}.json` 的 `ConnectionStrings.DefaultConnection`。

來源模糊時標 `[推論]`。回報時密碼一律遮蔽。

## 診斷情境指令

診斷表：

| 症狀 | 可能原因 | 診斷指令 |
|------|---------|---------|
| Migration 無法建立 | 建置失敗 | `dotnet build YourApp.sln -c Release` |
| Migration 套用失敗 | SQL 錯誤 | `dotnet ef database update --verbose $EF_ARGS` |
| ModelSnapshot 衝突 | 多人並行開發 | 檢查 git 衝突 |
| 資料庫狀態不明 | 手動修改資料庫 | `dotnet ef migrations list $EF_ARGS` |
| Factory log 顯示連錯 host | 連線 CLI args／env var 設錯 | 檢查連線注入參數 |

### ModelSnapshot 衝突

```bash
git stash                                        # 保存你的變更
git pull                                          # 拉最新
dotnet ef migrations remove $EF_ARGS              # 移除你的 migration
git stash pop                                     # 還原變更
dotnet ef migrations add {NewName} $EF_ARGS --context AppDbContext
```

（`git stash` 在共用 worktree 環境用具名 stash 或 WIP commit 代替。）

### 資料庫已套用但 Migration 遺失（同步狀態）

```bash
dotnet ef migrations add EmptySync $EF_ARGS       # 建立空 migration
# 手動清空 Up() 和 Down()
dotnet ef database update $EF_ARGS                # 只寫 __EFMigrationsHistory
```

### 一般失敗修復循環

migration 失敗 → 讀錯誤、定位 migration `.cs`、直接修 `.cs`、重跑 `dotnet ef database update`（EF 從失敗點繼續）→ 再失敗再修。**不用** `migrations remove`。

## Migration 內的 SQL 寫法

DDL 後接 DML 需延遲編譯（SQL Server）：

```sql
-- 錯：編譯時 NewCol 不存在
ALTER TABLE T ADD NewCol char(10) NULL;
UPDATE T SET NewCol = 'x' WHERE NewCol IS NULL;

-- 對：EXEC 延遲編譯
ALTER TABLE T ADD NewCol char(10) NULL;
EXEC('UPDATE T SET NewCol = ''x'' WHERE NewCol IS NULL');
```

在 C# migration 裡用 `migrationBuilder.Sql("...")`；其他 provider 的語法與限制見對應方言附錄。不包交易：`migrationBuilder.Sql("...", suppressTransaction: true)`。

## efcpt（EF Core Power Tools）scaffold

用 EF Core Power Tools CLI 從資料庫 reverse engineer Entity。

### 雙 Config 機制

CLI 與 GUI 使用**不同的 config 檔案**，兩邊必須同步：

| | GUI | CLI |
|--|-----|-----|
| Config | `efpt.config.json` | `efcpt-config.json` |
| 格式 | flat JSON（`UseT4`） | nested JSON（`use-t4`） |
| 表清單 | `Tables[].Name` + `ObjectType` | `tables[].name` + `views[].name`（分開） |

新增表時必須同時更新兩個 config，排序按 Schema 分組、Schema 內按名稱字母排序。

偵測 config 缺失：

```bash
find <project-dir> -name "efpt.config.json" -o -name "efcpt-config.json"
```

- 只有舊版 `efpt.config.json`：補新版 CLI config（JSON key 由 capitalized 轉 kebab-case，`Tables` 按 `ObjectType` 分為 `tables`（0）與 `views`（3））。
- 只有新版 `efcpt-config.json`：僅需新版；舊版只有 VS GUI 使用者才需要，可省略。
- 兩個都有但表清單不同步：以新版為準補齊舊版。

GUI 格式（`ObjectType`：0 = Table、3 = View）：

```json
{ "Name": "[Schema].[TableName]", "ObjectType": 0 }
```

CLI 格式（Table 加在 `"tables"`，View 加在 `"views"`）：

```json
{ "name": "[Schema].[TableName]" }
```

### CLI 版本要求

必須使用與專案 EF Core 版本對應的 CLI，版本不符會造成 Entity 屬性名稱差異、build 失敗：

```bash
dotnet tool install ErikEJ.EFCorePowerTools.Cli -g --version 8.*
efcpt --version   # 確認顯示 "for EF Core 8"
```

| 專案 EF Core | CLI 版本指令 |
|-------------|-------------|
| 8.x | `--version 8.*` |
| 9.x | `--version 9.*` |
| 10.x | 預設（最新） |

### 執行 scaffold

```bash
cd src/YourApp.Domain
efcpt "<連線字串>" mssql        # provider 參數見上表
```

SQL Server 連線字串：`Server=<host>,<port>;Database=<db>;User Id=<user>;Password=<pw>;TrustServerCertificate=True;`。連線字串**絕不寫入 config 或 commit**，只放記憶體或 shell 變數。CLI 自動讀取 `efcpt-config.json` 和 `CodeTemplates/EFCore/*.t4`（若有）。

### efcpt-config.json 關鍵設定對照

| CLI 設定 | GUI 設定 | 範例值 |
|---------|---------|---|
| `use-t4` | `UseT4` | `true` |
| `use-data-annotations` | `UseFluentApiOnly=false` | `true` |
| `output-path` | `OutputPath` | `"Entities"` |
| `output-dbcontext-path` | `OutputContextPath` | `"Data"` |
| `use-schema-folders-preview` | `UseSchemaFolders` | `true` |
| `split-dbcontext-preview` | `UseDbContextSplitting` | `true` |
| `use-DateOnly-TimeOnly` | `UseDateOnlyTimeOnly` | `false` |
| `dbcontext-name` | `ContextClassName` | `"AppDbContext"` |
| `refresh-object-lists` | N/A | `false`（防止抓全部表） |

### 檢查產出

- `Entities/{Schema}/{Entity}.cs`：Entity。
- `Data/Configurations/{Entity}Configuration.cs`：Configuration。
- `Data/AppDbContext.cs`：新增 `DbSet<Entity>`。

```bash
git diff --stat src/YourApp.Domain/    # 除 AppDbContext.cs 與兩個 config 外不應有既有檔案被改
dotnet build YourApp.sln -c Release --no-restore
```

### 建 migration（scaffold 之後）

```bash
dotnet ef migrations add Add{Entity}Table $EF_ARGS --context AppDbContext
dotnet build YourApp.sln -c Release --no-restore
```

auto-generated 檔頭為 `This file has been auto generated by EF Core Power Tools.`，手改會被下次 scaffold 覆蓋；precision／nullable／MaxLength 偏差回 efcpt 重新產生，或調整 T4 模板。

## 常見坑

- **用 `dotnet ef dbcontext scaffold` 代替 efcpt**
  - 症狀：產出的 Entity 風格與既有不同，缺少雙 config、T4 模板設定。
  - 原因：內建 scaffold 不讀 efcpt config 與模板。
  - 修法：一律用 `efcpt` CLI。
- **只改一個 config**
  - 症狀：CLI 抓得到表、VS GUI 抓不到（或相反）。
  - 原因：雙 config 表清單不同步。
  - 修法：同時更新 `efpt.config.json` 與 `efcpt-config.json`。
- **CLI 版本與專案 EF Core 不符**
  - 症狀：Entity 屬性名稱差異、build 失敗。
  - 原因：裝了最新版 CLI。
  - 修法：`dotnet tool install ... --version <主版號>.*`，`efcpt --version` 確認。
- **scaffold 覆蓋既有手動修改**
  - 症狀：既有 Entity／Configuration 被改。
  - 原因：re-scaffold 會重寫已存在的檔。
  - 修法：scaffold 前備份有手動修改的檔，scaffold 後 `git diff --stat` 確認零差異。
- **migration-first 造成改名沒生效**
  - 症狀：scaffold 出舊欄位名或型別；`migrations add` 吸入髒 snapshot。
  - 原因：efcpt 從尚未更新的資料庫讀。
  - 修法：先讓來源資料庫具備目標 schema → efcpt re-scaffold → 才 `migrations add`。
- **efcpt 連到 runtime DB 而非設計庫**
  - 症狀：scaffold 內容不是預期 schema。
  - 原因：專案的 reverse-engineer 來源是獨立設計庫／參考庫。
  - 修法：確認連線；schema 變更先在設計庫套用並備妥 rollback plan。
- **migration 時間戳早於遠端**
  - 症狀：套用順序錯亂。
  - 原因：本地落後遠端或時鐘偏差。
  - 修法：跑 timestamp 順序檢查，`git pull --rebase` 後重建。
- **Invalid column name／Cannot find the object**
  - 症狀：migration 套用時 SQL Server 報錯。
  - 原因：DDL 後接 DML 編譯期欄位不存在；新環境缺舊表。
  - 修法：`EXEC('...')` 延遲編譯；`IF OBJECT_ID(...) IS NOT NULL` 守衛（詳見 `sqlserver.md` 常見坑）。
