# Changelog

格式：每次改動 `skills/`、`agents/`、`references/` 時，於最上方新增版本條目並同步 bump 版號（規則見 `.claude/rules/version-consistency.md`）。

## [1.0.1] - 2026-11-05

- fix: `schema-docs` description 從 438 字壓到約 140 字（拿掉重複的英文觸發詞與方言清單），避免 skill 清單超出預算時被丟成只剩名稱。

## [1.0.0] - 2026-11-03

- feat!: 新 plugin，自 database-sqlserver 1.x 改寫為「通用方法＋方言／ORM 附錄」。`table-conventions`＋`view-conventions` → `schema-conventions`；`ef-migration`＋`migration-troubleshoot` → `migration`；`syncing-db-entities` → `orm-sync`；`generating-table-description` → `schema-docs`。
- feat: 附錄 `references/dialects/{sqlserver,postgresql,mysql,sqlite}.md`（SQL Server 自舊 skill 搬來；其餘三份依官方文件整理，標「未實戰驗證」）、`references/orm/ef-core.md`（migration、efcpt、診斷指令）。
- feat: 加 `package.json`（`pi.skills`），pi 也載入得到。
