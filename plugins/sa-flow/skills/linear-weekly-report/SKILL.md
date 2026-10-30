---
name: linear-weekly-report
description: "產出 Linear 每週進度報表供週一週會使用：上週回顧＋本週計劃，三份產出（會議簡報 HTML／Linear 會議文件／Linear 票務明細）。觸發：「Linear 週報」「週會報表」「產週會簡報」。日報請用 linear-daily-report。"
argument-hint: "[--project {專案名稱}] [--date {YYYY-MM-DD 週會日}] [--no-publish]"
model: opus
context: fork
---

# Linear 每週進度報表

> 非 Claude Code（如 Pi）執行時，先讀 `../../references/harness-terms.md`（相對本檔；Claude Code 為 `${CLAUDE_PLUGIN_ROOT}/references/harness-terms.md`，照字面執行可略過），把 Claude 專屬工具與路徑換成對應項。

本 skill 以 `context: fork` 執行：在不帶對話歷史的 subagent 裡跑，Linear 大量查詢結果不留在呼叫方的 context。fork 裡**沒有 `AskUserQuestion`**，所以不能中途問使用者，缺參數一律報錯終止。

供**週一週會**使用的 30 分鐘簡報與存檔文件。與 `linear-daily-report` 分工：
日報回答「今天會不會出事」，週報回答「上週推進了什麼、本週押什麼」。
**日報有的東西週報不重複**——昨日異動、Urgent 逐票追蹤、人員負荷表都不進週報。

- 指標定義與禁用指標：`references/metrics.md`
- Linear 查詢與分頁：`references/query-strategy.md`
- 三份產出的章節與範本：`references/outputs.md`
- 落地與 git 流程：`references/publishing.md`
- 工作日與假日（共用）：`${CLAUDE_PLUGIN_ROOT}/references/report-calendar.md`

## 輸入參數

| 參數 | 必填 | 預設 | 說明 |
|------|:----:|------|------|
| `--project` | 發布時必填 | — | Linear Project，只決定兩份 Document 放哪；**查詢一律 workspace 全域**。`--no-publish` 時可省略 |
| `--date` | 否 | 今天 | 週會日；一律回推到該週週一再推算兩條時間軸 |
| `--no-publish` | 否 | 否 | 只產檔不發布：三份產出全部落在 workspace 根 `.tmp/weekly-report/`，不寫 Linear、不動 docs |

## 兩條時間軸（先講清楚，講錯整場會跟著錯）

週會固定週一開，所以報表同時涵蓋兩週：

| 軸 | 範圍 | 用途 |
|----|------|------|
| **上週** | 剛結束那週（一~日） | 回顧：交付、卡點、數據 |
| **本週** | 今天起算那週（一~日） | 計劃：押注、待辦 |

兩者相鄰不重疊。下週一的報表以它的「上週」回頭對照本份的「待辦事項彙整」，
一週一循環、不留空窗。**行文一律用「上週／本週」，不准出現「下週」**
（例外：「下週一逐條對照」這種指涉會議日的用法）。

## 不可違反的三條

### 1. 清單是唯一真相

**先產清單，再由清單長度回填數字。禁止兩邊各算各的。**
每一個出現在報表上的統計數字，都必須等於某張票清單的筆數；產出後要程式化複驗，
不一致就是 bug，不是四捨五入。

> 教訓：初版有四個數字錯（新增、逾期、某客戶交付、某客戶在手），
> 全部是「數字用查詢 A 算、清單用查詢 B 撈」造成的。加了清單後一對就露餡。

### 2. 完成用 `completedAt`，不是 `updatedAt`

實測：過去 7 天 `updatedAt` 命中的票數可達 `completedAt` 落在窗內的數倍。
日報尺度小無所謂，週報用 `updatedAt` 會**嚴重虛胖**。

### 3. 判斷「缺票」一律另下全量查詢

不可用 7 天時間窗反推。窗內沒出現只代表「這週沒動過」，不代表不存在。

> 教訓：曾因此差點把「某模組缺測試票」寫進報表，實際早已開好。

### 4. 存量與流量是兩種口徑，不可混用

- **流量**（交付／新增）＝落在上週窗內
- **存量**（各階段張數）＝**產出當下的全量計數**，不受窗限制

兩者混用會得到互相矛盾的數字。報表上分區塊放並標明口徑。

> 教訓：初版把「待驗收 41」寫進報表——那是單頁抽樣裡某一人的數字。
> 全量實查是 97。結論方向沒錯但量級差一倍。

