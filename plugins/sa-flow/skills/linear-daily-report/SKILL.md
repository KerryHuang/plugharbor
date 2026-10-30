---
name: linear-daily-report
description: "產出 Linear 每日進度報表：走看板找卡點、只列今天變壞的事、每天一件要決策的事，並寫入 Linear Document。票號另出明細文件。觸發：「Linear 日報」「今天卡在哪」。週一週會的每週報表請用 linear-weekly-report。"
argument-hint: "[--project {專案名稱}] [--date {YYYY-MM-DD}] [--no-publish]"
model: sonnet
context: fork
---

# Linear 每日進度報表

> 非 Claude Code（如 Pi）執行時，先讀 `../../references/harness-terms.md`（相對本檔；Claude Code 為 `${CLAUDE_PLUGIN_ROOT}/references/harness-terms.md`，照字面執行可略過），把 Claude 專屬工具與路徑換成對應項。

本 skill 以 `context: fork` 執行：在不帶對話歷史的 subagent 裡跑，Linear 大量查詢結果不留在呼叫方的 context。fork 裡**沒有 `AskUserQuestion`**，所以不能中途問使用者，缺參數一律報錯終止。

回答一個問題：**今天有什麼會出包。** 不是「昨天發生了什麼」——那是紀錄，沒人看。

與 `linear-weekly-report` 分工：日報看**今天的異常**，週報看**一週的趨勢與承諾**。
日報不做趨勢、不做產能對照、不做承諾兌現。

- 燈號判準：`references/signal-logic.md`
- 報表範本與用語規則：`references/report-template.md`
- 查詢與口徑：`references/query-strategy.md`
- 工作日與假日（共用）：`${CLAUDE_PLUGIN_ROOT}/references/report-calendar.md`

## 輸入參數

| 參數 | 必填 | 預設 | 說明 |
|------|:----:|------|------|
| `--project` | 發布時必填 | — | Linear Project，只決定文件放哪；**查詢一律 workspace 全域**。`--no-publish` 時可省略 |
| `--date` | 否 | 今天 | 報表日 |
| `--no-publish` | 否 | 否 | 只產檔不寫 Linear，落在 `.tmp/daily-report/` |

## 四條不可違反

### 1. 清單是唯一真相

**先產清單，數字由清單長度回填。禁止兩邊各算各的。**
每個統計數字都必須等於某張票清單的筆數，發布前程式化複驗。

> 教訓：曾因只取前 100 筆，導致某人的票數與待驗收數都只剩實際的一半上下。
> **數字不可信的報表，讀的人會停止相信它。**

### 2. 不抽樣，拉全量

`hasNextPage` 為真就帶 cursor 續拉。大結果會自動落檔，改用 jq／python 讀，
落檔與衍生檔一律放 workspace 根 `.tmp/daily-report/`。

### 3. 「昨日」是上一個工作日，不是昨天

週一要回溯到上週五。工作日定義與假日處理見共用 reference；
沒有假日資料時退回「週一~週五」並在報表註明。

### 4. 停滯天數要驗證來源可信度

批次操作會把大批票的 `updatedAt` 一次重設，讓它們同時「跨過」某個門檻。
產報表前先看最後異動日的分布：**單日佔比超過 30% 即為批次操作痕跡**，
該日的票停滯天數只是下限。此時老化訊號標「本日不可用」並說明原因，**不要假裝能判斷**。

> 實測曾有單日佔了卡住總數近半。

## 工作流程

### Step 1 — 定日期與目標

`--date` 未給取今天。推出「上一個工作日」作為對照基準。
`--project` 未給且沒有 `--no-publish` → 呼叫 `list_projects` 列出可選的 project，回報「請帶 `--project` 重跑」後終止。不要自己挑一個。

### Step 2 — 拉資料（全量，平行）

依 `references/query-strategy.md`。同時取當日假日／請假資料（若有來源，見共用 reference）；
拿不到就走無假日資料模式。

### Step 3 — 建清單

每個要出現在報表上的數字，先建對應清單（含票號、標題、負責人、meta）。
**清單建完才進 Step 4。**

**清單一律落檔** `.tmp/daily-report/dataset.json`（key → `{label, note, items[]}`）——
Step 5 的 report-writer 讀它，不從對話拿。這也讓數字↔清單複驗有單一事實來源。

必備清單與各自的陷阱見 `references/query-strategy.md`；其中兩組容易錯：

- **批次結案要與真實交付分開**：結案時間相鄰 ≤3 分鐘、簇大小 ≥5、**且該簇票齡中位數 > 90 天**。
  只看時間會誤殺真交付；只看票齡會漏掉簇內剛開的票。判準與實測見 query-strategy.md。
