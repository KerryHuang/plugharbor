# 建票派工與建票規則

`full` 一棵票樹有五張票。每次 `create` 都算一輪，每輪都要重讀主 session 整份 context，全部落在主 session 成本會跟 context 一起放大，所以交給 subagent。`lean` 一張票，主 session 自己建。

## 主 session 做的事

1. 把確認後的草稿寫成 ticket-plan 檔：放在 session scratchpad，沒有就用系統暫存目錄，路徑用絕對路徑。每張票一節，節名 `## {序號} {角色}｜新建／既有 {票號}`，節內寫齊：title、parent（序號或既有票號）、stage（抽象階段）、labels、blocked_by（序號或既有票號，沒有寫「無」），最後是完整 description 原文（票源 flag 寫檔時就加好）。
2. 派 subagent（樣板如下）。
3. 收到回報後輸出 SKILL.md 步驟 8。

## 派工樣板

```
subagent_type: "general-purpose"
model: "sonnet"
prompt: |
  依 ticket-plan 建票，不做內容判斷：草稿已經使用者確認，逐字照用。
  ticket-plan：{絕對路徑}
  所有票務動作都叫用 lifecycle:ticket-ops（create、link_blocked_by），不直接呼叫任何票務工具。
  建票規則：{本檔絕對路徑}「建票規則」節

  回報格式（只回這張表加失敗清單，不貼 create 的整張票回傳）：
  | 序號 | 票號 | 標題 | URL | 階段 | blocked_by（實際寫入的票號，無則「—」） | 備註（降級、fallback） |
  失敗的票：序號、錯誤原文、已經做到哪一步。遇到失敗就停，不自己換參數重試。
```

> 派發時路徑要先換成絕對路徑，subagent 不會代換變數。

## 建票規則

- **順序**：先建被依賴的票（blocker 先建）與父票，再建子票；序號換成已建立的票號後才寫 `parent`、`blocked_by`。
- **階段**：照 ticket-plan 的抽象階段傳給 `create`，由 ticket-ops 轉成工具原生值；不自己查或猜狀態名。
- **票源 flag**：新建的票描述最後一行加 `_from lifecycle:ticket-create@{version}_`（斜體一行，前面空一行），`{version}` 取 `${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json` 的 `version`。不放標題。`lifecycle:dev-feedback` 靠這一行判斷票面是不是本 plugin 產生的。
- **blocked_by**：用 `link_blocked_by` 寫入；被拒就停下回報，不改掛弱關聯。回報表寫實際寫入的票號，與 ticket-plan 不同時在備註說明。
- **降級**：ticket-ops 回報的工具降級（blocked-by 只能寫在內文、父子只能用 task list 等）原樣放進備註欄。
- **既有票**：只補相依或補缺的子票，不改既有票內容。
