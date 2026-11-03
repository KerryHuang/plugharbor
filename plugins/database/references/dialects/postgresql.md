> 未實戰驗證：本附錄依官方文件整理，尚未在實際專案驗證。

# PostgreSQL 方言附錄

適用：連線字串含 `Host=`／`postgres://`／`postgresql://`；csproj 有 `Npgsql.EntityFrameworkCore.PostgreSQL`；docker-compose image 為 `postgres`。

## 型別對照

| 概念 | PostgreSQL | SQL Server | MySQL | SQLite |
|---|---|---|---|---|
| 32 位元整數 | `integer` | `int` | `int` | `INTEGER` |
| 64 位元整數 | `bigint` | `bigint` | `bigint` | `INTEGER` |
| 布林 | `boolean` | `bit` | `tinyint(1)` | `INTEGER` |
| 定點小數 | `numeric(p,s)` | `decimal(p,s)` | `decimal(p,s)` | `NUMERIC` |
| 字串 | `text`／`varchar(n)`（皆 Unicode，依資料庫編碼） | `nvarchar(n)` | `varchar(n)` | `TEXT` |
| 日期時間 | `timestamptz`（建議）／`timestamp` | `datetime2`／`datetimeoffset` | `datetime(6)` | `TEXT` |
| GUID | `uuid` | `uniqueidentifier` | `char(36)` | `TEXT` |
| 二進位 | `bytea` | `varbinary(max)` | `blob` | `BLOB` |
| JSON | `jsonb`（可索引，優先於 `json`） | `nvarchar(max)` | `json` | `TEXT` |

PostgreSQL 的 `text` 與 `varchar(n)` 效能無差異；沒有業務上限就用 `text`。另有 `array`、`enum`、`range`、`inet` 等原生型別。

## 識別欄／自動遞增

- 建議 `integer GENERATED ALWAYS AS IDENTITY`（SQL 標準，PG 10+）；`serial` 是舊寫法（背後建 sequence），新專案避免。
- 大表用 `bigint GENERATED ALWAYS AS IDENTITY`。
- `GENERATED ALWAYS` 不能直接 INSERT 值，除非 `OVERRIDING SYSTEM VALUE`；`BY DEFAULT` 則允許。
- 取回新 id：`INSERT ... RETURNING id`。
- 匯入資料後 sequence 不會自動前進：`SELECT setval(pg_get_serial_sequence('t','id'), (SELECT max(id) FROM t));`。

## 分頁

```sql
SELECT ... FROM sales.orders
ORDER BY created_at DESC, order_id DESC
LIMIT :take OFFSET :skip;
```

深分頁改 keyset：`WHERE (created_at, order_id) < (:last_at, :last_id)`（PG 支援 row value 比較）。

## 命名慣例與大小寫

- 未加雙引號的識別字會被折成小寫；慣例用 `snake_case` 且不加引號（`order_item`、`created_at`）。
- 一旦用雙引號建立大小寫混合名稱（`"OrderItem"`），之後所有查詢都得加引號；EF Core 搭配 `UseSnakeCaseNamingConvention()`（EFCore.NamingConventions）可避免。
- 約束命名：`pk_table`、`fk_child_parent`、`uq_table_col`、`ix_table_col`、`ck_table_rule`。
- 識別字長度上限 63 bytes，超過會被靜默截斷。
- 字串比較預設分大小寫；不分大小寫用 `ILIKE`、`citext` 擴充或 `lower()` 函式索引。

## 預設值與約束

```sql
created_at timestamptz NOT NULL DEFAULT now(),
deleted    boolean     NOT NULL DEFAULT false,
CONSTRAINT ck_order_qty CHECK (qty >= 0),
CONSTRAINT fk_order_customer FOREIGN KEY (customer_id) REFERENCES sales.customer (customer_id)
```

- 部分唯一索引做軟刪除下的唯一：`CREATE UNIQUE INDEX uq_user_email ON app_user (email) WHERE NOT deleted;`。
- 大表加 NOT NULL 欄位且有常數預設值時，PG 11+ 不重寫整表；volatile 預設值（如 `now()`）仍會重寫。
- `CREATE INDEX CONCURRENTLY` 避免鎖表（不能在交易內執行）。

## 日期時間與時區

- `timestamptz` 內部存 UTC，輸出依 session `TimeZone` 轉換；`timestamp` 不含時區，容易混淆。建議一律 `timestamptz`。
- Npgsql 6+ 預設：`DateTime` Kind=Utc 才能寫入 `timestamptz`，Kind=Unspecified／Local 會丟例外。
- 時區轉換：`ts AT TIME ZONE 'Asia/Taipei'`（用 IANA 名稱）。
- 區間用半開區間 `>= :from AND < :to`。

