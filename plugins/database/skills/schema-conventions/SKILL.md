---
name: schema-conventions
description: 撰寫或審查資料表（CREATE TABLE）與檢視表（CREATE VIEW）腳本的慣例——檔案結構、命名、主鍵、稽核欄、軟刪除、約束、view 撰寫原則；方言差異走附錄（附 SQL Server、PostgreSQL、MySQL、SQLite）。Use when writing or reviewing table／view DDL, "資料表慣例", "table 命名規則", "怎麼建表", "view 慣例", "檢視表怎麼寫", "schema convention", "table convention", "view convention".
triggers: ["怎麼建表", "資料表慣例", "table 命名", "CREATE TABLE"]
---

# Schema 撰寫慣例（table／view）

一套可調整的慣例框架。專案若已有自訂標準，以專案標準為準；沒有時沿用本文預設。語法細節（型別、識別欄、預設值、註解）一律看方言附錄。

## 0. 偵測技術棧與附錄

先看專案的 DB 連線字串（appsettings、`.env`、docker-compose）、`*.csproj` 的 provider 套件、migration 目錄、既有 `Table/**/*.sql`，對照下表載入附錄，並在回報第一行寫「附錄：<檔名>」。

| 偵測到 | 附錄 |
|---|---|
| `Server=`／`Data Source=` 加 `Initial Catalog`、`Microsoft.EntityFrameworkCore.SqlServer`、mssql image | `${CLAUDE_PLUGIN_ROOT}/references/dialects/sqlserver.md` |
| `Host=`、`postgres://`、`Npgsql`、postgres image | `${CLAUDE_PLUGIN_ROOT}/references/dialects/postgresql.md` |
| `mysql://`、`Uid=`、`Pomelo`／`MySql`、mysql／mariadb image | `${CLAUDE_PLUGIN_ROOT}/references/dialects/mysql.md` |
| `.db`／`.sqlite`、`Data Source=*.db`、`Microsoft.EntityFrameworkCore.Sqlite` | `${CLAUDE_PLUGIN_ROOT}/references/dialects/sqlite.md` |

沒有對應附錄（例如 Oracle）：照本 skill 的通用方法，加上專案既有程式的寫法（先找 2–3 個同類檔當樣板；有裝 workspace 就照 `workspace:convention-first`（可選））。做完問使用者要不要把這次的寫法整理成新附錄 `references/dialects/<方言>.md`，回報寫「附錄：無（照既有程式）」。

postgresql／mysql／sqlite 附錄標有「未實戰驗證」，依其建議寫完要在測試環境跑過再交。

## 1. 動手前

1. 找 2–3 張既有同類 table／view 當樣板，沿用其命名與排版。
2. 判斷這張表是本專案自建（維護 desired-state 的 `CREATE TABLE` 檔），還是外部／legacy 系統帶入（改動走 Alter 腳本，不改原 desired-state）。
3. 讀附錄「型別對照」「識別欄」「命名慣例與大小寫」三節。

## 2. Table 慣例

- **檔案結構**：一表一檔，放 `Table/**/*.sql`（或專案既有位置）；使用完整限定名（含 schema，若方言支援）；主鍵用具名約束。範例見附錄「Table 檔案結構與範例」。
- **欄位命名**：整個專案單一風格（PascalCase 或 snake_case，依方言附錄與既有程式）；不用保留字、不用縮寫混搭。
- **主鍵**：命名 `{TableName}Id`（或 `{table_name}_id`），整數自動遞增（寫法依方言）；預期筆數超過約 20 億用 64 位元。複合主鍵僅用於純關聯表。
- **稽核欄**：`CreatedDate`、`ModifiedDate`（高精度日期時間，統一存 UTC）；需追蹤人時加 `CreatedBy`、`ModifiedBy`。
- **軟刪除**：`DeleteFlag`（布林 NOT NULL，預設 false）；唯一性約束需考慮軟刪除（部分唯一索引或把 DeleteFlag 納入鍵）。
- **約束**：PK／FK／UNIQUE／CHECK／DEFAULT 一律具名，前綴統一（`PK_`、`FK_`、`UQ_`、`IX_`、`DF_`、`CK_`）；外鍵欄位建索引。
- **NOT NULL 優先**：可為空要有業務理由；對既有表新增 NOT NULL 欄要給預設值或分步回填。
- **說明**：每張表、每個欄位都寫說明（寫法依方言附錄「說明」節）。
- **Alter 腳本**：位於 `Table/Alter/`，命名 `{來源資料表}_{YYYYMMDD}.sql`，只用於修改非本專案 desired-state 管控的表；本專案自建的表直接改 desired-state 檔並透過 migration 發佈。

## 3. View 慣例

- **語法**：用該方言的「可重複執行」建立方式（`CREATE OR ALTER`／`CREATE OR REPLACE`；SQLite 先 `DROP VIEW IF EXISTS`），見附錄。
- **SELECT 欄位格式**：第一個欄位前不加逗號，後續欄位逗號開頭（`,欄位 AS 英文名`），diff 乾淨；一律 `AS` 映射成專案統一的英文名稱；用分類註解（`-- 訂單`、`-- 時間`）分組。
- **行末註解**：`-- 中文說明 (原始欄位) [關聯表] {選項值}`——這是 `schema-docs` 的解析來源，格式要穩定。
- **JOIN**：優先 `LEFT JOIN`；JOIN 行末註解關聯表用途；讀取隔離 hint（如 SQL Server 的 `NOLOCK`）依附錄，不在通用層預設使用。
- **命名**：PascalCase 加 `View` 後綴（或對應 snake_case `_view`）；schema 對應領域（Sales、Production…，方言不支援 schema 時用表名前綴）。
- **計算欄位**：把業務規則寫在 view 裡時，註解說明計算邏輯；避免在 view 內做昂貴的非 sargable 運算或巢狀 view 超過兩層。

## 4. 安全規則（通用）

- **唯讀優先**：查資料一律 SELECT；有唯讀工具就走唯讀工具。驗 DDL 語法不要丟給查詢工具（「唯讀」工具對含 DDL 的批次不一定真唯讀），只送純 SELECT。
- **DDL 前確認備份存在且可還原**，先在測試環境彩排；正式環境非必要不查，必查先告知並取得同意。
- **大量異動分批**：大量 UPDATE／DELETE 分批執行，每批獨立交易，避免交易記錄或鎖暴漲。
- 破壞性操作（DROP、TRUNCATE、無 WHERE 的 UPDATE／DELETE）先列出影響範圍，取得使用者同意。

## 5. 自我檢查

- [ ] 命名、型別、識別欄符合附錄與既有樣板
- [ ] 主鍵、稽核欄、軟刪除欄齊全，約束具名
- [ ] 表與欄位都有說明
- [ ] View 欄位註解格式符合 `schema-docs` 解析規則
- [ ] DDL 已在測試環境執行成功（或標「未驗證」）
- [ ] 若要發佈到既有環境：走 `migration` skill
