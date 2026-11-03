# database

資料庫能力 plugin：schema 撰寫慣例、migration 流程與疑難排解、DB schema 與 ORM entity 同步、資料表說明文件。SKILL.md 寫不綁技術的通用方法，方言與 ORM 工具的寫法放附錄。

## 定位

`[database]` 換資料庫或 ORM 只要補一份附錄。自 `database-sqlserver` 改寫而來。

## 技術棧附錄

| 附錄 | 狀態 | 內容 |
|---|---|---|
| `references/dialects/sqlserver.md` | 實戰驗證 | SQL Server 型別、IDENTITY、分頁、extended property、常見坑 |
| `references/dialects/postgresql.md` | 未實戰驗證 | 依官方文件整理 |
| `references/dialects/mysql.md` | 未實戰驗證 | 依官方文件整理 |
| `references/dialects/sqlite.md` | 未實戰驗證 | 依官方文件整理 |
| `references/orm/ef-core.md` | 實戰驗證 | EF Core migration、efcpt scaffold、診斷指令 |

每個 skill 開頭先偵測連線字串、provider 套件、migration 目錄，載入對應附錄並在回報第一行標「附錄：<檔名>」。沒有對應附錄時照通用方法加專案既有寫法，做完詢問是否整理成新附錄。

## Skills（4）

| Skill | 用途 |
|---|---|
| `schema-conventions` | table／view 撰寫慣例（命名、主鍵、稽核欄、約束、view 原則） |
| `migration` | migration 建立、審查、套用、回滾、失敗修復與特殊情境診斷 |
| `orm-sync` | DB schema 與 ORM entity 同步（DB-first、efcpt） |
| `schema-docs` | 由 view 產生資料表結構說明文件 |

## 安全規則

唯讀優先、DDL 前確認備份並先在測試環境彩排、大量異動分批、正式環境非必要不查。

## License

MIT
