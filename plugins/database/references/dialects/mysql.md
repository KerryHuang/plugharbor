> 未實戰驗證：本附錄依官方文件整理，尚未在實際專案驗證。

# MySQL 方言附錄

適用：連線字串含 `mysql://`／`Uid=`／`Server=...;Port=3306`；csproj 有 `Pomelo.EntityFrameworkCore.MySql` 或 `MySql.EntityFrameworkCore`；docker-compose image 為 `mysql`／`mariadb`。MariaDB 大致相容，差異處另註。

## 型別對照

| 概念 | MySQL | SQL Server | PostgreSQL | SQLite |
|---|---|---|---|---|
| 32 位元整數 | `int` | `int` | `integer` | `INTEGER` |
| 64 位元整數 | `bigint` | `bigint` | `bigint` | `INTEGER` |
| 布林 | `tinyint(1)`（`boolean` 別名） | `bit` | `boolean` | `INTEGER` |
| 定點小數 | `decimal(p,s)` | `decimal(p,s)` | `numeric(p,s)` | `NUMERIC` |
| 字串 | `varchar(n)`／`text`（字元集 utf8mb4） | `nvarchar(n)` | `varchar(n)`／`text` | `TEXT` |
| 日期時間 | `datetime(6)`／`timestamp(6)` | `datetime2` | `timestamptz` | `TEXT` |
| GUID | `char(36)`／`binary(16)` | `uniqueidentifier` | `uuid` | `TEXT` |
| 二進位 | `blob`／`longblob` | `varbinary(max)` | `bytea` | `BLOB` |
| JSON | `json` | `nvarchar(max)` | `jsonb` | `TEXT` |

注意：字元集必須用 `utf8mb4`（`utf8` 在 MySQL 是 3 bytes 閹割版，存不了 emoji 與部分漢字）；`varchar(n)` 的 n 是字元數，但整列有 65535 bytes 上限；`datetime` 預設無小數秒，要寫 `datetime(6)`。

## 識別欄／自動遞增

- `int NOT NULL AUTO_INCREMENT`，必須是索引（通常是主鍵）；大表用 `bigint`。
- 取回新 id：`LAST_INSERT_ID()`（連線層級）。
- 交易回滾或 INSERT 失敗會留下跳號，InnoDB 不保證連續。
- 伺服器重啟後 AUTO_INCREMENT 計數器在 8.0 之前會重算為 `max+1`，8.0 起持久化。

## 分頁

```sql
SELECT ... FROM orders
ORDER BY created_at DESC, order_id DESC
LIMIT 20 OFFSET 40;      -- 或 LIMIT 40, 20
```

深分頁改 keyset：`WHERE (created_at, order_id) < (?, ?)`，或 `created_at < ? OR (created_at = ? AND order_id < ?)`。

## 命名慣例與大小寫

