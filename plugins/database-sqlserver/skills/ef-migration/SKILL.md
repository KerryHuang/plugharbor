---
name: ef-migration
description: Use when 建立 / 套用 / 回復 EF Core migration、跑 `dotnet ef` 指令、切換目標資料庫連線、migration 失敗診斷。管理 SQL Server 上的 Entity Framework Core 資料庫 Migration。觸發：「建 migration」「套用 migration」「回滾 migration」「dotnet ef」「migration 失敗」。
---

# EF Core 資料庫 Migration 管理

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

**Config 優先序（後者覆蓋前者）**：`appsettings.json` → `appsettings.{env}.json` → CLI args → 對應 env var。若專案無此類 factory，直接用 `appsettings.{env}.json` 或 `--connection` 標準機制即可。

## 工作流程

### 1. 建置專案

```bash
dotnet build YourApp.sln -c Release --no-restore
```

### 2. 建立 Migration

#### 2.0 Timestamp 順序檢查（強制前置）

`dotnet ef migrations add` 前必跑，防止本地落後遠端後建出時間戳更早的 migration（會造成套用順序錯亂）：

```bash
git fetch origin
LATEST_MERGED=$(git ls-tree -r origin/develop --name-only \
  | grep -E '^src/YourApp\.Domain/Migrations/[0-9]{14}_.*\.cs$' \
  | sort | tail -1)
echo "origin/develop 最新 migration: $LATEST_MERGED"
date -u +'%Y%m%d%H%M%S'   # 對照即將產生的 timestamp prefix
```

新建 migration 的 14 位 timestamp 前綴**必須晚於** `$LATEST_MERGED`。若本地時鐘晚於 UTC、或 rebase 後遠端有新 migration → 先 `git pull --rebase` 再 `dotnet ef migrations add`。

> **Build pass 不證明順序對**：編譯不檢查 timestamp，必須以本檢查作為獨立驗證。

#### 2.1 執行 add

```bash
dotnet ef migrations add {MigrationName} $EF_ARGS --context AppDbContext
```

**命名慣例**：`Add{Entity}Table`、`Update{Entity}{Field}`、`Remove{Entity}`、`Add{Entity}{Index}Index`、`Alter{Entity}{Field}`。

#### 2.2 add 後驗證

```bash
ls src/YourApp.Domain/Migrations/ | grep -E '^[0-9]{14}_' | sort | tail -3
```

新檔 timestamp 應為清單最後一筆，且晚於 §2.0 紀錄的 `$LATEST_MERGED`。

#### 2.3 Migration ordering 變更保護（高風險，必先確認）

修改既有 migration 的排序 / 命名 / body 屬高 blast-radius 操作，動手前先停下來取得使用者確認：

| 編輯目標 | 必先動作 |
|---------|---------|
| 重新命名 migration `.cs` 檔（timestamp prefix） | **必先確認**，含理由 + 對既有 `__EFMigrationsHistory` 表的影響評估 |
| 刪除已存在的 migration `.cs` | **必先確認**；若該 migration 已 merge 進共用分支 → **禁止**刪除，改走 `dotnet ef migrations add Revert{Name}` 反向 |
| 修改既有 migration 的 `Up()` / `Down()` body | **必先確認**；若已 deploy 到任何環境 → 走 `migration-troubleshoot` skill |
| 手動補 `__EFMigrationsHistory` row | **禁止**自動執行，必使用者明示授權 |

**預設**：不動既有 migration；變更 schema 永遠新增一筆 migration。

### 3. 檢視產生的 Migration

位置：`src/YourApp.Domain/Migrations/`。檢查 `Up()` / `Down()` 正確性。

### 4. 列出 / 產生 SQL 腳本

```bash
# 列出所有 migration
dotnet ef migrations list $EF_ARGS

# 產生增量 SQL 腳本
dotnet ef migrations script $EF_ARGS --output Migrations/{MigrationName}.sql

# 產生冪等腳本（生產部署用）
dotnet ef migrations script --idempotent $EF_ARGS --output {MigrationName}.sql
```

### 5. 套用 Migration

```bash
dotnet ef database update $EF_ARGS

# 特定 migration
dotnet ef database update {MigrationName} $EF_ARGS
```

