---
name: ticket-weekly-report
description: "產出每週票務進度報表供週會使用：上週回顧＋本週計劃，三份產出（會議簡報 HTML 含可點數字抽屜、週報 Markdown、票務明細 Markdown）。資料經 ticket-ops 的 query 取得，支援 Linear、GitHub Issues。觸發：「週報」「週會報表」「產週會簡報」「ticket weekly report」。日報請用 ticket-daily-report。"
argument-hint: "[--date {YYYY-MM-DD 週會日}] [--out-dir {發布目錄}]"
model: opus
context: fork
---

# 每週票務進度報表

> 非 Claude Code（如 Pi）執行時，先讀 `../../references/harness-terms.md`（相對本檔；Claude Code 為 `${CLAUDE_PLUGIN_ROOT}/references/harness-terms.md`，照字面執行可略過），把 Claude 專屬工具與路徑換成對應項。

本 skill 以 `context: fork` 執行：在不帶對話歷史的 subagent 裡跑，大量查詢結果不留在呼叫方的 context。fork 裡**沒有 `AskUserQuestion`**，不能中途問使用者，缺設定一律報錯終止。

供週會使用的 30 分鐘簡報與存檔文件。與 `lifecycle:ticket-daily-report` 分工：
日報回答「今天會不會出事」，週報回答「上週推進了什麼、本週押什麼」。
**日報有的東西週報不重複**——昨日異動、最高優先逐票追蹤、人員負荷表都不進週報。

- 指標定義與禁用指標：`${CLAUDE_SKILL_DIR}/references/metrics.md`
- 查詢與分頁：`${CLAUDE_SKILL_DIR}/references/query-strategy.md`
- 三份產出的章節與範本：`${CLAUDE_SKILL_DIR}/references/outputs.md`
- 簡報 HTML 骨架（可點數字抽屜）：`${CLAUDE_SKILL_DIR}/references/drawer-template.html`
- 落地：`${CLAUDE_SKILL_DIR}/references/publishing.md`
- 行事曆整合（共用）：`${CLAUDE_PLUGIN_ROOT}/references/report-calendar.md`

## 輸入參數

| 參數 | 必填 | 預設 | 說明 |
|------|:----:|------|------|
| `--date` | 否 | 今天 | 週會日；一律回推到該週週一再推算兩條時間軸 |
| `--out-dir` | 否 | 無 | 發布目錄（相對專案根）；給了才把三份成品複製過去。未給則只留在 `.tmp/weekly-report/` |

## 兩條時間軸（先講清楚，講錯整場會跟著錯）

週會固定週一開，所以報表同時涵蓋兩週：

| 軸 | 範圍 | 用途 |
|----|------|------|
| **上週** | 剛結束那週（一~日） | 回顧：交付、卡點、數據 |
| **本週** | 今天起算那週（一~日） | 計劃：押注、待辦 |

兩者相鄰不重疊。下週一的報表以它的「上週」回頭對照本份的「待辦事項彙整」，一週一循環、不留空窗。
**行文一律用「上週／本週」，不准出現「下週」**（例外：「下週一逐條對照」這種指涉會議日的用法）。

## 不可違反的四條

### 1. 清單是唯一真相

**先產清單，再由清單長度回填數字。禁止兩邊各算各的。**
每一個出現在報表上的統計數字，都必須等於某張票清單的筆數；產出後要程式化複驗，
不一致就是 bug，不是四捨五入。

### 2. 完成用 `completedAt`，不是 `updatedAt`

留言、改 label 都會更新 `updatedAt`，週窗用它算「完成」會虛胖數倍。
完成只認 ticket-ops `query` 回傳的 `completedAt`；沒有回傳就把 `delivered`、`cleanup`、`lead_*` 標「未提供」，不退回 `updatedAt` 近似。

### 3. 判斷「缺票」一律另下全量查詢

不可用 7 天時間窗反推。窗內沒出現只代表「這週沒動過」，不代表不存在。

### 4. 存量與流量是兩種口徑，不可混用

- **流量**（交付／新增）＝落在上週窗內
- **存量**（各階段張數）＝**產出當下的全量計數**，不受窗限制

兩者混用會得到互相矛盾的數字。報表上分區塊放並標明口徑。

## 工作流程

