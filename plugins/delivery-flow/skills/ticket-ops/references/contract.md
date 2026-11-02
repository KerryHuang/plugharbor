# 操作契約

叫用端只用下列七個操作與抽象階段；工具差異由 `linear.md`、`github.md` 吸收。

## 抽象階段

`backlog`、`todo`、`in-progress`、`in-review`、`done`、`canceled`（與 `${CLAUDE_PLUGIN_ROOT}/references/config.md` 一致；底線寫法 `in_progress` 視為同義）。`ticket.states` 把它們對照成工具上的實際名稱。

轉換用 `scripts/ticket_backend.py`（`stage_to_native`）：

| 工具 | 回傳 |
|---|---|
| Linear | `{"state": "<state 名稱>"}` |
| GitHub | `{"labels_add": [...], "labels_remove": [...], "close": bool, "reason": "completed"｜"not planned"（僅 close 時）}` |

GitHub 慣例：階段用 label `stage:<名稱>` 表示（`ticket.states` 填 `stage:in-progress` 這類值）；`done` 與 `canceled` 不掛 label，改關閉 issue（`done` 以 completed、`canceled` 以 not planned 關閉），並移除所有 `stage:*`。未知階段會 raise 並列出合法值。

## 操作

| 操作 | 參數 | 回傳 | 說明 |
|---|---|---|---|
| `create` | `title`、`body`、`parent?`、`labels?`、`stage?` | 票 ID、URL | `parent` 為父票 ID；`stage` 預設 `backlog` |
| `set_stage` | `id`、`stage` | 新階段 | 先轉原生值再套用；規則見各 backend |
| `comment` | `id`、`body` | 留言 ID／URL | 冪等標記（首行固定字串）由叫用端放進 `body` |
| `attach` | `id`、`image_path`、`caption` | 內嵌用 markdown | 上傳後把圖內嵌進描述或留言。**回報必須寫明圖實際在哪、連結是否有效**；沒真正附上就明說，不得回報「已附圖」（GitHub：push 前連結是壞的，見 `github.md`，未 push 回報「圖仍在本機 <path>，未附」） |
| `query` | `filter`（階段、label、parent、更新時間、建立時間範圍、完成時間範圍、關鍵字） | 票清單（ID、標題、階段、labels、parent、updatedAt、url、`assignee?`、`createdAt?`、`completedAt?`、`priority?`、`dueDate?`） | 結果大時落檔，回傳路徑。**不得靜默截斷**：後端有筆數上限就分段或分頁取完，取不全要回「query 完整性：可能截斷」，數字標下限（見各 backend）。階段不在 `ticket.states` 對照內回 `unmapped:<name>` |
| `get` | `id` | 標題、body、階段、labels、parent、children ids、url、updatedAt | 讀單張票全文；`parent` 無則 null，`children` 無則空 list |
| `link_blocked_by` | `id`、`blocker_id` | 是否成功、降級說明 | 見各 backend 的通知語意差異 |

`query` 回傳欄位中 `?` 表示後端有才回；`completedAt` 只在階段為 `done` 時非 null；`priority` 一律正規化為 `urgent`／`high`／`medium`／`low`／`none`。`estimate` 不在契約內。

## 能力差異摘要

| 能力 | Linear | GitHub Issues |
|---|---|---|
| 階段 | team 自訂 state（先查 ID） | `stage:*` label＋open／closed |
| 父子票 | `parentId`，子票進度自動 rollup | 內文 task list（`- [ ] #n`）；rollup 弱 |
| blocked-by | 原生 `blockedBy`，blocker 完成時推通知 | 內文 `blocked-by: #n` 慣例，無通知 |
| 讀單張票 | `get_issue`（children 取子票） | `gh issue view`；parent 讀 body 的 `parent: #n`，children 讀 body 的 task list |
| 附圖 | 三步簽名上傳 | 無官方 API，圖存 repo、push 後再貼連結 |
| priority／estimate／dueDate | 原生欄位 | 無，需要時用 label |
