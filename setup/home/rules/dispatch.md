# 派工判準

動手前先判斷這件事該誰做：

| 情況 | 交給 |
|---|---|
| 小、需要目前對話的 context | 自己做 |
| 範圍明確、不需中途問人、結果一份回報就裝得下 | Agent subagent（同一則訊息平行派） |
| 長（預估 15 分鐘以上）、可能中途問人、要完整 session 能力，或要換 CLI | herdr pane worker（專案提供派工 skill（如 `<plugin>:dispatch-worker`）就用它；沒有，或要派給 agy／pi，用 `agent-dispatch` 的長任務模式；只要唯讀第二意見用 `agent-dispatch` 短問答，不開 pane） |

- **派工帶模型**：派 Agent tool 時依等級表設 `model` 與 `effort`，herdr pane 與其他 CLI 也一律明確帶，不繼承預設。規劃、架構、關鍵審查＝`opus`／`high`；實作、研究、QA、除錯＝`sonnet`／`medium`；文件、格式、機械工作＝`haiku`／`low`（同 agent-dispatch 的 `routing.json`）。碰安全、資料、DB 結構、公開介面，或變更超過 300 行，可升一級；偏離等級表就在回報寫「升級理由：…」。
- 平行與否看**共用資源**（同一個 worktree、同一批檔案、build／測試產物、瀏覽器、DB 寫入），不看先後感。
- **該不該拆**：能力、工具、context、驗證迴圈都相同就不拆；「實作＋它的測試」是一件事，失敗後的診斷才另派。
- **派工 prompt 要自足**：自帶目標、背景、前置產出、交付物、驗收標準，以及已拍板的決定（不要重問）與試過排除的方向（不要重走）；worker 得讀完整對話才做得下去＝沒切乾淨。
- **herdr worker 最貴**：每個都是完整 session，開場 context 每輪重讀，subagent 開場不到一半。能用 subagent 就不開 pane。
- 開 pane 前確認在 herdr 內（開場 context 有注明就不查，否則查 `HERDR_ENV`，不另報告）；不在就同 session 接著做並說明。
- **跨 session 訊息照則計費**：每則讓收方整段 context 重送。只在完成或卡住時發，不報進度、不回「收到」。
- 派出去的 worker 卡住時，不替它回答，請使用者 attach 進去。