### Step 0 — 讀設定

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/config.py get ticket.tool
```

退出碼 2（缺檔、缺鍵或格式錯誤）→ 輸出 stderr 的建檔指引並終止，不猜值。
本 skill 全程只用抽象階段（`backlog`、`todo`、`in-progress`、`in-review`、`done`、`canceled`），由 `ticket.states` 對照實際名稱。

### Step 1 — 定週界

`--date` 未給時取今天；一律回推到**該週的週一**當作週會日。
由此推出上週（週一 00:00 ~ 週日 24:00，專案所在時區）與本週。

### Step 2 — 拉資料

依 `query-strategy.md`，叫用 `lifecycle:ticket-ops` 的 `query`，**本 skill 不直接呼叫任何票務工具**。三件事必守：

- **分頁要拉完**，別只取第一頁就算數。
- **大結果落檔再用 jq／python 處理**，不要塞進對話。落檔與所有衍生檔一律放專案根 `.tmp/weekly-report/`，用完即刪。
- **backlog 類清單（等驗收／進行中／需求池）要帶標題**，票務明細與簡報都要用。

### Step 3 — 建清單（這步決定所有數字）

產出一份 drill dataset（key → `{label, note, items[]}`），每個 item 至少含
ID、標題、一句 meta（完成日／停滯天數／期限）；有負責人、`url` 就帶。
清單建完才進 Step 4，**不准先寫數字再回頭補清單**。

**落檔** `.tmp/weekly-report/dataset.json`——Step 5 的三個 report-writer 都讀它，
不從對話拿。這是三份產出數字一致的唯一保證。

必備清單見 `metrics.md`；其中三組容易做錯：

- **批次結案要拆出來**：結案時間相鄰 ≤3 分鐘、簇大小 ≥5、**且該簇票齡中位數 > 90 天**。
  兩條都要。混在一起會讓「本週完成 N 項」被讀成產能。缺精確結案時間就標「未偵測」。
- **逾期／到期只計未完成**，且需要 `dueDate`（GitHub 不支援，`dueDate` 恆為空）。沒有此欄就整組標「未提供」。
- **流動時間只算實際交付**，含清理批次會製造假的長尾。

**歸戶用 label**（專案約定的客戶、模組標籤），不用 project／parent 欄位——後者覆蓋率通常不完整。

### Step 4 — 算衍生指標

依 `metrics.md` 計算：流入／流出／淨變化、各階段存量、產能 vs 需求（依歸戶 label）、開發段流動時間 vs 驗收段停滯時間、到期風險。

**行事曆**（共用 reference）：本週可用人日（工作日 × 人數 − 請假 − 會議時數）、本週關鍵對外會議（驗收、教育訓練等硬期限）、上週實際工作日。
**「本週押三件事」必須對照可用人日提出——沒有這個對照，押注只是願望。**
拿不到行事曆時走無行事曆模式並註明，不中止。

**禁用指標**（算了也不要放），理由見 `metrics.md`：

| 禁用 | 一句話理由 |
|------|-----------|
| Cycle／Sprint 完成率 | Cycle 常是全票容器不是承諾，完成率長期個位數，無資訊量 |
| 工時／故事點 | `estimate` 不在 ticket-ops 契約內且覆蓋率通常偏低，畫出來的數字是編的 |
| 人員票數排名 | 票數 ≠ 工作量，會議上點名會變成防禦性辯論。改報「哪一棒缺人」 |

### Step 5 — 派 `report-writer` 產三份（**平行**）

**主 session 不寫報表。** 三份產出彼此獨立、寫不同檔 → **同一批次一次送出三個 tool call**。
**前景派發、不帶 `run_in_background`**：本 skill 跑在 `context: fork`，fork 若用背景派工，可能先結束自己這一輪，回報改送到最上層 session，後面的複驗與落地就沒人做。

| 產出 | 形態 | 票號 | out_path | 用途 |
|------|------|:----:|---|------|
| 會議簡報 | 單頁 HTML | 只在抽屜裡 | `.tmp/weekly-report/slides-{週會日}.html` | 會議室投影 |
| 每週進度報表 | Markdown（mermaid 圖） | **零票號** | `.tmp/weekly-report/report-{週會日}.md` | 會議文件 |
| 週會票務明細 | Markdown | 全部 | `.tmp/weekly-report/tickets-{週會日}.md` | 會後查證 |

```
subagent_type: "lifecycle:report-writer"
prompt: |
  report_type: {slides-html ｜ weekly ｜ ticket-detail}
  out_path: {上表對應路徑的絕對路徑}
  template: ${CLAUDE_SKILL_DIR}/references/outputs.md
  dataset: {專案根}/.tmp/weekly-report/dataset.json
  period: 上週 {範圍}／本週 {範圍}；週會日 {日期}
  constraints: |
    禁用指標：Cycle／Sprint 完成率、工時／故事點、人員票數排名（理由見 metrics.md）
    行文一律用「上週／本週」，**不准出現「下週」**（例外：「下週一逐條對照」指涉會議日）
    存量與流量分區塊放並標明口徑
    「本週押三件事」的優先序與待辦負責人留【人工填】——那是判斷不是資料
    首次執行無前次待辦 → 寫「首場週會，無前次待辦可對照」，不要編
    priority、dueDate 只在 dataset 有提供時才寫；沒有就寫「未提供」，不寫「無」
    簡報 HTML 依 ${CLAUDE_SKILL_DIR}/references/drawer-template.html 的骨架（按鈕 class="drill"、data-k、內嵌 id="drill-data"）
  siblings: |
    {另外兩份的檔名與各自負責的內容}
    三份互相指路（「明細見 X」）但**不互相複製內容**
