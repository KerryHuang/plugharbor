# SQL Server 安全

- 唯讀優先：查資料一律 SELECT；有唯讀工具就走唯讀工具，不開通用連線。
- **禁止把寫入／破壞性效果的 MCP 工具（如 `execute_sql`、`execute_ddl`、
  `delete_connection` 這類工具）預先核准進 `permissions.allow`**——一律逐次經人工確認，不得靠 allow 規則跳過。
- 正式環境非必要不查；必查先告知並取得同意。
- 任何 DDL／破壞性 DML 前：確認備份存在且可還原，先在測試環境彩排。
- 大量刪除／更新分批執行（每批獨立交易、定期 CHECKPOINT），避免交易記錄暴漲；
  SIMPLE 復原模式也一樣要分批。
- 「唯讀」工具對含 DDL 的批次不一定真唯讀——驗 DDL 語法不要丟給查詢工具，只送純 SELECT。
- 效能歸因要隔離實測（一次改一個變數、量一次）；plan cache 只能證明哪個陳述式慢，
  不能證明為什麼慢。
