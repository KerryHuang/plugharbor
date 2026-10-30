---
name: issue-triage
description: "把一批回饋（會議記錄／需求清單）逐項對照現況 codebase 分類成 Bug／Enhancement／Feature，標既有票與規格鏈，產出可開票的問題清單。觸發：「問題清單」「回饋分類」「issue triage」。"
argument-hint: "[會議記錄路徑 或 貼入回饋清單]"
model: sonnet
---

# 問題清單分流（issue-triage）

> 非 Claude Code（如 Pi）執行時，先讀 `../../references/harness-terms.md`（相對本檔；Claude Code 為 `${CLAUDE_PLUGIN_ROOT}/references/harness-terms.md`，照字面執行可略過），把 Claude 專屬工具與路徑換成對應項。

把一批回饋逐項對照**現況 codebase** 分類成 **Bug／Enhancement／Feature**、標**既有票／規格鏈**，產出可交接開票的分類問題清單。填 `meeting-minutes`（產記錄）與 `linear-create`（開票）之間的缺口。

**互動原則**：互動詢問依 `${CLAUDE_PLUGIN_ROOT}/references/shared-preludes.md` §互動詢問規範。PO 逐項裁決時**只補自己的改動、保留 PO 註記**。

## 0. 輸入與前置

- 取得輸入：會議記錄路徑，或使用者貼入的回饋／需求清單。
- **先確認變體與術語**（分類建立在正確前提）：客戶／場域變體（如 B2B vs B2C 版本）、版本命名對照（如標準版／進階版／lite）。不確定就查證或問，勿憑字面分類。

## 1. 拆解 items

把回饋拆成離散、可分類的 item，**依模組歸群**（同模組放一起）。純現況描述、非需求者不列（標註即可）。

## 2. 三路 grounding（並行 Explore）

依 `${CLAUDE_PLUGIN_ROOT}/skills/issue-triage/references/grounding.md`：
- **先問**後端／前端／docs 的路徑（不寫死）。
- 並行派 3 個 `Explore`：判各項**現況**（已實作／部分／未實作／疑似壞掉）＋**既有票／規格鏈**。

## 3. 分類 + 防呆

依 `${CLAUDE_PLUGIN_ROOT}/skills/issue-triage/references/classification.md`：
- **Bug**＝現行功能異常｜**Enhancement**＝改既有｜**Feature**＝全新無實作。
- **防呆（核心）**：客戶說「缺少」的常已實作（版本差異／capability flag／測試點）→ 標「先實機確認、勿逕自開發」，別當 Feature。
- **既有票／規格鏈對照**：標「需新建」前查 docs＋票務系統（如 Linear），避免誤判。

## 4. 待釐清（可選顧問審閱）

SoT／狀態機／聚合根／domain 邊界疑點列「待釐清」。**先問使用者要不要請 `sa-flow:domain-advisor` 審閱**，說要才派（`mode: review`，同 meeting-minutes 做法）。

## 5. 產出分類問題清單（**派 `report-writer`**）

分類判定（Bug／Enhancement／Feature、優先序、既有票對照）由主 session 完成後，
把結論放 `dataset`，派 agent 依範本產出：

```
subagent_type: "sa-flow:report-writer"
prompt: |
  report_type: issue-list
  out_path: {落檔絕對路徑，見下}
  template: ${CLAUDE_PLUGIN_ROOT}/skills/issue-triage/references/table-format.md
  dataset: {分類結論彙整檔絕對路徑}
  constraints: |
    分類由呼叫端判定，**不得自行改判**
    每表含「優先順序／已完成」欄；**同模組相鄰**；ID 連續（如 ENH-01…）
    §1 已實作防呆表要保留「先實機確認、勿逕自開發」的標註
    PO 註記逐字保留，不得改寫
  siblings: 無
```

落檔規則見下。
**落檔預設**：屬既有模組 → `{docs-root}/{模組}/{功能}/`；不屬任何既有模組（如單一客戶的導入回饋）→ 先問使用者放哪。可由使用者覆寫，但**不得在 docs 第一階新建目錄**（模組目錄取自 `{docs-root}` 既有第一階目錄）：
- 統計摘要 → §1 已實作防呆表 → Bug／Enhancement／Feature 三分類表 → 待釐清表 → 既有票對照 → 建議下一步。
- 每表含**優先順序／已完成**欄；**同模組相鄰**；ID 連續（如 ENH-01…）。

## 6. PO 逐項裁決迭代

- 逐項與 PO 確認分類／優先／狀態。
- PO 直接改檔（overwrite）時：**讀當前檔為準、只補自己被蓋掉的改動、保留 PO 所有註記**。
- ID 重編（連續化）時**同步更新所有交叉引用**（§1、待釐清、跨表引用）。

## 7. 交棒

清單定案（待釐清皆定案）後 → 交棒 `sa-flow:linear-create` 開票；**對齊既有票以 CR 併入，勿另開重複票**。

## 收尾條件

全部成立才算完成（見 `${CLAUDE_PLUGIN_ROOT}/references/dispatch-conventions.md` §八）：

1. 每個 item 都有分類（Bug／Enhancement／Feature）與優先序，**無一未分類**
2. 清單已落檔，路徑符合 §5 規則（**不得在 docs 第一階新建目錄**）
3. ID 連續且所有交叉引用（§1、待釐清、跨表）都已同步更新
4. 待釐清項目**皆已定案**——仍有未定案項時不得交棒 `linear-create`
5. 既有票對照已做：標「需新建」的項目都查過 docs ＋ Linear

## 錯誤處理

| 情境 | 處理 |
|------|------|
| 無輸入 | 請使用者提供會議記錄路徑或貼入回饋清單，否則終止 |
| grounding 路徑不明 | `AskUserQuestion` 補問後端／前端／docs 路徑 |
| Explore 回未知 | 標「待實機／待查」，不臆造分類 |