```

> 派發時 `${CLAUDE_SKILL_DIR}` 要先換成絕對路徑，agent 不會代換變數。

議程固定 30 分鐘八段，**卡點佔最久**（已完成的事不逐項唸）：

```
0–3 上週定調｜3–5 上次待辦兌現｜5–10 各案進度｜10–14 產能與時間
14–22 卡點決策｜22–26 本週承諾｜26–28 臨時動議｜28–30 待辦事項彙整
```

「待辦事項彙整」是全場收斂點：卡點的決定＋承諾＋各案冒出的事，彙成一張
「來源／負責人／期限／完成」表。**能綁票 ID 的綁票 ID**（下週一可機器判定），
綁不了的（如「找 PO 確認方向」）標【人工判定】，下週一主動問使用者。

**與 `lifecycle:meeting-minutes` 的界線**：本 skill 產的是**會前**簡報與待辦表；會中新增或變更的待辦由 `meeting-minutes` 記錄，兩邊不要合併。
下週一「上次待辦兌現」**一律以本 skill 產出的「待辦事項彙整」為對照基準**。

### Step 6 — 複驗（兩道閘門，任一不過不得發布）

**① 數字↔清單一致性**：

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/verify_counts.py .tmp/weekly-report/slides-{週會日}.html .tmp/weekly-report/dataset.json
```

比對每個可點數字的顯示值與其清單筆數，非零 exit code 即失敗。

**② agent 回報**：三個 agent 的回報各自含複驗結果，**任一份回報「不建議發布」即失敗**。
腳本驗 HTML，agent 驗自己那份 Markdown，涵蓋範圍不同，**兩者都要過**。

<law>
**agent 的複驗結果要抽驗。** 隨機挑 2~3 個數字自己對回 `dataset.json`，不照單全收。
</law>

### Step 7 — 落地

依 `publishing.md`。有 `--out-dir` 才複製；沒給就停在 `.tmp/weekly-report/` 並在回報講明。
本 skill 不把報表寫進票務工具、不 commit、不 push。

### Step 8 — 回報

輸出三份檔案路徑、上週／本週日期範圍、「數字↔清單一致性」複驗結果、dataset 缺哪些選配欄位（`completedAt`、`createdAt`、`priority`、`dueDate`）。

## 錯誤處理

| 情境 | 處理 |
|------|------|
| `ticket.tool` 設定缺或錯 | 輸出建檔指引，終止 |
| 票務工具 MCP／CLI 不可用 | 報 ticket-ops 回的缺什麼，終止 |
| 查詢結果過大無法回傳 | 已自動落檔，改用 jq／python 讀，不要重試縮小欄位 |
| 首次執行、無前次待辦 | 第二節寫「首場週會，無前次待辦可對照」，不要編 |
| 數字與清單不一致 | **不得發布**，回頭查是哪個查詢口徑不同 |

## 使用範例

```text
lifecycle:ticket-weekly-report                         # 週會日取今天
lifecycle:ticket-weekly-report --date 2026-09-14        # 補產某週
lifecycle:ticket-weekly-report --out-dir docs/reports/weekly
```

## 排程

搭配 `/schedule` 每週一 08:30 執行：`0 8 * * 1`。
排程產出後仍需人工填「本週押三件事」的優先序與待辦負責人——**那是判斷不是資料**。
