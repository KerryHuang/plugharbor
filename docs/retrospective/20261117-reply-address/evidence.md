# feedback-review 2026-11-17 轉交 toolkit:retrospective

## 群 1：派工環境變數 AGENT_DISPATCH_* 漏給子程序

- 佇列 id：20261113125135-f6146a（agent friction，缺口型）
- 原話：herdr pane worker 帶 AGENT_DISPATCH_RESULT／INTERACTIVE 跑 e2e，在子程序開 claude -p；子程序繼承環境變數，dispatch-stop-guard 逼它把 e2e 報告寫進派工結果檔，主控誤以為 worker 完成
- 根因：`plugins/toolkit/skills/agent-dispatch/SKILL.md:104` 只列 HERDR_*、HC_TERMINAL_ID、HC_TERMINAL_SOCKET、HC_SCOPE 要濾；`ask.mjs` 自動濾的清單也沒有 AGENT_DISPATCH_*
- 建議：優先用機制，讓 ask.mjs／mux.py 起拋棄式子 CLI 時自動濾掉 AGENT_DISPATCH_*（附測試）；不行才改 SKILL 文字

## 群 2：改名後派工，回報位址沿用舊名

- 佇列 id：20261117161903-74c3fb（使用者糾正）
- 原話：「剛才的位址錯了（前 session 已改名）。請把同一則兩行確認訊息改用 SendMessage 發給『README 開頭縮短（雙顧問） [44dec6]』」
- 經過：session 3a056a5f 早先用 plugharbor-25 當回報位址（transcript 第 112 行），之後依回合結尾規則改名（第 403～413 行），情境 5 交接 prompt（第 459 行）仍寫 plugharbor-25，新 session 回報「No agent named 'plugharbor-25' is reachable」
- 既有文字：`agent-dispatch/SKILL.md:107` 已要求「先用 ListAgents 取得自己的位址寫進 prompt」，沒被遵守；文字已證明無效，要升級成機制
- 建議方向（未驗證）：spawn／self-rotate 自動帶入目前名稱；或回報位址一律用 [ref]（要先驗證 ref 在改名後是否不變）
- 相關帳本：user 帳本「2026-11-08｜已派出 worker 且未回報時不建議 /rename」（觀察中）；如果 ref 改名後不變，這條例外可以合併或刪除

## 跨 session 掃描：SendMessage「No agent named」（subagent 分類，2026-11-17）

| 日期 | 事件 | 失敗位址形式 | 成因 | 後來成功 |
|---|---|---|---|---|
| 11-03 | 1 | 舊名 [ref] | 派工後改名 | 新名 [同 ref]（ListAgents 後） |
| 11-03 | 2 | 只有 [ref] | 位址格式 | 同上 |
| 11-06 | 3 | 裸 ref | 位址格式（收件方沒改名） | 無，寫 undelivered |
| 11-09 | 4 | 裸 ref | 位址格式（收件方沒改名） | 無 |
| 11-12 | 5 | 名 [ref] | 派工方 ref 換了、名稱沒變（同名有 2 個） | 無 |
| 11-12 | 6 | 裸名 | 派工後約 4 分鐘改名 | 無，寫 undelivered |
| 11-13 | 7 | 裸名 | 改名且重開（ref 全換） | 新裸名 |
| 11-13 | 8 | 名 [ref] | 派工 2 分鐘後改名，ref 不變 | 無 |
| 11-17 | 9 | 裸名 | 改名後沿用舊快照 | 新名 [同 ref] |

- 10-21～22 另一專案的派工批次：69 次失敗、65 個 session；61 次是「舊名 [ref]」，那個 ref 在別處以新名出現；抽查 3 個，改送新名 [同 ref] 後都成功。
- 全量統計：名 [ref] 成功 242 次、失敗 69 次；純名成功 316 次、失敗 14 次；裸 ref 0／2；只有括號 ref 0／1；agentId 271／271。
- 僅本機 Claude Code transcript；無 token 量化數據。