- 慣例 `snake_case`，以反引號 `` ` `` 括起（保留字時才必要）。
- 資料表名稱是否分大小寫取決於作業系統與 `lower_case_table_names`：Linux 預設分、Windows 不分、macOS 預設不分。跨平台一律全小寫。
- 欄位名、索引名不分大小寫。
- 約束命名：`pk_`／`fk_child_parent`／`uq_table_col`／`ix_table_col`／`ck_table_rule`。注意 MySQL 的 PRIMARY KEY 名稱固定為 `PRIMARY`。
- 字串比較由 collation 決定（`utf8mb4_0900_ai_ci` 不分大小寫與重音；`_bin` 分）。

## 預設值與約束

```sql
created_at datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
modified_at datetime(6) NULL ON UPDATE CURRENT_TIMESTAMP(6),
deleted tinyint(1) NOT NULL DEFAULT 0,
CONSTRAINT ck_order_qty CHECK (qty >= 0),
CONSTRAINT fk_order_customer FOREIGN KEY (customer_id) REFERENCES customer (customer_id)
```

- 引擎用 InnoDB（有交易與外鍵）；MyISAM 不支援外鍵。
- `CHECK` 約束 8.0.16 起才真的執行（之前語法接受但忽略）。
- 預設值為運算式需括號：`DEFAULT (uuid())`（8.0.13+）。
- 索引 key 長度限制：utf8mb4 下 `varchar(255)` 約 1020 bytes，單欄索引上限 3072 bytes。

## 日期時間與時區

- `datetime` 不轉時區；`timestamp` 以 UTC 儲存並依 session `time_zone` 轉換，範圍只到 2038-01-19。
- 建議：存 UTC，用 `datetime(6)`，應用程式端負責轉換；或連線字串固定 session 時區。
- 時區名稱轉換（`CONVERT_TZ(dt,'UTC','Asia/Taipei')`）需先載入 time zone tables（`mysql_tzinfo_to_sql`）。
- 區間用半開區間。

## 說明（comment／extended property）怎麼寫

```sql
CREATE TABLE workstation (
    workstation_id int NOT NULL AUTO_INCREMENT COMMENT '工作站編號',
    workstation_code varchar(20) NOT NULL COMMENT '工作站代碼',
    PRIMARY KEY (workstation_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工作站';

ALTER TABLE workstation COMMENT = '工作站（新說明）';
ALTER TABLE workstation MODIFY workstation_code varchar(20) NOT NULL COMMENT '新說明';  -- 改欄位說明得重述完整欄位定義
```

查詢：`information_schema.COLUMNS.COLUMN_COMMENT`、`SHOW FULL COLUMNS FROM workstation`。View 沒有 comment 語法，說明寫在 SELECT 行末註解。

## migration 工具

- EF Core：見 `${CLAUDE_PLUGIN_ROOT}/references/orm/ef-core.md`（Pomelo provider；`UseMySql(conn, ServerVersion.AutoDetect(conn))`）。
- 其他：Flyway、Liquibase、gh-ost／pt-online-schema-change（大表線上改結構）、Alembic、Prisma、Rails／Django migrations。
- **DDL 會隱式 commit**，無法包在交易內回滾；migration 失敗可能停在半途，需手動補修。
- 腳本冪等：`CREATE TABLE IF NOT EXISTS`；`ADD COLUMN IF NOT EXISTS` 僅 MariaDB 支援，MySQL 要查 `information_schema`。
- 8.0 的 `ALGORITHM=INSTANT`／`INPLACE` 可降低大表改結構鎖定。

## Table 與 View 寫法要點

```sql
CREATE TABLE production_workstation (
    workstation_id   int NOT NULL AUTO_INCREMENT,
    workstation_code varchar(20) NOT NULL,
    created_at       datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    modified_at      datetime(6) NULL,
    deleted          tinyint(1) NOT NULL DEFAULT 0,
    PRIMARY KEY (workstation_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE OR REPLACE VIEW sales_order_view AS
SELECT o.order_no AS order_id,   -- 訂單編號
       c.name     AS customer_name
FROM orders o
LEFT JOIN customer c ON c.customer_id = o.customer_id;
```

MySQL 沒有 schema 與 database 之分（schema 即 database）；原本 SQL Server 的 Schema 領域分組改用表名前綴。InnoDB 為 MVCC，不需 `NOLOCK` hint。

## View 計算欄位關鍵字（供 schema-docs 解析）

`CASE WHEN`、`IF(`、`IFNULL(`、`COALESCE(`、`DATEDIFF(`、`TIMESTAMPDIFF(`、`CAST(`。布林計算欄位常為 `IF(cond,1,0)` 或 `(cond)`，計算邏輯取條件式。

## 常見坑

- **中文／emoji 變問號或寫入失敗**
  - 症狀：`Incorrect string value: '\xF0\x9F...'`。
  - 原因：資料庫、表或連線字元集為 `utf8`（3 bytes）或 `latin1`。
  - 修法：資料庫與表用 `utf8mb4`，連線字串加 `CharSet=utf8mb4`。
- **大小寫導致換平台後找不到表**
  - 症狀：Windows／macOS 正常，Linux 部署 `Table 'x' doesn't exist`。
  - 原因：Linux 表名分大小寫。
  - 修法：全小寫 snake_case；不要在執行中修改 `lower_case_table_names`。
- **migration 失敗留下半套結構**
  - 症狀：重跑 migration 報 `Table already exists` 或 `Duplicate column name`。
  - 原因：DDL 隱式 commit，失敗前的語句已生效。
  - 修法：手動補完或還原到失敗前，再重跑；腳本盡量一個 migration 只做一件事。
- **Specified key was too long**
  - 症狀：建索引報 `Specified key was too long; max key length is 3072 bytes`。
  - 原因：utf8mb4 每字元 4 bytes，長 varchar 做索引超限。
  - 修法：縮短欄位、改前綴索引 `(col(191))`，或改存雜湊欄位建索引。
- **timestamp 超出範圍**
  - 症狀：寫入 2038 年後日期失敗或被改成 0。
  - 原因：`timestamp` 範圍到 2038-01-19。
  - 修法：改用 `datetime(6)`。
- **GROUP BY 報 only_full_group_by**
  - 症狀：`SELECT list is not in GROUP BY clause`。
  - 原因：5.7+ 預設 `ONLY_FULL_GROUP_BY`。
  - 修法：把非聚合欄位加進 GROUP BY 或用 `ANY_VALUE()`，不要關掉 sql_mode。
- **tinyint(1) 被當數字**
  - 症狀：布林欄位出現 2、-1 之類值或 ORM 對映成 sbyte。
  - 原因：`tinyint(1)` 只是慣例，不限制值域。
  - 修法：加 `CHECK (col IN (0,1))`；ORM 明確指定 bool 對映。
