# Linear backend

用 Linear MCP 工具（Claude Code 名稱 `mcp__linear__*` 或 `mcp__claude_ai_Linear__*`，Pi 對照見 harness-terms）。先確認 MCP 可用；沒有就停下，告訴使用者缺 Linear MCP。
`ticket.team` 為 team 名稱或 key，所有呼叫都帶它。

## 操作對映

| 操作 | 工具 |
|---|---|
| `create` | `save_issue(team, title, description, state, labels, parentId)`；沒有 `id` 即建新票。`state` 同 `set_stage`，用先查到的狀態 ID，不用名稱 |
| `set_stage` | `save_issue(id, state=<狀態 ID>)`；參數名是 `state`，不是 `stateId` |
| `comment` | `save_comment(issueId, body)`；列既有留言用 `list_comments` |
| `attach` | 三步簽名上傳，見下 |
| `query` | `list_issues(query, state, labels, parentId, updatedAt, cursor)`；`hasNextPage` 為真就續抓 |
| `link_blocked_by` | `save_issue(id, blockedBy=[blocker_id])` |

## 與 GitHub 不同、最容易踩的行為

1. **state 是 team 自訂的**：名稱因團隊而異。改階段前先 `list_issue_statuses(team)` 查出 `ticket.states` 對照名稱的 ID，用 ID 指定；查不到就停下回報，不改用近似名稱。
2. **blockedBy 才會通知**：blocker 完成（解除）時 Linear 才推通知給被擋住的票；`relatedTo` 不會。要「被擋住的人收到通知」就必須用 `blockedBy`，被拒時不要降成 `relatedTo` 蒙混，回報原因。
3. **子票進度 rollup 是被動訊號**：父票自動顯示「2/2」。re-parent（改掛父票）可能觸發 team 自動化改 assignee 或 state，掛完要讀回確認。
4. **description 整段覆寫**：`save_issue(description)` 取代全文。更新前一律先 `get_issue` 讀回完整原文，改好整份送回，不可只送片段。含 `linear-embed`（使用者拖進去的檔案）時不要覆寫，寫回會把 embed 洗成空殼；改請使用者把檔案改成附件，或停下回報。送出後再 `get_issue`，確認目標字串在、`updatedAt` 有變；沒變就停下回報，不改用整份重送。
5. **互斥 label group**：同一組 label 同票只能帶一個，同帶會回 400（`Only one label in a group can be applied`）。
6. **專案與 team 綁定**：帶了未綁該 team 的 project 會回 400；票的 team 不在專案綁定清單就不帶 `project`，照建並備註。
7. **estimate 尺規**：被團隊拒絕（沒啟用或值不在尺規內）時，去掉 `estimate` 重送一次，票照建，備註「estimate 未寫入」。
8. 「票面有錯」改描述，不用留言更正；留言只用在需要對話的場合。

## 附圖（三步，一次一檔）

簽名 URL 只有 60 秒，批次 prepare 會過期；每個檔案 prepare、PUT、finalize 做完才處理下一個。

1. `prepare_attachment_upload(issue, filename, contentType, size, title)`；`size` 用 `ls -l` 取精確 bytes。
2. 用 curl PUT 到回傳的 `uploadRequest.url`：

   ```bash
   curl -sS -X PUT --data-binary @"<檔案絕對路徑>" \
     -H "content-type: image/png" \
     -H "cache-control: public, max-age=31536000" \
     -H "x-goog-content-length-range: <size>,<size>" \
     -H 'Content-Disposition: attachment; filename="<檔名>.png"' \
     -o /dev/null -w "%{http_code}" "<uploadRequest.url 完整網址>"
   ```

   期望輸出 `200`。URL 必須逐字元完整複製（簽名是長 hex，錯一字就 400）；回傳的 headers 全部照帶；400／403 代表 URL 錯或過期，重新 prepare，不重試舊 URL。
3. `create_attachment_from_upload(issue, assetUrl, title)`。

內嵌：用 `![說明](<assetUrl>)` 寫進描述（assetUrl 不帶簽名參數，Linear 顯示時自動重簽）；寫描述時遵守上面第 4 點，在既有描述中插入，不動其他章節。
