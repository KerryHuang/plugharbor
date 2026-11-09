---
name: orm-sync
description: 讓 ORM entity 與資料庫 schema 保持同步（DB-first）——加新表／view、從資料庫重新產生 entity、修正 precision／nullable／長度與實際 schema 的偏差；附 EF Core Power Tools（efcpt）流程。Use when 加表, 同步 Entity, scaffold, efcpt, 更新實體, re-scaffold, 重新產生 Entity, "DB schema 同步到 ORM", "entity 欄位型別跟資料庫不一致", or when a file with an "auto generated" header must be changed (手改會被覆蓋).
triggers: ["同步 Entity", "re-scaffold", "efcpt", "重新產生 Entity"]
---

# DB schema ↔ ORM entity 同步

**核心原則**：Entity 是資料庫 schema 的鏡射。修 precision／nullable／長度偏差，不手改自動產生的檔（下次 scaffold 會覆蓋），一律回到產生工具重新產生。

## 0. 偵測技術棧與附錄

先看專案的 `*.csproj`／`package.json`／`pyproject.toml`、產生工具設定檔（`efcpt-config.json`、`efpt.config.json`、`prisma/schema.prisma`、`sqlacodegen` 設定）、DB 連線字串，對照下表載入附錄，並在回報第一行寫「附錄：<檔名>」。

| 偵測到 | 附錄 |
|---|---|
| `Microsoft.EntityFrameworkCore*`、`efcpt-config.json`／`efpt.config.json`、自動產生檔頭 `EF Core Power Tools` | `${CLAUDE_PLUGIN_ROOT}/references/orm/ef-core.md`（「efcpt scaffold」一節） |
| SQL Server／PostgreSQL／MySQL／SQLite 連線線索 | `${CLAUDE_PLUGIN_ROOT}/references/dialects/<sqlserver｜postgresql｜mysql｜sqlite>.md`（型別對照、連線字串、常見坑） |

沒有對應附錄（Prisma、SQLAlchemy、TypeORM 等）：照本 skill 的通用流程，加上專案既有程式的寫法（先找 2–3 個既有 entity 當樣板；有裝 workspace 就照 `workspace:convention-first`（可選））。做完問使用者要不要把這次的寫法整理成新附錄 `references/orm/<工具>.md`，回報寫「附錄：無（照既有程式）」。

## 1. DB-first 順序（絕不 migration-first）

本次變更需要新增或改 schema（新表、加欄、view 改名、型別變）時，照順序：

1. **先讓來源資料庫具備目標 schema**；
2. **重新 scaffold／產生 entity**；
3. **才建 migration**（接 `migration` skill）。

migration-first 的兩個坑：

- 產生工具從尚未更新的資料庫讀，產出舊欄位名／型別（改名沒生效）。
- 改名後 model 與 migration-first 當下的 snapshot 漂移，之後建 migration 會吸入髒 snapshot。

若專案的 reverse-engineer 來源是獨立的「設計庫／參考庫」（與 runtime／app DB 不同連線），要先在那個庫套用 schema 變更（並備妥 rollback plan），再 scaffold。設計庫已有目標 schema、只是 re-scaffold，直接走第 2 節。

## 2. 流程

1. **偵測設定檔狀態**：產生工具若有多份設定（如 efcpt 的 GUI／CLI 雙 config），確認齊全且表清單一致；缺的補齊（細節見 ORM 附錄）。
2. **確認目標**：向使用者確認要新增／同步的表或 view（含 schema 名）與類型；用你慣用的 DB 查詢工具（唯讀）確認表存在且欄位、型別、nullable 正確。
3. **取得 reverse-engineer 來源連線**：連線字串**絕不寫入設定檔或 commit**，只在記憶體或 shell 變數；不確定連的是 runtime 庫還是設計庫就問。
4. **更新設定的表清單**：所有設定檔同步新增，排序規則一致（按 schema 分組、組內字母序）。
5. **執行產生工具**：先確認工具版本與專案 ORM 版本一致（版本不符會造成屬性命名差異、build 失敗）。
6. **檢查產出**：新增的 entity、configuration、context 註冊是否如預期；`git diff --stat` 確認除預期檔案外，**既有檔案零差異**（已存在的 entity 有手動修改的要先備份）。
7. **建置驗證**：專案 build 通過。
8. **建 migration**：接 `migration` skill。

## 3. Red Flags

| 想法 | 現實 |
|---|---|
| 「用 ORM 內建的 scaffold 指令就好」 | 要用專案約定的產生工具，才讀得到設定與模板 |
| 「只改一份設定就好」 | 多份設定檔的表清單必須同步 |
| 「裝最新版工具就好」 | 工具版本要與專案 ORM 版本一致 |
| 「連線字串寫進設定檔」 | 禁止，僅在記憶體或 shell 變數使用 |
| 「產生器連的就是 runtime DB」 | 專案可能用獨立設計庫，先確認 |
| 「產生完就好，不用檢查」 | 必須確認既有檔案零差異再建 migration |
| 「直接套用 migration」 | 先審查 migration SQL，確認無破壞性變更 |
| 「手改自動產生的 entity 比較快」 | 下次產生會被覆蓋；調模板或設定 |

## 4. 安全規則（通用）

- 唯讀優先：查 schema 只用 SELECT／系統目錄；不用通用寫入連線。
- 目標是共用或正式資料庫時，先告知並取得同意。
- 需要先改設計庫 schema：DDL 前確認備份、先測試環境彩排。

## 5. 自我檢查

- [ ] 附錄已載入並標註
- [ ] 先有 schema、後 scaffold、最後才建 migration
- [ ] 所有設定檔表清單一致、連線字串未落檔
- [ ] 既有檔案零差異（或差異都已解釋）
- [ ] build 通過
- [ ] 回報分開宣稱：scaffold、build、migration 各自結果