## 工作流程

### Step 1 — 定週界與目標

`--date` 未給時取今天；一律回推到**該週的週一**當作週會日。
由此推出上週（週一 00:00 ~ 週日 24:00，UTC+8）與本週。

`--project` 未給且沒有 `--no-publish` → 呼叫 `list_projects` 列出可選的 project，回報「請帶 `--project` 重跑」後終止，不要自己挑一個；
目標 Project 只決定 Linear 文件放哪，
**查詢一律 workspace 全域**。

### Step 2 — 拉資料

依 `references/query-strategy.md` 平行發查詢。三件事必守：

- **分頁要拉完**：`hasNextPage` 為真就用 cursor 續拉，別只取第一頁就算數。
- **大結果落檔再用 jq／python 處理**，不要塞進對話。落檔與所有衍生檔
  一律放 workspace 根 `.tmp/weekly-report/`（已 gitignore），用完即刪。
- **backlog 類清單（測試中／待驗收／需求中）要帶 title**，票務明細與簡報都要用。

### Step 3 — 建清單（這步決定所有數字）

產出一份 drill dataset（key → {label, note, items[]}），每個 item 至少含
票號、標題、負責人、一句 meta（完成日／停滯天數／期限）。
清單建完才進 Step 4，**不准先寫數字再回頭補清單**。

**落檔** `.tmp/weekly-report/dataset.json`——Step 5 的三個 report-writer 都讀它，
不從對話拿。這是三份產出數字一致的唯一保證。

必備清單見 `references/metrics.md`；其中三組容易做錯：

- **批次結案要拆出來**：結案時間相鄰 ≤3 分鐘、簇大小 ≥5、**且該簇票齡中位數 > 90 天**。
  兩條都要——只看時間會誤殺「一次交付多張」，只看票齡會漏掉簇內剛開的票。
  混在一起會讓「本週完成 N 項」被讀成產能。
- **逾期／到期只計未完成**。含已完成票會虛報（實測 75 vs 37）。
- **流動時間只算實際交付**，含清理批次會製造假的長尾。

**客戶歸戶用 label（名稱用 `list_issue_labels` 查，不寫死），不要用 `project` 欄位**——
實測 `project` 覆蓋率可低到三分之一，拿來歸戶會漏掉大半。

### Step 4 — 算衍生指標

依 `references/metrics.md` 計算：流入／流出／淨變化、各階段存量、
產能 vs 需求（依客戶）、開發段流動時間 vs 驗收段停滯時間、到期風險。

**工作日與假日**（共用 reference）：本週可用人日（工作日 × 人數 − 請假 − 會議時數）、
本週關鍵對外會議（客戶驗收／測試／教育訓練，這些是硬期限）、上週實際工作日。
**「本週押三件事」必須對照可用人日提出——沒有這個對照，押注只是願望。**
拿不到假日／出勤資料時走無假日資料模式並註明，不中止。

**禁用指標**（算了也不要放）——三項，理由與實測數字見 `references/metrics.md`：

| 禁用 | 一句話理由 |
|------|-----------|
| Cycle 完成率 | Cycle 若是全票容器而非 sprint 承諾，完成率永遠偏低，無資訊量 |
| 工時／故事點 | `estimate` 覆蓋率通常偏低，畫出來的數字是編的 |
| 人員票數排名 | 票數 ≠ 工作量，會議上點名會變成防禦性辯論、吃掉決策時間。改報「哪一棒缺人」 |

### Step 5 — 派 `report-writer` 產三份（**平行**）

**主 session 不寫報表。** 三份產出彼此獨立、寫不同檔 → **同一批次一次送出三個 tool call**。

| 產出 | 形態 | 票號 | out_path | 用途 |
|------|------|:----:|---|------|
| 會議簡報 | 單頁 HTML | 只在抽屜裡 | `.tmp/weekly-report/slides-{週會日}.html` | 會議室投影 |
| 每週進度報表 | Markdown（mermaid 圖） | **零票號** | `.tmp/weekly-report/report-{週會日}.md` | 會議文件 |
| 週會票務明細 | Markdown | 全部 | `.tmp/weekly-report/tickets-{週會日}.md` | 會後查證 |