### 6. 一般失敗修復循環

**IF** migration 失敗 → 讀錯誤、定位 migration `.cs`、直接修 `.cs`、重跑 `dotnet ef database update`（EF 從失敗點繼續）→ 再失敗再修。

**不用** `migrations remove`，直接修 `.cs` 重跑。

**常見錯誤**：

| 特徵 | 分析 | 修法 |
|------|------|------|
| `Invalid column name 'XXX'` | DDL 後接 DML，編譯時欄位不存在 | DML/ALTER 包 `EXEC('...')` 延遲編譯 |
| `Cannot find the object "Schema.Table"` | 新環境缺舊表 | 用 `IF OBJECT_ID('Schema.Table', 'U') IS NOT NULL` 守衛 |
| Factory log 顯示連錯 host | 連線參數設錯 | 檢查 CLI args / env var / appsettings |

> **特殊情境** — ModelSnapshot 衝突、資料庫已套用但 migration 紀錄遺失、生產緊急回滾診斷 → 走 `migration-troubleshoot` skill。

**DDL + DML 延遲編譯**：

```sql
-- ❌ 編譯時 NewCol 不存在
ALTER TABLE T ADD NewCol char(10) NULL;
UPDATE T SET NewCol = 'x' WHERE NewCol IS NULL;

-- ✅ EXEC 延遲編譯
ALTER TABLE T ADD NewCol char(10) NULL;
EXEC('UPDATE T SET NewCol = ''x'' WHERE NewCol IS NULL');
```

### 7. 切換目標資料庫

**單次指令**的暫時連線覆寫（不碰 appsettings）。取得目標 DB 連線資訊後，依專案支援的機制擇一：

**方式 A — 自訂 factory CLI args**（專案 factory 支援時）：

```bash
dotnet ef migrations list $EF_ARGS -- \
  --mssqlHost <host> --mssqlPort <port> \
  --mssqlUserId <user> --mssqlPassword <pw> \
  --mssqlDatabase <db>
```

**方式 B — env var override**（適合自動化腳本）：

```bash
export MSSQL__Host=<host> MSSQL__Port=<port> MSSQL__UserId=<user> \
       MSSQL__Password=<pw> MSSQL__ApplicationDatabase=<db>
dotnet ef migrations list $EF_ARGS
unset MSSQL__Host MSSQL__Port MSSQL__UserId MSSQL__Password MSSQL__ApplicationDatabase
```

**方式 C — 標準 EF 連線覆寫**：`dotnet ef database update $EF_ARGS --connection "<connection string>"`。

**禁用**：直接改 `appsettings.Development.json` 再還原 — 易忘記還原造成污染。長期切換才改 appsettings。

### 8. 驗證資料庫狀態

```bash
dotnet ef dbcontext info $EF_ARGS
```

### 9. 回復 / 移除 Migration

```bash
# 回復到指定 migration
dotnet ef database update {PreviousMigrationName} $EF_ARGS

# 回復所有
dotnet ef database update 0 $EF_ARGS

# 移除未套用的 migration
dotnet ef migrations remove $EF_ARGS
```

## 生產環境部署

檢查清單：測試環境驗證 → 檢查 SQL 腳本 → 備份資料庫 → 維護時段套用 → 驗證完整性 → 準備回復計劃。

## 執行後：回報資料庫連線資訊

每次執行任何 migration 操作後（建立 / 套用 / 回復 / 列出），**必須**向使用者回報目前的資料庫連線資訊：

```
📦 目前資料庫連線
  Host     : <host>
  Port     : <port>
  Database : <database>
  User     : <userId>
```

**取得來源（依優先順序）**：

1. **CLI args / `--connection`**（本次指令明確傳入）→ 直接讀取
2. **`MSSQL__*` env var**（`env | grep MSSQL__`）→ 從環境變數讀取
3. **`dotnet ef dbcontext info $EF_ARGS`** → 解析輸出的 `ConnectionString`
4. **`appsettings.{env}.json`** → 讀 `ConnectionStrings.DefaultConnection`

**不確定時**（來源模糊）→ 加上 `[推論]` 標記。
