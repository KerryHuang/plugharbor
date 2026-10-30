# 雙顧問討論：執行細節

> 規則（何時開、兩個視角、輪次、結案、校準、證據、問使用者）在 `consultant-desk.md`「雙顧問討論」節，先讀那裡。
> 本檔只放執行時才需要的指令、檔案格式與異常處理。

兩位顧問是**同一支 `domain-advisor` 的兩個實例**，派工時以 `lens` 指定視角：

| 代號 | `lens` | 看什麼 |
|------|--------|--------|
| flow | `business-flow` | 業務流程：角色與情境、狀態流轉、例外與回退、業務規則與口徑 |
| data | `data-boundary` | 資料與系統邊界：聚合根與一致性、Source of Truth、跨模組／外部系統責任、權限與稽核 |

視角只決定「先看哪裡、提什麼爭點」，校準、證據等級與回應規則兩邊完全相同。

## 目錄與檔案

```
{功能目錄}/analysis/advisor-discussion/{YYYYMMDD}/
  _run.json            # 執行狀態，每輪更新（主線 context 被壓縮後先讀它）
  agenda.md            # 主持人整理後的議程（D-1～D-5）
  open-flow.md         # 開場：業務流程視角的爭點提案
  open-data.md         # 開場：資料與系統邊界視角的爭點提案
  r{N}-to-flow.md      # 第 N 輪轉給 flow 的內容（主線寫）
  r{N}-flow.md         # 第 N 輪 flow 的回應（主線從 transcript 取出後落檔）
  r{N}-to-data.md / r{N}-data.md
```

顧問是唯讀 agent，**所有檔案都由主線寫**。結案後彙整進 `analysis/consultant-notes.md`（格式見本檔末），
本目錄保留作為完整討論紀錄。

`_run.json`：

```json
{
  "mode": "pane",
  "flow": {"pane_id": "wD:p7", "session": "<agent_session.value>"},
  "data": {"pane_id": "wD:p8", "session": "<agent_session.value>"},
  "round": 2,
  "open_issues": ["D-2", "D-4"],
  "closed": {"D-1": "共識", "D-3": "證據裁決"},
  "asked_user": []
}
```

subagent 模式把 `pane_id`／`session` 換成 `agent_id`。

## pane 模式（預設）

前置判定依 `sa-flow:dispatch-worker` Step 0（`HERDR_ENV=1`、cwd 檢查）；不成立 → 走 subagent 模式，並告訴使用者「本次無 pane，紀錄在 advisor-discussion/」。cwd 一律專案根。

開 pane 與起顧問：

```bash
herdr pane split --current --direction right --cwd "<專案根>" --no-focus      # → flow pane_id
herdr agent start advisor-flow --kind claude --pane <flow pane_id> -- --agent sa-flow:domain-advisor
herdr pane split <flow pane_id> --direction down --cwd "<專案根>" --no-focus   # → data pane_id
herdr agent start advisor-data --kind claude --pane <data pane_id> -- --agent sa-flow:domain-advisor
herdr agent list                                             # 取兩者的 agent_session.value 寫進 _run.json
```

- pane_id 讀法與孤兒 pane 處理依 `sa-flow:dispatch-worker` Step 2～3。
- `--agent sa-flow:…` 會套用該 agent 的工具白名單與 model（顧問沒有 `AskUserQuestion`、沒有寫檔工具），不會自己停下來等人。
- 每一則送題的開頭都寫 `lens:`，不只寫在開場——顧問 context 被壓縮後仍知道自己是哪個視角。

送題與取回應：

```bash
herdr agent prompt <pane_id> "$(cat <絕對路徑>/r2-to-flow.md)" --wait --timeout 540000   # run_in_background: true
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/advisor_last_reply.py <session> > <絕對路徑>/r2-flow.md
```

- 送題寫檔依 `sa-flow:dispatch-worker` Step 1（**不含結果檔**：顧問以 `--agent` 起、沒有寫檔工具），等待依 Step 4（`--wait` 不加 `--until`）。
  完成判準是 `advisor_last_reply.py` exit 0 且取到文字，不是結果檔。
- 同一輪兩位顧問的送題互不相依時，在同一則訊息平行送出；爭點進入循序回應（見 consultant-desk 第 3 步）時，先送 A、取回 A 的回應，再連同它送 B。
- 開發中要用工作區未發布的 agent 定義：`agent start` 的參數加 `--plugin-dir <plugins/sa-flow 的絕對路徑>`。
- `advisor_last_reply.py` exit 1（找不到 transcript／最後一輪沒有文字）→ 不可當成「沒意見」，先 `herdr agent read` 看狀態。
- 每輪轉話前 `herdr agent read <pane_id>` 看使用者有沒有直接在 pane 插話；有就把那段併進下一輪的送題，並在回應檔註記「使用者插話」。

## subagent 模式（無 herdr 時）

- 開場：同一則訊息平行派兩個 `sa-flow:domain-advisor`（`mode: discuss-open`，一個 `lens: business-flow`、一個 `lens: data-boundary`），把回傳的 agentId 寫進 `_run.json`。
- 每輪：`SendMessage` 給該 agentId（`mode: discuss-reply`，附 `lens`），回傳文字由主線落檔成 `r{N}-*.md`。
- 沒有續接能力的 harness：每輪重派，prompt 附上該顧問先前所有回應檔（依 `harness-terms.md` 對應）。

## 異常處理

| 情境 | 處置 |
|------|------|
| `--wait` 逾時，或顧問停在畫面上等輸入 | 依 `sa-flow:dispatch-worker` Step 5：逾時不重送不關 pane；等輸入就提醒使用者 attach，不代答 |
| 顧問 pane 不見了 | 重開 pane 起同一個 agent，送題附上 `lens` 與它先前所有 `open-*.md`／`r*-*.md`，輪數不重算 |
| subagent 續接失敗 | 重派，prompt 附上 `lens` 與它先前所有回應檔 |
| 主線 context 被壓縮 | 先讀 `_run.json` 與最後一輪的檔案再續，不重問已結案爭點 |

## 收尾

1. 所有爭點結案、交使用者的題目都答完並寫回 `consultant-notes.md` 之後，才關顧問。
2. pane 模式依 `sa-flow:dispatch-worker` Step 6 逐個關顧問 pane。
3. `_run.json` 標 `"finished": true`。

## consultant-notes.md 追加格式

```markdown
## 雙顧問討論 {日期}（{階段}，{pane／subagent}）

| # | 爭點 | 輪數 | 結局 | 結論 | 關鍵證據 |
|---|------|------|------|------|---------|
| D-1 | … | 2 | 共識 | … | path:line |
| D-2 | … | 5 | 交使用者 → 選 B | … | 測試環境查詢摘要 … |

### 備忘（未討論）
- …

### 延後清單
- …

完整紀錄：`analysis/advisor-discussion/{YYYYMMDD}/`
```
