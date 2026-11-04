# daily 模式流程

共同規則（清單即真相、全量、`completedAt`、口徑、禁用指標、批次結案）見 SKILL.md。本檔只寫日報特有的步驟。

- 燈號判準：`${CLAUDE_SKILL_DIR}/references/signal-logic.md`
- 報表範本與用語規則：`${CLAUDE_SKILL_DIR}/references/daily-template.md`
- 查詢與口徑：`${CLAUDE_SKILL_DIR}/references/daily-query.md`
- 行事曆：`${CLAUDE_PLUGIN_ROOT}/references/report-calendar.md`

## 「昨日」是上一個工作日，不是昨天

週一要回溯到上週五。工作日定義與行事曆接法見共用 reference；拿不到行事曆時退回週一至週五並在報表註明。

## 步驟

### 1. 定日期

`--date` 未給取今天，推出上一個工作日作為對照基準。

### 2. 拉資料（全量，平行）

依 `daily-query.md`，叫用 `lifecycle:ticket-ops` 的 `query`。同時取行事曆（今日會議、請假、假日）；拿不到就走無行事曆模式。

### 3. 建清單

每個要出現在報表上的數字先建對應清單（含 ID、標題、階段、labels、meta），清單建完才進下一步。**一律落檔** `.tmp/daily-report/dataset.json`，report-writer 讀它，不從對話拿；這也讓數字與清單複驗有單一事實來源。必備清單與各自的陷阱見 `daily-query.md`。

### 4. 判燈號

依 `signal-logic.md`。核心原則：**燈號比較「今天 vs 上一個工作日」，不用絕對值**，絕對值天天紅等於沒有訊號。

### 5. 派 `report-writer` 產兩份（平行）

主 session 不寫報表。兩份寫不同檔，同一批次一次送出兩個 tool call：

| 產出 | 票號 | out_path |
|------|:----:|---|
| 主報表 | **零票號** | `.tmp/daily-report/report-{日期}.md` |
| 票務明細 | 全部 | `.tmp/daily-report/tickets-{日期}.md` |

```
subagent_type: "lifecycle:report-writer"
prompt: |
  report_type: {daily ｜ ticket-detail}
  out_path: {上表對應路徑的絕對路徑}
  template: {專案根或 plugin 的絕對路徑}/references/daily-template.md
  dataset: {專案根}/.tmp/daily-report/dataset.json
  period: 報表日 {日期}，對照基準 {上一個工作日}
  constraints: |
    禁用指標：Cycle／Sprint 完成率、工時／故事點、人員票數排名（理由見 signal-logic.md）
    存量與流量是兩種口徑，不可混用；報表上分區塊並標明
    第三節「今天要決定什麼」的決策人留【人工填】——那是判斷不是資料
    燈號比較「今天 vs 上一個工作日」，不用絕對值
    priority、dueDate 只在 dataset 有提供時才寫；沒有就寫「未提供」，不寫「無」
    {若偵測到批次操作痕跡：老化訊號標「本日不可用」並說明，不要假裝能判斷}
  siblings: |
    {另一份的檔名與它負責的內容——主報表不列票號，票務明細才列}
```

四節結構、走看板順序與用語規則都在 `daily-template.md`：

```
一、今天有什麼變壞了     沒有就寫「今天沒有新的壞消息」——那也是有效資訊
二、走看板（右 → 左）    驗收 → 進行中 → 待排 → 需求池，每段講「卡的是什麼、誰能幫」
三、今天要決定什麼        每條配決策人＋期限；連續出現要標第幾次
   附錄                   上一個工作日完成、行事曆、資料警告
```

**從右到左走看板，不要逐人報告。** 逐人報告是 status theater——每個人輪流講一遍、沒有任何事被處理。從離出貨最近的一段開始問「是什麼擋住它、誰能幫」。

### 6. 複驗

兩個 agent 的回報都含「數字與清單複驗」結果。任一份回報「不建議發布」→ 不得發布。依 SKILL.md 抽驗 2～3 個數字。

### 7. 落地與回報

兩份每天新建、不覆蓋。沒給 `--out-dir` 就停在 `.tmp/daily-report/` 並講明。回報：兩份檔案路徑、報表日與對照基準日、複驗結果、`dataset.json` 缺哪些選配欄位（priority、dueDate 等）。
