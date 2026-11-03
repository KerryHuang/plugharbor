> 未實戰驗證：本附錄依官方文件整理，尚未在實際專案驗證。

# SQLite 方言附錄

適用：連線字串為檔案路徑，副檔名 `.db`／`.sqlite`／`.sqlite3`，或 `Data Source=*.db`、`Filename=`；csproj 有 `Microsoft.EntityFrameworkCore.Sqlite`；常見於本機 app、測試、嵌入式。

## 型別對照

SQLite 採動態型別（type affinity）：欄位宣告型別只決定「親和性」，任何欄位幾乎可存任何值（`STRICT` 表除外）。

| 概念 | SQLite | SQL Server | PostgreSQL | MySQL |
|---|---|---|---|---|
| 整數 | `INTEGER`（最大 8 bytes） | `int`／`bigint` | `integer`／`bigint` | `int`／`bigint` |
| 布林 | `INTEGER`（0／1） | `bit` | `boolean` | `tinyint(1)` |
| 浮點 | `REAL` | `float` | `double precision` | `double` |
| 定點小數 | 無原生；用 `INTEGER`（存最小單位，如分）或 `TEXT` | `decimal(p,s)` | `numeric(p,s)` | `decimal(p,s)` |
| 字串 | `TEXT`（UTF-8） | `nvarchar(n)` | `text`／`varchar(n)` | `varchar(n)` |
| 日期時間 | `TEXT`（ISO 8601）或 `INTEGER`（Unix 秒） | `datetime2` | `timestamptz` | `datetime(6)` |
| GUID | `TEXT`／`BLOB` | `uniqueidentifier` | `uuid` | `char(36)` |
| 二進位 | `BLOB` | `varbinary(max)` | `bytea` | `blob` |
| JSON | `TEXT`＋JSON1 函式（`json_extract`） | `nvarchar(max)` | `jsonb` | `json` |

建議新表加 `STRICT`（3.37+）強制型別：`CREATE TABLE t (...) STRICT;`，允許型別僅 `INT/INTEGER/REAL/TEXT/BLOB/ANY`。`decimal` 在 SQLite 會被當 `NUMERIC` 親和性，實際以浮點儲存，金額勿依賴；EF Core SQLite 對 `decimal` 也有排序／聚合限制。

## 識別欄／自動遞增

- `INTEGER PRIMARY KEY` 即 rowid 別名，自動遞增（取最大 rowid+1，可能重用被刪的 id）。
- 需要保證不重用：`INTEGER PRIMARY KEY AUTOINCREMENT`（多一張 `sqlite_sequence`，稍慢）。
- 必須精確寫成 `INTEGER`（不是 `INT`）才會成為 rowid 別名。
- 取回新 id：`last_insert_rowid()`，或 `INSERT ... RETURNING`（3.35+）。

## 分頁

```sql
SELECT ... FROM orders
ORDER BY created_at DESC, order_id DESC
LIMIT 20 OFFSET 40;
```

深分頁改 keyset：`WHERE (created_at, order_id) < (?, ?)`（3.15+ 支援 row value）。

## 命名慣例與大小寫

- 慣例 `snake_case`；需引用時用雙引號或 `[ ]`／反引號（皆接受）。
- 識別字不分大小寫（ASCII）。
- 字串比較預設分大小寫（`BINARY`）；不分大小寫用 `COLLATE NOCASE`（僅限 ASCII），或 `lower()`。
- 沒有 schema（只有 `main`、`temp` 與 `ATTACH` 的資料庫別名），領域分組用表名前綴。
- 約束命名可用 `CONSTRAINT pk_x PRIMARY KEY` 語法，但名稱不太被工具使用。

## 預設值與約束

```sql
created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
deleted    INTEGER NOT NULL DEFAULT 0 CHECK (deleted IN (0,1)),
customer_id INTEGER NOT NULL REFERENCES customer(customer_id)
```

- **外鍵預設不啟用**：每個連線都要 `PRAGMA foreign_keys = ON;`（Microsoft.Data.Sqlite 預設會開）。
- 預設值運算式需括號。
- `ALTER TABLE` 能力有限：可 `ADD COLUMN`、`RENAME`、3.35+ 可 `DROP COLUMN`，但不能改欄位型別、加約束或改 NOT NULL；需「建新表→複製資料→刪舊表→改名」重建。
- 檔案型資料庫為單一寫入者；開 WAL（`PRAGMA journal_mode = WAL;`）改善讀寫併發。

## 日期時間與時區

