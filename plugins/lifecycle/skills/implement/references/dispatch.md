# 派工：角色、模型等級與路由

通用派工慣例（主 session 不讀正文、平行怎麼切、回報紀律）見 `${CLAUDE_PLUGIN_ROOT}/references/dispatch-conventions.md`；本檔只寫 implement 特有的部分。

## 角色與模型等級

派工一律明寫模型等級，不繼承主 session 的模型。

| 用途 | agent | 等級 | 同家（Claude）模型 | agent-dispatch 類型 |
|---|---|---|---|---|
| 規劃任務清單 | 通用 subagent | top | opus | `plan` |
| 技術選型、ADR | `lifecycle:architect` | top | opus | `architecture` |
| 寫程式 | `lifecycle:developer` | standard | sonnet | `implement` |
| 寫測試、TDD Red | `lifecycle:tester` | standard | sonnet | `implement` |
| 除錯、找根因 | `lifecycle:debugger` | standard | 照 agent 定義（opus） | `debug` |
| 規格比對 | 通用 subagent | standard | sonnet | `qa` |
| 程式碼審查 | `lifecycle:reviewer` | top | opus | `review-critical` |
| 驗證單條審查發現 | 通用唯讀 subagent | standard | sonnet | `research` |
| 純機械（打勾、搬檔） | 主 session 自己做 | — | — | — |

## 路由

- **有裝 toolkit**：照 `toolkit:agent-dispatch` 的路由規則，用上表「agent-dispatch 類型」查表決定 CLI、模型與思考等級。查到的是主 session 自己這一家 → 用同家 subagent，帶查到的模型；查到別家 → 照 agent-dispatch 的長任務模式派（改檔的 task）或短問答（唯讀的審查、驗證）。回報照抄它的「交給 <cli>（<模型>／<等級>）」那行。
- **沒裝 toolkit 的退路**：一律同家 subagent，模型照上表「同家模型」欄，回報寫一行「未安裝 toolkit，已改用同家 subagent」。
- agent 不存在（例如只裝了部分 plugin）→ 改派通用 subagent，把該 agent 的職責寫進 brief，模型等級不變。

## context 預算（規劃時檢查）

每個 task 必須在一個全新 subagent 的 context 裡做完，規劃時就檢查：

- brief＋要讀的規格段落＋要讀與要改的檔，總量粗估超過 context 的一半 → 拆。
- 一個 task 要改超過約 10 個檔、或跨兩個以上不相干的模組 → 拆。
- 「實作＋它的測試」算同一個 task，不拆；TDD 模式例外（Red 與 Green 分給 tester 與 developer）。
- 主 session 也有預算：只讀 ledger、tasks.md、報告第一行與疑慮段；要細節就派 subagent 讀了回結論。

## prompt 寫法

```
你是 <feature> 的 <task-id> 實作者。
brief：.tmp/implement/<feature>/briefs/<task-id>.md（先讀，照做）
已定決策：<1–5 行，從 ledger 抄>
完整報告寫到 .tmp/implement/<feature>/reports/<task-id>.md；回覆只回一行「狀態＋報告路徑」。
```

不在 prompt 裡貼規格全文或前一個 task 的對話；需要的東西都放 brief。

`lifecycle:reviewer` 是唯讀（沒有寫檔與 Bash）：它的報告由主 session 原樣落檔到 `reports/review-<輪>.md`（機械落檔，不改內容），它列的「待主對話查證」套件由主 session 查 registry。
