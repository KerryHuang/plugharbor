# 批次分流流程

輸入是一批回饋（會議記錄、需求清單）。目標：逐項對照現況，產出可交接開票的分類清單。填「會議記錄（`lifecycle:meeting-minutes`）」與「開票（`lifecycle:ticket-create`）」之間的缺口。

## 0. 輸入與前置

- 取得輸入：會議記錄路徑，或使用者貼入的清單。無輸入 → 請使用者提供，終止。
- 後面查既有票（`lifecycle:ticket-ops` 的 `query`）與交棒開票都走 ticket-ops；設定缺時它會自己問。
- 先確認變體與術語（客戶或場域變體、版本命名對照）。不確定就查證或問，不憑字面分類。

## 1. 拆解 items

拆成離散、可分類的 item，依模組歸群（同模組放一起）。純現況描述、非需求者不列，在清單裡標註即可。

## 2. 三路勘察（並行 Explore）

先用 `AskUserQuestion` 問後端、前端、規格文件各自的路徑（可從專案文件或目錄結構推導預設值當選項，不寫死）。再在**同一則訊息**並行派 3 個 `Explore`（medium 廣度），把依模組拆好的 item 清單交給三路：

- **後端**：每項為「已實作／部分／未實作／疑似壞掉」，附 `檔案:行號`。聚焦資料與邏輯面：欄位是否存在、預設帶入、卡控、狀態機、查詢維度、聚合值。
- **前端**：每項在畫面與互動面的現況與元件證據。特別注意版本差異（同功能不同版可能落差）。
- **規格文件**：每個主題是否已有需求、設計、變更文件或票號，回報路徑與票號。

要求逐項輸出「item → 現況＋證據」，不確定標未知，不臆造。

收斂：主 session 交叉比對三份。後端有、前端無（或反之）＝部分；規格有鏈＝標既有票；多處同症狀＝合併調查。

## 3. 有效性＋分類

依 `${CLAUDE_SKILL_DIR}/references/classification.md`：每項先判有效性類別，有效者再分 Bug／Enhancement／Feature，附證據與信心度，套用防呆。標「需新建」前查規格目錄＋票務系統。

## 4. 待釐清（可選第二意見）

單一事實來源、狀態機、聚合根、領域邊界疑點列入「待釐清」。先問使用者要不要請第二意見 agent 審閱，說要才派（唯讀，以分類結論與勘察證據為唯一依據，做法同 `${CLAUDE_PLUGIN_ROOT}/skills/meeting-minutes/references/second-opinion.md`）。

## 5. 產出分類清單（派 `report-writer`）

分類判定由主 session 完成，結論整理成 dataset 檔，派 agent 依範本產出：

```
subagent_type: "lifecycle:report-writer"
prompt: |
  report_type: issue-list
  out_path: {落檔絕對路徑}
  template: ${CLAUDE_PLUGIN_ROOT}/skills/triage/references/table-format.md
  dataset: {分類結論彙整檔絕對路徑}
  constraints: |
    分類由呼叫端判定，不得自行改判
    每表含「優先順序／已完成」欄；同模組相鄰；ID 連續（如 ENH-01…）
    「已實作」防呆表要保留「先實機確認、勿逕自開發」的標註
    PO 註記逐字保留，不得改寫
  siblings: 無
```

落檔預設：放專案既有文件目錄中對應的模組或功能位置；沒有對應位置（如單一客戶的導入回饋）→ 先問使用者放哪。不在文件目錄第一階新建目錄（依 `${CLAUDE_PLUGIN_ROOT}/references/shared-preludes.md` §Step 0.5）。

## 6. PO 逐項裁決迭代

- 逐項與 PO 確認分類、優先序、狀態。
- PO 直接改檔時：以當前檔為準，只補自己被蓋掉的改動，保留 PO 所有註記。
- ID 重編（連續化）時同步更新所有交叉引用。

## 7. 交棒

清單定案（待釐清皆定案）後交棒開票：叫用 `lifecycle:ticket-create`。對齊既有票者以變更需求併入，不另開重複票。

## 收尾條件

全部成立才算完成（見 `${CLAUDE_PLUGIN_ROOT}/references/dispatch-conventions.md` §八）：

1. 每個 item 都有有效性類別；有效者有分類與優先序，無一未分類。
2. 清單已落檔，路徑符合 §5 規則。
3. ID 連續，所有交叉引用（§1、待釐清、跨表）都已同步。
4. 待釐清項目皆已定案；仍有未定案項時不得交棒開票。
5. 既有票對照已做：標「需新建」的項目都查過規格＋票務系統。

## 錯誤處理

| 情境 | 處理 |
|------|------|
| 勘察路徑不明 | `AskUserQuestion` 補問後端、前端、規格路徑 |
| Explore 回未知 | 標「待實機／待查」，不臆造分類 |
