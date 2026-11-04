---
name: ticket-report
description: "產出票務進度報表，兩個模式：daily（每日：走看板找卡點、只列今天變壞的事、票號另出明細）、weekly（每週：上週回顧＋本週計劃，簡報 HTML 含可點數字抽屜、週報 Markdown、票務明細）。資料經 ticket-ops 的 query 取得，不綁特定票務工具。Use when 「日報」「今天卡在哪」「週報」「週會報表」「ticket report」。"
argument-hint: "{daily|weekly} [--date {YYYY-MM-DD}] [--out-dir {發布目錄}]"
disable-model-invocation: true
model: sonnet
context: fork
---

# 票務進度報表

> 非 Claude Code（如 Pi）執行時，先讀 `../../references/harness-terms.md`（相對本檔；Claude Code 為 `${CLAUDE_PLUGIN_ROOT}/references/harness-terms.md`，照字面執行可略過），把 Claude 專屬工具與路徑換成對應項。

本 skill 以 `context: fork` 執行：在不帶對話歷史的 subagent 裡跑，大量查詢結果不留在呼叫方的 context。fork 裡**沒有 `AskUserQuestion`**，不能中途問使用者，缺設定一律報錯終止。

兩個模式回答不同的問題，不要混用：

| 模式 | 回答 | 流程檔 |
|------|------|--------|
| `daily` | 今天有什麼會出包（不是「昨天發生了什麼」） | `${CLAUDE_SKILL_DIR}/references/daily-flow.md` |
| `weekly` | 上週推進了什麼、本週押什麼（供週會使用） | `${CLAUDE_SKILL_DIR}/references/weekly-flow.md` |

日報有的東西週報不重複：昨日異動、最高優先逐票追蹤、人員負荷表都不進週報。日報不做趨勢、產能對照、承諾兌現。

## 輸入

| 參數 | 必填 | 預設 | 說明 |
|------|:----:|------|------|
| 第一個參數 | 是 | 無 | `daily` 或 `weekly`；缺或不合法 → 列出兩個模式後終止（fork 裡不能問） |
| `--date` | 否 | 今天 | daily：報表日。weekly：週會日，一律回推到該週週一 |
| `--out-dir` | 否 | 無 | 發布目錄（相對專案根）；給了才把成品複製過去，未給則只留在 `.tmp/{daily,weekly}-report/` |

## 共同的四條不可違反

### 1. 清單是唯一真相

先產清單，數字由清單長度回填，禁止兩邊各算各的。每個統計數字都必須等於某張票清單的筆數，發布前複驗；不一致就是 bug，不是四捨五入。數字不可信的報表，讀的人會停止相信它。

### 2. 不抽樣，拉全量

查詢經 `lifecycle:ticket-ops` 的 `query`，要求它分頁拉完；結果大時它會落檔並回傳路徑，改用 jq／python 讀，落檔與衍生檔一律放專案根 `.tmp/{daily,weekly}-report/`。**本 skill 不直接呼叫任何票務工具。** 只取第一頁會讓數字系統性偏低。

### 3. 完成時間只認 `completedAt`

完成與交付只認 ticket-ops 回傳的 `completedAt`；沒有回傳就把相關清單標「未提供」，不拿 `updatedAt` 冒充（留言、改 label 都會更新它，會虛胖數倍）。

### 4. 存量與流量是兩種口徑

- **流量**：落在窗內（交付、新增、階段變更）。
- **存量**：產出當下的全量計數，不受窗限制（各階段張數）。

混用會得到互相矛盾的數字。報表上分區塊放並標明口徑。

## 共同規則

