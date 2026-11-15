# Jira 設定對照範例（未實測）

本層沒有實測過 Jira，沒有對應實作。下列只供參考；`ticket.tool: jira` 時 `ticket-ops` 會先告知並要使用者確認才繼續。

```yaml
ticket:
  tool: jira
  states:
    backlog: Backlog
    todo: To Do
    in-progress: In Progress
    in-review: In Review
    done: Done
    canceled: Won't Do
```

對映想法（皆未驗證）：

| 操作 | Jira 做法 |
|---|---|
| `create` | `POST /issue`；欄位多為專案自訂 |
| `set_stage` | 先查 transitions，再 `POST /issue/{key}/transitions`；不是任意狀態都可達 |
| `comment` | `POST /issue/{key}/comment` |
| `attach` | `POST /issue/{key}/attachments`（multipart），描述以 `!檔名!` 內嵌 |
| `query` | JQL＋`startAt`／`maxResults` |
| `link_blocked_by` | issue link type（Blocks／is blocked by） |

注意：描述格式不是 markdown（wiki markup 或 ADF），渲染差異大；父子階層受 issue type 限制。`stage_to_native` 對 `jira` 回 `{"state": 名稱}`，之後的 transition 查詢需自行處理。
