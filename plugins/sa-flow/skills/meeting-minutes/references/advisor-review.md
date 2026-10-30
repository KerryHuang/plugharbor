# 顧問審閱（meeting-minutes 整理階段）

於整理階段「收斂產出」之後觸發。**先問使用者要不要上，說要才派。**
`domain-advisor` 唯讀，只回饋建議；主 session 負責整併落檔。

## 1. 詢問（一定先問）

用 `AskUserQuestion` 問一題：

> 這場要不要請 domain-advisor 審一遍會議記錄？

選項：
- 要，請顧問審
- 不用（預設）

回答「不用」→ 跳過本流程，直接回報檔案路徑。

## 2. 派發（回答「要」才做）

派 `subagent_type="sa-flow:domain-advisor"`，`mode: review`，以**完整會議記錄**為 context。
本流程無 scout evidence_bundle——**以會議記錄內容本身為唯一證據來源**，明寫在 prompt。

```
mode: review
context: |
  {完整會議記錄 markdown 內容}
審查重點：從通用 Domain 視角，指出隱含需求、邊界問題、
  資料 SoT、狀態機、整合邊界、待釐清清點。以會議記錄為唯一證據來源，勿臆測記錄外事實。
```

> 註：若 `domain-advisor` 的 review 模式要求 `evidence_bundle`，以會議記錄充當。

## 3. 整併落檔

主 session 收回饋，整併寫進記錄檔「顧問建議 / 待釐清」區塊：

- **隱含需求**：條列。
- **domain 邊界 / 待釐清**：條列，每條簡述理由。
- **建議後續**：若顧問建議接需求流程（explore / requirement），**只列建議、不自動交棒**。

顧問為唯讀 subagent、不落檔；整併與寫檔一律由主 session 執行。
