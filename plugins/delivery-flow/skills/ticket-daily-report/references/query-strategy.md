# 查詢策略與口徑

所有查詢都叫用 `delivery-flow:ticket-ops` 的 `query`（篩選：階段、label、parent、更新時間、建立時間範圍、完成時間範圍、關鍵字；回傳 ID、標題、階段、labels、parent、updatedAt、url，以及選配的 assignee、createdAt、completedAt、priority、dueDate）。

## 原則

1. **全量，不抽樣**：要求 ticket-ops 分頁拉完。只取第一頁，數字會系統性偏低。
   ticket-ops 回「query 完整性：可能截斷」時，報表**頂端**用警語標明（「查詢可能被截斷，以下數字為下限」），受影響的數字標「≥」，不當完整結果交出。
2. **大結果落檔**：結果過大時 ticket-ops 會落檔並回傳路徑，改用 jq／python 讀，
   **不要為了塞進對話而砍欄位重試**。落檔與衍生檔一律放 `.tmp/daily-report/`。
3. **選配欄位**：`assignee`、`createdAt`、`completedAt`、`priority`、`dueDate` 由 ticket-ops 依後端能力回傳（GitHub 的 `dueDate` 恆為空）。
   ticket-ops 未回傳時，對應清單與燈號標「未提供」，完成日不拿 `updatedAt` 冒充。`estimate` 不在契約內。

## 存量 vs 流量

| 口徑 | 定義 | 用在哪 |
|------|------|-------|
| **流量** | 落在「上一個工作日 ~ 現在」窗內 | 交付、新增、階段變更 |
| **存量** | 產出當下的全量狀態計數，不受窗限制 | 各段卡住件數 |

兩者混用會得到互相矛盾的數字。報表上分區塊放並標明口徑。

## 階段對應

看板從右到左：`in-review`（等驗收）→ `in-progress`（進行中）→ `todo`（待排）→ `backlog`（需求池）。`done` 與 `canceled` 只用在交付與清理判斷。

## 必備清單

| key | 定義 | 陷阱 |
|-----|------|------|
| `delivered` | 窗內進入 `done`，**扣除批次清理** | 這才是真實交付；ticket-ops 未回傳 `completedAt` 時才標「未提供」 |
| `cleanup` | 同窗內的批次結案 | 分開列，不然虛胖；ticket-ops 未回傳 `completedAt` 時才標「未提供」 |
| `created` | 同窗內新建 | ticket-ops 未回傳 `createdAt` 時才標「未提供」 |
| `review_*` | `in-review` 全量存量 | 與流量不同口徑 |
| `blocked` | 帶 `blocked` label 的未完成票（label 名稱以專案約定為準） | 重點是等幾天，不是幾件；專案沒有此 label 時整組標「未提供」，不要寫成 0 |
| `new_urgent` | 窗內新建或升級為最高優先的票 | ticket-ops 未回傳 `priority`（或全為 `none`）時才標「未提供」；紅燈來源 |
| `unblocked` | 窗內脫離被擋狀態 | 綠燈來源，別漏了好消息 |

## 批次結案偵測

**兩個條件都要成立：**

1. 結案時間相鄰 **≤3 分鐘**聚類，簇大小 **≥5**
2. 該簇的**票齡中位數 > 90 天**

> 缺一不可。只看時間會誤殺——開發者本來就可能三分鐘內連關五張剛做完的票；
> 票齡中位數把「清理陳年票」和「一次交付多張」分開。間隔用 60 秒會把同一次清理切斷、漏掉尾巴，180 秒較穩。

## 歸戶

依專案約定的 label 歸戶（客戶、模組、產品線）。`parent`／project 欄位的覆蓋率通常不完整，不可當唯一依據；用 label 前先看覆蓋率，過低就在資料警告註明。

## 判斷「缺票」

一律另下全量查詢，**不可用時間窗反推**。窗內沒出現只代表今天沒動過。

## 停滯天數

以 `updatedAt` 起算，但先驗證可信度：最後異動日分布中**單日佔比 > 30% 即為批次痕跡**，該批天數只是下限。
天數一律換算成**工作日**，行事曆接法見 `${CLAUDE_PLUGIN_ROOT}/references/report-calendar.md`。