- **階段**：全程只用抽象階段 `backlog`、`todo`、`in-progress`、`in-review`、`done`、`canceled`，由 `ticket.states` 對照實際名稱；不寫任何工具專屬的狀態名。
- **日期與工作日**：算法與假日降級見 `${CLAUDE_PLUGIN_ROOT}/references/report-calendar.md`；拿不到行事曆時走無行事曆模式並在報表註明，不中止。
- **批次結案要拆出來**：結案時間相鄰 ≤3 分鐘聚類、簇大小 ≥5、**且該簇票齡中位數 > 90 天**，兩條都要。只看時間會誤殺真交付，只看票齡會漏掉簇內剛開的票。缺精確結案時間就標「未偵測」。
- **停滯天數要驗證來源可信度**：批次操作會一次重設大批票的 `updatedAt`。先看最後異動日分布，單日佔比 >30% 即為批次痕跡，該日的票停滯天數只是下限；此時老化訊號標「本日不可用」並說明原因，不假裝能判斷。天數一律換算工作日。
- **歸戶用 label**（專案約定的客戶、模組標籤），不用 parent／project 欄位，後者覆蓋率通常不完整；用前先看覆蓋率，過低就在資料警告註明。
- **禁用指標**：Cycle／Sprint 完成率、工時／故事點、人員票數排名（理由見 `${CLAUDE_SKILL_DIR}/references/metrics.md` 與 `signal-logic.md`）。
- **選配欄位**（`assignee`、`createdAt`、`completedAt`、`priority`、`dueDate`）依後端能力回傳；未提供就寫「未提供」，不寫「無」或 0。

## 共同工作流程骨架

1. **讀設定**：`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/config.py get ticket.tool`；退出碼 2 → 輸出 stderr 的建檔指引並終止，不猜值。
2. **定日期**，3. **拉資料**（全量，無相依的查詢同批發出），4. **建清單並落檔** `dataset.json`（key → `{label, note, items[]}`，每個 item 至少含 ID、標題、一句 meta；有負責人與 `url` 就帶），5. **算指標／判燈號**，6. **派 `lifecycle:report-writer` 產出**（平行、前景派發、不帶 `run_in_background`：fork 若用背景派工可能先結束這一輪，回報改送到最上層，後面的複驗就沒人做），7. **複驗**，8. **落地**，9. **回報**。

各步驟的具體做法（查詢清單、燈號、產出份數與範本）在對應模式的流程檔。派發 report-writer 時，prompt 裡的路徑變數要先換成絕對路徑，agent 不會代換。

**agent 的複驗結果要抽驗，不是照單全收**：隨機挑 2～3 個數字自己對回 `dataset.json`。任一份回報「不建議發布」→ 不得發布，找出不一致處修正 `dataset.json` 或重派該份。

## 落地與界線

- 報表每次新建、不覆蓋，檔名帶日期；前一份是隔次判斷「變壞了沒」與兌現待辦的基準。
- 有 `--out-dir` 才複製過去；目錄不存在就停下回報，不自建。逐檔報告實際落地路徑。weekly 另依 `publishing.md`。
- 本 skill 不把報表寫進票務工具、不 commit、不 push。
- 與 `lifecycle:meeting-minutes` 的界線：weekly 產的是**會前**簡報與待辦表；會中新增或變更的待辦由 meeting-minutes 記錄，兩邊不合併。

## 錯誤處理

| 情境 | 處理 |
|------|------|
| 模式缺或不合法 | 列出 `daily`、`weekly`，終止 |
| `ticket.tool` 設定缺或錯 | 輸出建檔指引，終止 |
| 票務工具不可用 | 報 ticket-ops 回的缺什麼，終止 |
| 查詢結果過大 | 已自動落檔，用 jq／python 讀，不要砍欄位重試 |
| 查詢可能被截斷 | 報表頂端用警語標明，受影響數字標「≥」，不當完整結果交出 |
| 行事曆拿不到 | 走無行事曆模式並註明，不中止 |
| 數字與清單不一致 | **不得發布**，回頭查是哪個查詢口徑不同 |

## 使用範例

```text
lifecycle:ticket-report daily
lifecycle:ticket-report daily --date 2026-09-08 --out-dir docs/reports/daily
lifecycle:ticket-report weekly --out-dir docs/reports/weekly
```

排程用 `/schedule`：daily 每個工作日 09:00（`0 9 * * 1-5`）、weekly 每週一 08:30（`0 8 * * 1`）。排程產出後，daily 第三節的決策人與 weekly「本週押三件事」的優先序、待辦負責人仍需人工填，那是判斷不是資料。
