# Formwright 試用 tickets：設計

## 目的

Formwright 24 小時跑 `workspace:unattended`，拿它當 tickets plugin 的真實試用場，讓 ticket-* 在長時間、無人值守的情境下暴露問題；每個問題回饋到 plugharbor、修正、發版，Formwright 再拿到新版繼續跑。

- 目標：ticket-create、triage、ticket-ops、ticket-report 在真實工作中被用到；問題有固定管道回到 plugharbor 並在合理時間內發版。
- 非目標：取代 `docs/roadmap.md`（工作段順序仍只認它）；ticket-reply 本階段不刻意製造使用情境。
- 反目標：為了試用改動 Formwright 的自動駕駛主迴圈、讓 roadmap 與票出現兩個進度來源；plugharbor 的 skill 行為在使用者沒看過的情況下改變。

## 做法（選項與裁決）

| 選項 | 取捨 | 結果 |
|---|---|---|
| 只把 `todo.md`「其他」搬成 GitHub Issues | 主迴圈不動、plugharbor skill 不改；ticket-reply 用得少 | **使用者選定** |
| 再加：待決改在票上問 | 五個 skill 全用到，但要改 unattended 回報流程，和回來報告重複 | 不做（第二階段再評估） |
| 工作段也開票 | ticket-ops 用最多，但 unattended 收尾要加同步，roadmap 與票會對不上 | 不做 |

## Formwright 端

1. **安裝**：`setup/install-project.sh <Formwright 根> tickets`（project 範圍，同 lifecycle）。`.plugharbor/lifecycle.yml` 加 `ticket:`：`tool: github`、`repo: KerryHuang/formwright`、`states` 沿用 plugharbor 的 `stage:*` 對照；看板照 `references/config.md` 建（關掉 Project 內建 workflow）。
2. **搬遷**：`docs/todo.md`「其他」每項用 ticket-create 開成 backlog 票，搬完刪掉該區、區塊說明改成「從 backlog 票挑」。「近期可開工」保留在 todo.md，從票升上來的項目寫上票號。
3. **日常流程**（寫進 Formwright `AGENTS.md`／todo.md 說明，不改 plugharbor skill）：
   - 審查留下的建議、CI 偶發失敗、實測 bug → triage 或 ticket-create 開票，不再寫進 todo。
   - 從 backlog 挑進「近期可開工」→ 票改 todo；開做 → in-progress；合併 → 關票並留言 commit。
4. **回饋 plugharbor**：用到 tickets 卡住、skill 做法不對、文件與行為不符時，用 ticket-ops 在 `KerryHuang/plugharbor` 開 issue，label `from:formwright`＋`plugin:tickets`，會讓產線停下或寫錯票的加 `blocker`。內文寫重現步驟、tickets 版本、預期與實際；兩個 repo 都公開，內文照 plugharbor 外洩規則。開完繼續做不依賴它的事。

## plugharbor 端

1. **常駐 worker**（herdr pane，cwd plugharbor）：輪詢 `from:formwright` 的開票，用 `tickets:triage` 分流：
   - bug、文件錯誤、測試缺口：自己修＋測試（validate.py、tickets 腳本測試、`claude -p --plugin-dir plugins/tickets` 本地 e2e）。
   - 會改 skill 行為、規則、description 的：開草稿分支、在票上寫方案與理由、加 `needs-decision`，等使用者裁決。
2. **發版節奏**（使用者裁決）：`blocker` 修完立刻 patch 發版；其餘累積，每天合併發一版。CHANGELOG「起因」寫票號。走 `release-plugin` 同步版號；push 前試用一步由 Formwright 本身擔任（本地 e2e 不省）。
3. **通知新版**：`blocker` 發版後傳一則訊息給 Formwright 主控（只在發版時傳）；每日版不通知，Formwright 段開工前自己更新（見下）。

## Formwright 拿新版

段開工前跑 `claude plugin marketplace update plugharbor` 與 `claude plugin update tickets@plugharbor --scope project`，再 `/reload-plugins`；寫進 Formwright `AGENTS.md`。（我的決定：比每次傳訊省，最多晚一段拿到。）

## 待建置者處理

- 新 label `from:formwright`、`plugin:tickets`、`blocker`、`needs-decision` 在 plugharbor repo 建立。
- worker 的輪詢間隔與 prompt（我的決定：30 分鐘、`blocker` 不等下一輪——Formwright 開 blocker 時同時傳一則訊息叫醒 worker）。
- `ticket-report daily` 設了 `disable-model-invocation`，自動駕駛不能自己叫；改用排程每天跑一次（launchd 或 `/schedule`），或使用者手動跑。
- 驗收：一週內 (1) Formwright 至少 5 張票走完 backlog→done；(2) 至少一則 `from:formwright` 回饋走完修正→發版→Formwright 載入新版；(3) roadmap 與 todo「近期可開工」沒有因試用被改壞。
