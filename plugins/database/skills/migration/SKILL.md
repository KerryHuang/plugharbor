---
name: migration
description: 資料庫 migration 全流程——建立、審查產生的 SQL、套用、回滾、失敗修復、切換目標資料庫，以及特殊情境診斷（snapshot 衝突、歷史紀錄遺失、緊急回滾）；方言走 dialects 附錄，工具走 ORM 附錄（附 EF Core）。Use when 建 migration, 套用 migration, 回滾 migration, migration 失敗, dotnet ef, snapshot 衝突, "migration 對不上", "緊急回滾", "migration 診斷", "create migration", "apply migration", "rollback".
---

# Migration 流程與疑難排解

通用流程寫在本文；指令與語法在附錄。本 skill 涵蓋「一般流程」與「特殊診斷」兩部分。

## 0. 偵測技術棧與附錄

先看專案的 `*.csproj`／`package.json`／`pyproject.toml`／`go.mod`、migration 目錄（`Migrations/`、`db/migrate/`、`alembic/`、`prisma/migrations/`）、DB 連線字串，對照下表載入附錄，並在回報第一行寫「附錄：<檔名>」。需同時載入「方言」與「ORM／工具」兩份。

| 偵測到 | 附錄 |
|---|---|
| `Microsoft.EntityFrameworkCore*`、`Migrations/*ModelSnapshot.cs` | `${CLAUDE_PLUGIN_ROOT}/references/orm/ef-core.md` |
| SQL Server（`Server=`＋`Initial Catalog`、`EntityFrameworkCore.SqlServer`） | `${CLAUDE_PLUGIN_ROOT}/references/dialects/sqlserver.md` |
| PostgreSQL（`Host=`、`postgres://`、`Npgsql`） | `${CLAUDE_PLUGIN_ROOT}/references/dialects/postgresql.md` |
| MySQL（`mysql://`、`Uid=`、`Pomelo`） | `${CLAUDE_PLUGIN_ROOT}/references/dialects/mysql.md` |
| SQLite（`.db`／`.sqlite`、`EntityFrameworkCore.Sqlite`） | `${CLAUDE_PLUGIN_ROOT}/references/dialects/sqlite.md` |

沒有對應附錄（例如 Flyway、Alembic、Prisma 等非 EF 工具）：照本 skill 的通用方法，加上專案既有程式的寫法（先看 2–3 個既有 migration 當樣板；有裝 workspace 就照 `workspace:convention-first`（可選））。做完問使用者要不要把這次的寫法整理成新附錄 `references/orm/<工具>.md`，回報寫「附錄：無（照既有程式）」。

postgresql／mysql／sqlite 附錄標有「未實戰驗證」，在測試環境跑過再往上推。

## 1. 安全規則（通用，先於一切操作）

- **唯讀優先**：先用唯讀方式確認目標資料庫與目前 migration 狀態，再決定動作。
- **目標環境確認**：任何套用／回滾前，向使用者顯示目標 Host／Database 並取得確認；正式環境非必要不連，必連先告知並取得同意。
- **DDL 前確認備份存在且可還原**，先在測試環境彩排整條 migration（含 Down）。
- **大量資料異動分批**：資料回填、大量 UPDATE／DELETE 分批，每批獨立交易，避免交易記錄暴漲；SIMPLE 復原模式也一樣。
- **預設不動既有 migration**：變更 schema 永遠新增一筆 migration。

## 2. 一般流程

1. **建置專案**：確認編譯通過。
2. **順序前置檢查**：確認新 migration 的排序（時間戳或序號）晚於遠端分支最新的 migration；落後先 rebase／pull（指令見 ORM 附錄）。建置通過不證明順序正確。
3. **建立**：用工具產生，名稱描述意圖（`Add{Entity}Table`、`Alter{Entity}{Field}`、`Add{Entity}{Index}Index`）。產生後確認新檔是清單最後一筆。
4. **審查產生的內容**：讀 `Up()`／`Down()`（或 SQL）。重點：
   - 有無非預期的 DROP／資料遺失（欄位改名被產成 drop＋add）。
   - 新增 NOT NULL 欄是否有預設值或回填。
   - 對大表是否會長時間鎖表。
   - Down 是否真的可逆。
5. **產生 SQL 腳本審查**：增量腳本給人看；生產部署用冪等腳本（指令見 ORM 附錄）。
6. **套用**：先測試環境，再依環境逐級往上；套用後驗證資料庫狀態（目前版本、表結構）。
7. **回報連線資訊**：每次 migration 操作（建立／套用／回復／列出）後，向使用者回報目前資料庫連線（Host、Port、Database、User；**密碼遮蔽**）與資訊來源（CLI 參數、環境變數、工具輸出、設定檔）；來源不確定標 `[推論]`。

## 3. 既有 migration 的保護（高風險，動手前必先確認）

| 編輯目標 | 必先動作 |
|---|---|
| 重新命名 migration 檔（改時間戳或序號） | 必先確認，附理由與對歷史紀錄表的影響評估 |
| 刪除已存在的 migration | 必先確認；已合併進共用分支者**禁止**刪，改新增反向 migration（`Revert{Name}`） |
| 修改既有 migration 的 Up／Down | 必先確認；已 deploy 到任何環境者改走第 5 節診斷 |
| 手動補歷史紀錄表的 row | **禁止**自動執行，須使用者明示授權 |

## 4. 失敗修復循環

migration 套用失敗：讀錯誤 → 定位 migration 檔 → 直接修該檔 → 重跑套用（多數工具從失敗點繼續）→ 再失敗再修。**不用 remove／rollback 重來**，除非確認該 migration 尚未套用到任何環境。

方言相關的常見錯誤（DDL 後接 DML 編譯錯誤、缺舊表、交易行為差異）查方言附錄的 `## 常見坑`。DDL 是否可交易、失敗會不會留下半套結構，也看方言附錄。

## 5. 特殊情境診斷

| 症狀 | 可能原因 | 做法 |
|---|---|---|
| 無法建立 migration | 專案建置失敗 | 先修建置 |
| 套用失敗 | SQL 錯誤 | 以詳細模式重跑看實際 SQL |
| snapshot／模型快照衝突 | 多人並行開發 | 檢查 git 衝突 |
| 資料庫狀態不明 | 手動改過資料庫 | 列出 migration 與歷史紀錄表比對 |
| log 顯示連錯主機 | 連線參數／環境變數設錯 | 檢查連線注入來源 |

具體指令（快照衝突的重建步驟、「資料庫已套用但 migration 遺失」的空 migration 同步法）見 ORM 附錄的「診斷情境指令」。

### 生產緊急回滾檢查清單

- [ ] 確認回滾版本的 Down 正確
- [ ] 產生回滾 SQL 腳本並審查
- [ ] 備份資料庫
- [ ] 測試環境驗證回滾
- [ ] 通知相關團隊
- [ ] 記錄事故報告

## 6. 自我檢查

- [ ] 附錄已載入並標註
- [ ] 目標環境已向使用者確認，備份存在
- [ ] 新 migration 排序晚於遠端最新
- [ ] Up／Down／產生的 SQL 已審查，無非預期 DROP
- [ ] 套用後驗證了資料庫狀態並回報連線資訊（密碼遮蔽）
- [ ] 回報分開宣稱：產生、測試環境套用、正式環境套用各自的結果，沒跑到的標「未驗證」
- [ ] 需要同步 ORM entity：接 `orm-sync`
