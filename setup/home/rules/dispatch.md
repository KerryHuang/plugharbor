# 派工判準

動手前先判斷該誰做：

| 情況 | 交給 |
|---|---|
| 小、需要目前對話的 context | 自己做 |
| 範圍明確、不需中途問人、結果一份回報就裝得下 | 背景 worker（`agent-dispatch` 的 `bg.mjs --type`，走 API 額度）；要 MCP／Web 或未提交改動才用 Agent subagent（同一則訊息平行派） |
| 長（預估 15 分鐘以上）、可能中途問人、要完整 session 能力或換 CLI | herdr（TUI 或 Herdr.app）pane worker（專案有派工 skill（如 `<plugin>:dispatch-worker`）就用；沒有或要派 agy／pi，用 `agent-dispatch` 的長任務模式；唯讀第二意見用 `agent-dispatch` 短問答，不開 pane） |

- **派工帶模型**：派 Agent tool 時依等級表（agent-dispatch `routing.json`：規劃／架構／關鍵審查 opus-high、實作／研究／QA sonnet-medium、文件／機械 haiku-low）設 `model` 與 `effort`，pane 與其他 CLI 也明確帶，不繼承預設。碰安全、資料、DB 結構、公開介面或超過 300 行可升一級，回報寫「升級理由：…」。
- 平行與否看**共用資源**（同一 worktree、檔案、build／測試產物、瀏覽器、DB 寫入、吃 CPU 的測試）。長工作丟背景前先做或派不衝突的待辦，沒有才等、不輪詢。
- **該不該拆**：能力、工具、context、驗證迴圈都相同就不拆；「實作＋測試」是一件事，失敗後的診斷才另派。
- **派工 prompt 要自足**：自帶目標、背景、前置產出、交付物、驗收標準，及已拍板決定（不要重問）與試過排除方向（不要重走）；worker 得讀完整對話才做得下去＝沒切乾淨。
- **herdr worker 最貴**：完整 session，context 每輪重讀；判準表落在自己做或 subagent 時才省 pane，不拿此句推翻長任務列——預估 15 分鐘以上仍派 subagent，回報寫偏離理由。
- **能自己做就不交回**：開新 session、換 repo 接手、自己能跑的測試與實測，都由我派工（herdr 內開 pane；不在 herdr 就同 session 接著做並說明），不叫使用者開 session 或貼 prompt；只有本人能做的（登入、系統授權、實體裝置）才寫 👉。
- **跨 session 訊息照則計費**：每則讓收方整段 context 重送。只在完成或卡住時發，不報進度、不回「收到」。
- worker 卡住時不替它回答，請使用者 attach。使用者授權代答時，先取消選單、用 prompt 送文字裁決（send-keys 送選項數字會被預設選項吃掉），送完讀畫面確認它照做。
- **關 worker 前確認使用者不在跟它談**：結果檔存在、狀態 idle、輸入框空白都不算證據；比對它 transcript 最後一則 user 訊息時間，晚於結果檔就不關，回報後等使用者說收工。
- **驗 agent 遵從率要開新 session**：同 session 派出的 subagent 用 process 啟動時的定義快照，`/clear` 不重載 plugin。改完 agent／skill 後在同 session 只能驗機制，不能驗「有沒有照新規則做」。
- **瀏覽器**：claude-in-chrome 連了多台瀏覽器時，開分頁前先 `list_connected_browsers` 選使用者面前那台（要使用者登入或看畫面時尤其）；用完在回報同一輪關掉自己起的 Chrome（驗 debug port 無回應）與自己開的分頁，不等使用者問；沒關會佔住 port／profile，下個 session 撞到。
- **主 session 做機械性工作**（批次改格式、搬檔、逐筆重跑）前，先提醒使用者切小模型；每回合成本固定，回合數才是乘數。