- 沒有日期型別，三種約定擇一並全專案一致：ISO 8601 `TEXT`（建議，可排序）、Unix 時間 `INTEGER`、Julian `REAL`。
- 函式：`datetime('now')`（UTC）、`strftime(fmt, ...)`、`date(x,'+1 day')`、`datetime(x,'localtime')`。
- 無時區資訊：統一存 UTC，字串帶 `Z` 後綴，顯示端轉換。
- EF Core SQLite 把 `DateTime` 存成 ISO 字串，`DateTimeOffset` 的排序／比較在伺服器端翻譯有限制。

## 說明（comment／extended property）怎麼寫

SQLite 沒有 `COMMENT ON` 或 extended property。做法：

- 在 DDL 檔用 SQL 註解（`-- 說明` 或 `/* */`）；註解會保留在 `sqlite_master.sql` 文字內，可由 `SELECT sql FROM sqlite_master` 讀回。
- 說明另存於文件（見 `schema-docs`）或自建 `_column_comment(table_name, column_name, comment)` 表。

## migration 工具

- EF Core：見 `${CLAUDE_PLUGIN_ROOT}/references/orm/ef-core.md`（`Microsoft.EntityFrameworkCore.Sqlite`）。注意 SQLite provider 對 AlterColumn、DropColumn（舊版）、加約束用「重建表」實作，migration 產生的 SQL 會較長。
- 其他：Flyway、Alembic（batch mode）、golang-migrate、Prisma、`PRAGMA user_version` 手動記版本。
- 重建表流程：`PRAGMA foreign_keys=OFF` → BEGIN → 建新表 → `INSERT INTO new SELECT ... FROM old` → `DROP old` → `ALTER new RENAME TO old` → 重建索引／trigger／view → `PRAGMA foreign_key_check` → COMMIT → `foreign_keys=ON`。
- SQLite 的 DDL 可交易，失敗可回滾。

## Table 與 View 寫法要點

```sql
CREATE TABLE IF NOT EXISTS production_workstation (
    workstation_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    workstation_code TEXT NOT NULL,
    created_at       TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    modified_at      TEXT,
    deleted          INTEGER NOT NULL DEFAULT 0
) STRICT;

CREATE VIEW IF NOT EXISTS sales_order_view AS
SELECT o.order_no AS order_id,   -- 訂單編號
       c.name     AS customer_name
FROM orders o
LEFT JOIN customer c ON c.customer_id = o.customer_id;
```

沒有 `CREATE OR REPLACE VIEW`／`CREATE OR ALTER`：改 view 要 `DROP VIEW IF EXISTS` 後重建。

## View 計算欄位關鍵字（供 schema-docs 解析）

`CASE WHEN`、`IFNULL(`、`COALESCE(`、`NULLIF(`、`CAST(`、`julianday(`、`strftime(`、`json_extract(`。布林計算欄位為 `CASE WHEN cond THEN 1 ELSE 0 END`，計算邏輯取條件式。

## 常見坑

- **外鍵沒作用**
  - 症狀：刪除父資料不報錯，留下孤兒列。
  - 原因：外鍵檢查預設關閉，是連線層級設定。
  - 修法：每個連線 `PRAGMA foreign_keys = ON;`；用 `PRAGMA foreign_key_check` 檢查既有資料。
- **database is locked**
  - 症狀：並行寫入時 `SQLITE_BUSY`／`database is locked`。
  - 原因：單一寫入者，讀寫互斥（非 WAL 模式）。
  - 修法：開 WAL；設定 `busy_timeout`（連線字串 `Default Timeout`）；縮短交易；寫入集中序列化。
- **ALTER COLUMN 不被支援**
  - 症狀：`near "ALTER": syntax error`，或 migration 失敗。
  - 原因：SQLite 不能直接改欄位型別／約束。
  - 修法：重建表流程（見 migration 工具節）；EF Core 讓其自動產生重建步驟，並檢視產出的 SQL。
- **型別沒被強制**
  - 症狀：INTEGER 欄位存進了字串，不報錯。
  - 原因：動態型別。
  - 修法：新表加 `STRICT`，或加 `CHECK (typeof(col) = 'integer')`。
- **金額小數誤差**
  - 症狀：`decimal` 欄位加總有浮點誤差，EF Core 排序報錯。
  - 原因：無真正定點型別。
  - 修法：金額以最小單位整數儲存（分），應用層轉換。
- **ID 被重用**
  - 症狀：刪除最後一筆後新增，拿到相同 id，外部引用錯指。
  - 原因：`INTEGER PRIMARY KEY` 無 AUTOINCREMENT 時取 max+1。
  - 修法：需要單調遞增時加 `AUTOINCREMENT`，或改用 UUID。
- **LIKE 對中文／非 ASCII 不分大小寫失效**
  - 症狀：`LIKE` 對非 ASCII 字母仍分大小寫。
  - 原因：內建 `NOCASE`／`LIKE` 僅處理 ASCII。
  - 修法：應用層正規化後比對，或載入 ICU 擴充。
