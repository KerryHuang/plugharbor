# weekly 模式流程

供週會使用的 30 分鐘簡報與存檔文件。共同規則（清單即真相、全量、`completedAt`、口徑、批次結案、禁用指標）見 SKILL.md。本檔只寫週報特有的部分。

- 指標定義與禁用指標：`${CLAUDE_SKILL_DIR}/references/metrics.md`
- 查詢與分頁：`${CLAUDE_SKILL_DIR}/references/weekly-query.md`
- 三份產出的章節與範本：`${CLAUDE_SKILL_DIR}/references/weekly-outputs.md`
- 簡報 HTML 骨架（可點數字抽屜）：`${CLAUDE_SKILL_DIR}/references/drawer-template.html`
- 落地：`${CLAUDE_SKILL_DIR}/references/publishing.md`
- 行事曆：`${CLAUDE_PLUGIN_ROOT}/references/report-calendar.md`

## 兩條時間軸（講錯整場會跟著錯）

週會固定週一開，所以報表同時涵蓋兩週：

| 軸 | 範圍 | 用途 |
|----|------|------|
| **上週** | 剛結束那週（一至日） | 回顧：交付、卡點、數據 |
| **本週** | 今天起算那週（一至日） | 計劃：押注、待辦 |

兩者相鄰不重疊。下週一的報表以它的「上週」回頭對照本份的「待辦事項彙整」，一週一循環、不留空窗。**行文一律用「上週／本週」，不准出現「下週」**（例外：「下週一逐條對照」指涉會議日）。

## 週報特有的規則

- **判斷「缺票」一律另下全量查詢**，不可用 7 天時間窗反推；窗內沒出現只代表這週沒動過。
- **逾期、到期只計未完成**，且需要 `dueDate`（GitHub 不支援，恆為空）；沒有此欄整組標「未提供」。
- **流動時間只算實際交付**，含清理批次會製造假的長尾。
- **backlog 類清單（等驗收、進行中、需求池）要帶標題**，票務明細與簡報都要用。

## 步驟

### 1. 定週界

`--date` 未給取今天；一律回推到該週週一當作週會日，推出上週（週一 00:00 至週日 24:00，專案所在時區）與本週。

### 2. 拉資料

依 `weekly-query.md` 叫用 `lifecycle:ticket-ops` 的 `query`：分頁拉完、大結果落檔再處理、無相依查詢同批發出。

### 3. 建清單（這步決定所有數字）

產出 drill dataset（key → `{label, note, items[]}`），清單建完才進下一步，不准先寫數字再回頭補清單。**落檔** `.tmp/weekly-report/dataset.json`——三個 report-writer 都讀它，這是三份產出數字一致的唯一保證。必備清單見 `metrics.md`。

### 4. 算衍生指標

依 `metrics.md`：流入／流出／淨變化、各階段存量、產能 vs 需求（依歸戶 label）、開發段流動時間 vs 驗收段停滯時間、到期風險。

行事曆（共用 reference）：本週可用人日（工作日 × 人數 − 請假 − 會議時數）、本週關鍵對外會議（驗收、教育訓練等硬期限）、上週實際工作日。**「本週押三件事」必須對照可用人日提出——沒有這個對照，押注只是願望。** 拿不到行事曆時走無行事曆模式並註明。

### 5. 派 `report-writer` 產三份（平行）

主 session 不寫報表。三份寫不同檔，同一批次一次送出三個 tool call，前景派發：

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
  template: {絕對路徑}/references/weekly-outputs.md
  dataset: {專案根}/.tmp/weekly-report/dataset.json
  period: 上週 {範圍}／本週 {範圍}；週會日 {日期}
  constraints: |
    禁用指標：Cycle／Sprint 完成率、工時／故事點、人員票數排名（理由見 metrics.md）
    行文一律用「上週／本週」，不准出現「下週」（例外：「下週一逐條對照」指涉會議日）
    存量與流量分區塊放並標明口徑
    「本週押三件事」的優先序與待辦負責人留【人工填】——那是判斷不是資料
    首次執行無前次待辦 → 寫「首場週會，無前次待辦可對照」，不要編
    priority、dueDate 只在 dataset 有提供時才寫；沒有就寫「未提供」，不寫「無」
    簡報 HTML 依 {絕對路徑}/references/drawer-template.html 的骨架（按鈕 class="drill"、data-k、內嵌 id="drill-data"）
  siblings: |
    {另外兩份的檔名與各自負責的內容}
    三份互相指路（「明細見 X」）但不互相複製內容
```

議程固定 30 分鐘八段，**卡點佔最久**（已完成的事不逐項唸）：

```
0–3 上週定調｜3–5 上次待辦兌現｜5–10 各案進度｜10–14 產能與時間
14–22 卡點決策｜22–26 本週承諾｜26–28 臨時動議｜28–30 待辦事項彙整
```

「待辦事項彙整」是全場收斂點：卡點的決定＋承諾＋各案冒出的事，彙成一張「來源／負責人／期限／完成」表。能綁票 ID 的綁票 ID（下週一可機器判定），綁不了的（如「找 PO 確認方向」）標【人工判定】，下週一主動問使用者。下週一「上次待辦兌現」一律以本流程產出的「待辦事項彙整」為對照基準。

### 6. 複驗（兩道閘門，任一不過不得發布）

**① 數字與清單一致性**：

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/verify_counts.py .tmp/weekly-report/slides-{週會日}.html .tmp/weekly-report/dataset.json
```

比對每個可點數字的顯示值與其清單筆數，非零 exit code 即失敗。

**② agent 回報**：三個 agent 的回報各自含複驗結果，任一份「不建議發布」即失敗。腳本驗 HTML，agent 驗自己那份 Markdown，涵蓋範圍不同，兩者都要過。並依 SKILL.md 抽驗數字。

### 7. 落地與回報

依 `publishing.md`。回報：三份檔案路徑、上週／本週日期範圍、數字與清單一致性複驗結果、dataset 缺哪些選配欄位（`completedAt`、`createdAt`、`priority`、`dueDate`）。

首次執行、無前次待辦時，第二節寫「首場週會，無前次待辦可對照」，不要編。
