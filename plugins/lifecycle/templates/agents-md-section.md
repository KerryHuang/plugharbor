<!-- plugharbor-lifecycle begin -->
## 設計與實作流程（lifecycle）

- 設計文件放 `.plugharbor/lifecycle.yml` 的 `spec.dir`（預設 `docs/superpowers/specs/`），檔名 `YYYY-MM-DD-<slug>-design.md`，進版控。
- 七節各用 `##`，依序：起因、目標（含非目標、反目標）、限制、做法比較、決定、驗收、留給 builder；開頭 `# <功能>`，下一行 `票號：#n · 狀態：草稿 · yyyy-mm-dd`（沒票寫「無」）。專案額外章節放「留給 builder」之前。
- 決定一條一行：`- D-01 <決定>；否決：<選項與原因>（拍板：使用者／顧問／證據／自行決定）`。
- 腦力激盪、寫計畫要問使用者設計題前，先整批交 `lifecycle:domain-advisor` 分流（`mode: triage`，見 lifecycle 的 `consultant-desk.md`），只問它轉交的；它定的拍板寫「顧問，待使用者確認」並在回報列出。
- 驗收每條關鍵規則一正例一反例、預期只寫看得到的事實；欄位內容一律用清單，最小案例：

  ```
  ## 驗收
  ### AC-01 儲存後顯示成功 [ui]
  #### 前置條件
  - 已登入
  #### 步驟
  1. 開啟訂單 SO-001，按「儲存」
  #### 預期
  - 顯示「儲存成功」
  ```

- 實作計畫放 `docs/superpowers/plans/`，進版控；最後一個 task 是 lifecycle 收尾（`lifecycle:implement` 的 after.md）：驗收對照、功能清單打勾、同步票。
- 計畫寫完做計畫審查（跨家族 CLI 優先，沒有就全新 subagent，再沒有自審並標「自審」），必修修完才開工。
- 計畫寫完說「開始實作」交 `lifecycle:implement`：沿用計畫、補審查與收尾，不重寫計畫。
- Git Flow 專案發版交 `lifecycle:release`。
<!-- plugharbor-lifecycle end -->
