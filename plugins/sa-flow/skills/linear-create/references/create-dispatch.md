# 建票派工（linear-create Step 9）

建票工作交給 subagent，不在主 session 做。每次呼叫 `save_issue` 都算一輪，每一輪都要把主 session
的整份 context 重讀一遍，而且每次都會回傳約 4k 字元的整張票。一棵票樹十幾張票，全部落在主 session
上，成本就會跟著 context 大小一起放大。

## 主 session 做的事

1. **把 Step 8 確認後的草稿寫成 ticket-plan 檔**：放在 session scratchpad 目錄，沒有的話用系統暫存目錄；
   路徑一律是絕對路徑。每張票一節，節名是 `## {序號} {票種}｜新建／校正 {既有票號}`，
   節內寫齊以下欄位：team、title、parent（寫序號或既有票號）、assignee、state（寫名稱，
   由 subagent 查 ID）、priority、labels、projectId、estimate（僅 Dev 票）、dueDate（見下方 SLA）、
   links、blockedBy（序號或既有票號＋依據，沒有寫「無」），最後放完整的 description 原文。
   描述最後一行的票源 flag 要在寫檔時就加好（見下方）。
2. **派 subagent**，照下方樣板。
3. **收到回報後輸出 Step 10**，票號和 URL 都從回報取，不要自己再 `get_issue` 一張一張查。

## 派工樣板

```
subagent_type: "general-purpose"
model: "sonnet"
prompt: |
  依 ticket-plan 在 Linear 建票，不做任何內容判斷：草稿已經過使用者確認，逐字照用。
  ticket-plan：{絕對路徑}
  建票規則：${CLAUDE_PLUGIN_ROOT}/skills/linear-create/references/create-dispatch.md「建票規則」節
  建立順序、parentId、blockedBy、links：${CLAUDE_PLUGIN_ROOT}/skills/linear-create/references/ticket-flow.md
  狀態與 assignee 預設：${CLAUDE_PLUGIN_ROOT}/skills/linear-create/references/linear-ticket-defaults.md

  回報格式（只回這張表加失敗清單，不要貼 save_issue 的回傳內容）：
  | 序號 | 票號 | 標題 | URL | 狀態 | blockedBy（實際寫入的票號，無則「—」） | 備註（estimate 未寫入、狀態 fallback 等） |
  失敗的票：序號、錯誤原文、已經做到哪一步。遇到失敗就停，不要自己換參數重試，
  「建票規則」明文允許的 fallback 除外。
```

## 建票規則

依 ticket-plan 的順序建立每張票，帶入 description、assignee、state、labels、links、priority
（Urgent=1、High=2、Normal=3、Low=4）；estimate **只有 Dev 票**帶。

- **票源 flag**：本次新建的票全部要在描述**最後一行**加 `_from sa-flow:linear-create@{version}_`
  （斜體一行，前面空一行），`{version}` 取 `${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json` 的 `version`。
  **不放在標題**（標題留給人讀）。Step 3.5 校正的既有票如果原本沒有 flag，也補在描述最後一行。
  `sa-flow:dev-feedback` 靠這一行判斷票面內容是不是本 plugin 產生的。
- **Step 3.5 校正項**同一批執行：既有 Dev 票用 `save_issue` 更新描述與 blockedBy（**只改 Dev 票**，PM／QA 票及其
  assignee、state 都不動），補開的票掛回既有根票。
- **Project**：ticket-plan 有 projectId 時，**所有票**都帶。
- **Due date（SLA）**：Dev 子票（前端／後端）和 **Bug 樹的 QA 票**，依優先級帶 `dueDate`
  （建票當日 + SLA 天數，格式 `YYYY-MM-DD`）；Bug 樹 QA 票的天數 = Dev + 1。
  Low、沒有優先級，以及其他票種（PM、SA、Feature 樹 QA）都不帶。天數表見
  `linear-ticket-defaults.md` §Due date（SLA）預設規則。
- **Estimate**：既有 Dev 票校正時**不覆寫原有 estimate**，只補沒有的。`save_issue` 因為 estimate
  被拒（團隊沒啟用估算，或尺規裡沒有這個值）→ 去掉 `estimate` 重送一次，票照建，回報時備註「estimate 未寫入」。
- **state 照 ticket-plan**，用 `list_issue_statuses` 查 ID 指定，不用名稱；`Blocked By BE` 查不到就用 `Todo`，
  備註註明。
- **blockedBy**：用 `save_issue` 的 `blockedBy` 參數寫入（序號換成已建立的票號，blocker 先建）；被拒就停下回報，
  不改掛 `relatedTo`。回報表 blockedBy 欄寫實際寫入的票號，與 ticket-plan 不同時在備註說明。