## 說明（comment／extended property）怎麼寫

```sql
COMMENT ON TABLE sales.orders IS '銷售訂單';
COMMENT ON COLUMN sales.orders.order_id IS '訂單編號';
COMMENT ON VIEW sales.sales_order_view IS '訂單檢視';
```

查詢：`obj_description('sales.orders'::regclass)`、`col_description('sales.orders'::regclass, 1)`。

## migration 工具

- EF Core：見 `${CLAUDE_PLUGIN_ROOT}/references/orm/ef-core.md`（provider `Npgsql.EntityFrameworkCore.PostgreSQL`）。
- 其他：Flyway、Liquibase、sqitch、golang-migrate、Alembic（Python）、Prisma Migrate、Rails／Django migrations。
- 腳本冪等：`CREATE TABLE IF NOT EXISTS`、`ALTER TABLE ... ADD COLUMN IF NOT EXISTS`、`CREATE OR REPLACE VIEW`（只能追加欄位在尾端，不能改既有欄位型別或順序，否則先 `DROP VIEW`）。
- PG 的 DDL 可交易：整個 migration 包在 `BEGIN; ... COMMIT;`，失敗自動回滾（SQL Server 與 MySQL 做不到完全一樣）。

## Table 與 View 寫法要點

```sql
CREATE TABLE production.workstation (
    workstation_id   integer GENERATED ALWAYS AS IDENTITY,
    workstation_code varchar(20) NOT NULL,
    created_at       timestamptz NOT NULL DEFAULT now(),
    modified_at      timestamptz,
    deleted          boolean NOT NULL DEFAULT false,
    CONSTRAINT pk_workstation PRIMARY KEY (workstation_id)
);

CREATE OR REPLACE VIEW sales.sales_order_view AS
SELECT o.order_no AS order_id,   -- 訂單編號
       c.name     AS customer_name
FROM sales.orders o
LEFT JOIN sales.customer c ON c.customer_id = o.customer_id;
```

PG 讀取不會被寫入阻擋（MVCC），view 不需要也沒有 `NOLOCK` 類 hint。

## View 計算欄位關鍵字（供 schema-docs 解析）

`CASE WHEN`、`COALESCE(`、`NULLIF(`、`CAST(`／`::`、`age(`、`date_trunc(`、`extract(`、`EXISTS (`。布林計算欄位多為 `(expr) AS is_xxx` 或 `CASE WHEN ... THEN true ELSE false END`，計算邏輯取條件式。

## 常見坑

- **relation "xxx" does not exist**
  - 症狀：明明有表卻查不到。
  - 原因：建表時用了雙引號大小寫混合名稱，查詢卻沒加引號；或 `search_path` 未含該 schema。
  - 修法：統一 snake_case 不加引號；跨 schema 寫全名 `schema.table`，或設定 `search_path`。
- **Npgsql 拒絕寫入 DateTime**
  - 症狀：`Cannot write DateTime with Kind=Local to PostgreSQL type 'timestamp with time zone'`。
  - 原因：Npgsql 6+ 嚴格區分 Kind。
  - 修法：寫入前轉 UTC（`ToUniversalTime()`／`DateTime.SpecifyKind`）；不建議開 `Npgsql.EnableLegacyTimestampBehavior`。
- **匯入後主鍵衝突**
  - 症狀：`duplicate key value violates unique constraint "xxx_pkey"`。
  - 原因：手動或批次插入指定了 id，identity／sequence 沒前進。
  - 修法：`setval` 把 sequence 調到 `max(id)`。
- **migration 中 CREATE INDEX CONCURRENTLY 失敗**
  - 症狀：`CREATE INDEX CONCURRENTLY cannot run inside a transaction block`。
  - 原因：migration 工具預設包交易。
  - 修法：EF Core 用 `migrationBuilder.Sql("...", suppressTransaction: true)`；其他工具用其「不包交易」標記。
- **識別字被截斷**
  - 症狀：兩個長約束名稱衝突或與預期不符。
  - 原因：識別字上限 63 bytes（中文每字 3 bytes），超過靜默截斷。
  - 修法：縮短名稱，表與約束名用英文。
- **LIKE 找不到不同大小寫**
  - 症狀：`WHERE name LIKE 'abc%'` 漏掉 `ABC`。
  - 原因：PG 字串比較預設分大小寫。
  - 修法：`ILIKE`，或對 `lower(name)` 建函式索引，或 `citext`。