```
subagent_type: "sa-flow:report-writer"
prompt: |
  report_type: {slides-html ｜ weekly ｜ ticket-detail}
  out_path: {上表對應路徑}
  template: ${CLAUDE_PLUGIN_ROOT}/skills/linear-weekly-report/references/outputs.md
  dataset: {workspace 根}/.tmp/weekly-report/dataset.json
  period: 上週 {範圍}／本週 {範圍}；週會日 {日期}
  constraints: |
    禁用指標：Cycle 完成率、工時／故事點、人員票數排名（理由見 metrics.md）
    行文一律用「上週／本週」，**不准出現「下週」**（例外：「下週一逐條對照」指涉會議日）
    存量與流量分區塊放並標明口徑
    「本週押三件事」的優先序與待辦負責人留【人工填】——那是判斷不是資料
    首次執行無前次待辦 → 寫「首場週會，無前次待辦可對照」，不要編
  siblings: |
    {另外兩份的檔名與各自負責的內容}
    三份互相指路（「明細見 X」）但**不互相複製內容**
```

議程固定 30 分鐘八段，**卡點佔最久**（已完成的事不逐項唸）：

```
0–3 上週定調｜3–5 上次待辦兌現｜5–10 各案進度｜10–14 產能與時間
14–22 卡點決策｜22–26 本週承諾｜26–28 臨時動議｜28–30 待辦事項彙整
```

「待辦事項彙整」是全場收斂點：卡點的決定＋承諾＋各案冒出的事，彙成一張
「來源／負責人／期限／完成」表。**能綁票號的綁票號**（下週一可機器判定），
綁不了的（如「找 PO 確認方向」）標【人工判定】，下週一主動問使用者。

**與 `meeting-minutes` 的界線**：本 skill 產的是**會前**簡報與待辦表；會中新增或變更的
待辦由 `sa-flow:meeting-minutes` 記錄（落地位置依該 skill 的發布方式，與本 skill 不同，不要合併）。
下週一「上次待辦兌現」**一律以本 skill 產出的「待辦事項彙整」為對照基準**。

### Step 6 — 複驗（兩道閘門，任一不過不得發布）

**① 數字↔清單一致性**：跑 `scripts/verify_counts.py`，吃 drill dataset 與產出的 HTML，
比對每個可點數字的顯示值與其清單筆數。非零 exit code 即失敗。

三個 agent 的回報也各自含複驗結果，**任一份回報「不建議發布」即失敗**。
腳本與 agent 回報**兩者都要過**——腳本驗 HTML，agent 驗自己那份 Markdown，涵蓋範圍不同。

<law>
**agent 的複驗結果要抽驗。** 隨機挑 2~3 個數字自己對回 `dataset.json`，不照單全收。
</law>

**② 站台收錄**（僅在 docs 有靜態站台建置時）：build 後確認三件事——
產出含簡報 `.html`、與來源 `cmp` 位元相同（確認 JS 與內嵌資料沒被處理掉）、
首頁導覽未出現該目錄（沒誤入導覽）。細節見 `references/publishing.md`。

### Step 7 — 落地

依 `references/publishing.md`：把 agent 產出的 HTML 從 `.tmp/weekly-report/` 複製進 `{docs-root}` 下的週會簡報目錄 `{週會日}.html`
（`{docs-root}` 取自 workspace CLAUDE.md 的 `sdlc-docs-path` 設定，目錄取自專案既有第一階目錄，**該目錄只放 `.html`**）、
兩份 Linear Document 建在目標 Project 下、三份互相指路。
`--no-publish` 時只產檔不發布。

### Step 8 — 回報

輸出三個連結、上週／本週日期範圍、以及「數字↔清單一致性」複驗結果。

## 錯誤處理

| 情境 | 處理 |
|------|------|
| Project 不存在 | 列出現有 Project，請使用者帶正確的 `--project` 重跑，終止 |
| Linear MCP 未設定 | 提示設定 `.mcp.json`，終止 |
| 查詢結果過大無法回傳 | 已自動落檔，改用 jq／python 讀，不要重試縮小欄位 |
| 首次執行、無前次待辦 | 第二節寫「首場週會，無前次待辦可對照」，不要編 |
| 數字與清單不一致 | **不得發布**，回頭查是哪個查詢口徑不同 |

## 使用範例

```bash
sa-flow:linear-weekly-report --project "{專案名稱}"   # 週會日取今天
sa-flow:linear-weekly-report --project "{專案名稱}" --date 2026-09-14   # 補產某週
sa-flow:linear-weekly-report --no-publish             # 只產檔不發布
```

## 排程

搭配 `/schedule` 每週一 08:30 執行：`0 8 * * 1`，指令必須帶 `--project`。
排程產出後仍需人工填「本週押三件事」的優先序與待辦負責人——**那是判斷不是資料**。