- **存量與流量是兩種口徑**：流量＝窗內、存量＝當下全量，混用會得到矛盾數字。

### Step 4 — 判燈號

依 `references/signal-logic.md`。核心原則：**燈號比較「今天 vs 上一個工作日」，
不用絕對值**——絕對值天天紅等於沒有訊號。

**Cycle 完成率預設停用**，不放進報表：Cycle 若是全票容器而非 sprint 承諾，
該比率永遠偏低，無資訊量。
同樣停用：工時／故事點（覆蓋率通常偏低，數字不可信）、人員票數排名（會變成防禦性辯論）。

### Step 5 — 派 `report-writer` 產兩份（**平行**）

**主 session 不寫報表。** 兩份產出彼此獨立、寫不同檔 → **同一批次一次送出兩個 tool call**。

| 產出 | 票號 | out_path |
|------|:----:|---|
| 主報表 | **零票號** | `.tmp/daily-report/report-{日期}.md` |
| 票務明細 | 全部 | `.tmp/daily-report/tickets-{日期}.md` |

```
subagent_type: "sa-flow:report-writer"
prompt: |
  report_type: {daily ｜ ticket-detail}
  out_path: {上表對應路徑}
  template: ${CLAUDE_PLUGIN_ROOT}/skills/linear-daily-report/references/report-template.md
  dataset: {workspace 根}/.tmp/daily-report/dataset.json
  period: 報表日 {日期}，對照基準 {上一個工作日}
  constraints: |
    禁用指標：Cycle 完成率、工時／故事點、人員票數排名（理由見 signal-logic.md）
    存量與流量是兩種口徑，不可混用；報表上分區塊並標明
    第三節「今天要決定什麼」的決策人留【人工填】——那是判斷不是資料
    燈號比較「今天 vs 上一個工作日」，不用絕對值
    {若偵測到批次操作痕跡：老化訊號標「本日不可用」並說明，不要假裝能判斷}
  siblings: |
    {另一份的檔名與它負責的內容——主報表不列票號，票務明細才列}
```

四節結構、走看板的順序、用語規則全部在 `references/report-template.md`，
agent 依該檔產出：

```
一、今天有什麼變壞了     沒有就寫「今天沒有新的壞消息」——那也是有效資訊
二、走看板（右 → 左）    驗收 → 前端 → 開發 → 需求，每段講「卡的是什麼、誰能幫」
三、今天要決定什麼        每條配決策人＋期限；連續出現要標第幾次
   附錄                   上一個工作日完成、行事曆、資料警告
```

**從右到左走看板，不要逐人報告。** 逐人報告是 status theater——每個人輪流講一遍、
沒有任何事被處理。從離出貨最近的一段開始問「是什麼擋住它、誰能幫」。

### Step 6 — 複驗

兩個 agent 的回報都含「數字↔清單複驗」結果。**任一份回報「不建議發布」→ 不得發布**：
讀該檔找出不一致處，修正 `dataset.json` 或重派該份，複驗過了才進 Step 7。

<law>
**agent 的複驗結果要抽驗，不是照單全收。** 隨機挑 2~3 個數字自己對回 `dataset.json`——
實測 agent 的量化斷言曾出現偏差。
</law>

### Step 7 — 兩份產出

| 產出 | 票號 | 標題 |
|------|:----:|------|
| 主報表 | **零票號** | `每日進度報表 {日期}` |
| 票務明細 | 全部 | `每日票務明細 {日期}` |

**每天新建、不覆蓋**，標題帶當日日期。
> 覆蓋同一份文件時標題日期容易沒跟著改，曾出現標題與內文日期不一致。

### Step 8 — 回報

輸出兩個連結、報表日與對照基準日、數字↔清單複驗結果。

## 錯誤處理

| 情境 | 處理 |
|------|------|
| Project 不存在 | 列出現有 Project，請使用者帶正確的 `--project` 重跑，終止 |
| Linear MCP 未設定 | 提示設定 `.mcp.json`，終止 |
| 查詢結果過大 | 已自動落檔，用 jq／python 讀，不要砍欄位重試 |
| 行事曆拿不到 | 走無行事曆模式並在報表註明，不中止 |
| 停滯天數偵測到批次痕跡 | 老化訊號標「本日不可用」＋說明，不做假判斷 |
| 數字與清單不一致 | **不得發布** |

## 使用範例

```bash
sa-flow:linear-daily-report --project "{專案名稱}"
sa-flow:linear-daily-report --project "{專案名稱}" --date 2026-09-08
sa-flow:linear-daily-report --no-publish
```

## 排程

`/schedule` 每個工作日 09:00：`0 9 * * 1-5`，指令必須帶 `--project`。
排程產出後**第三節的決策人仍需人工填**——那是判斷不是資料。
