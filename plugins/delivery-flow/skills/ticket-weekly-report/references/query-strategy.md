# 查詢策略

所有查詢都叫用 `delivery-flow:ticket-ops` 的 `query`（篩選：階段、label、parent、更新時間、建立時間範圍、完成時間範圍、關鍵字；回傳 ID、標題、階段、labels、parent、updatedAt、url，以及選配的 assignee、createdAt、completedAt、priority、dueDate）。

## 原則

1. **無相依查詢同批發出**
2. **分頁拉到底**：只取第一頁會少算，淨變化會跟著偏
3. **大結果會落檔**：ticket-ops 回傳路徑，改用 `jq`／`python` 讀，**不要為了塞進對話而砍欄位重試**。
   落檔複本與所有衍生檔一律放專案根 `.tmp/weekly-report/`，用完即刪
4. **選配欄位**：`assignee`、`createdAt`、`completedAt`、`priority`、`dueDate` 由 ticket-ops 依後端能力回傳（GitHub 的 `dueDate` 恆為空）。
   ticket-ops 未回傳時，對應清單標「未提供」；完成日不拿 `updatedAt` 冒充。`estimate` 不在契約內

## 兩批

**第一批（平行）**

| 用途 | 條件 |
|------|------|
| 上週異動全量 | `updatedAt` 在上週窗內 |
| 上週完成與新增 | `completedAt`、`createdAt` 在上週窗內 |
| 各階段存量 | 依階段分別查（`in-review`、`in-progress`、`todo`、`backlog`）；被擋用 `blocked` label |

**第二批（依第一批結果）**

- 要判斷「缺票」時的全量查詢（關鍵字＋label 篩選）
- 案子維度的補查

## 歸戶

規則（用 label，不用 parent／project）見 SKILL.md Step 3。標籤組由專案約定；開跑前先確認覆蓋率，過低就在資料警告註明。
