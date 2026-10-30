# Step 2 背景調查派工樣板

`requirement` Step 2 的派工 prompt 範本。**主 session 不自己掃 codebase、不自己查 DB、不自己開瀏覽器**
——三路用不同工具、寫不同檔，**同一批次一次送出**。

`{}` 為呼叫端填入值；`{功能目錄}` 一律展開成**絕對路徑**。

> **FRD 階段的勘察刻意比 SAD 淺**：這裡要回答的是「有沒有類似的東西、涉及哪些表、
> 舊系統怎麼做」，供業務層判斷；完整的重用盤點與資料模型分析是 `system-analysis` Step 3 的事。
> 派工時把範圍講清楚，不要讓 agent 做成完整勘察。

---

## A 路：既有實作與舊系統對照 → `scout`

涵蓋 2.1（既有規格書／需求文件／Entity／Controller／Handler）與 2.3（舊系統業務規則）。

```
subagent_type: "sa-flow:scout"
prompt: |
  context: {使用者的需求描述 ／ 探索摘要重點}
  keywords: [{功能關鍵字}, {推測的 Entity 名}, {推測的資料表名}]
  docs_root: {sdlc-docs-path}
  scope: FRD 階段的淺勘——只要回答「有沒有既有的同類東西、大致涉及什麼」，
         不做完整重用盤點（那是 system-analysis Step 3 的範圍）
  scan:
    - docs 內同義／相近功能的既有規格書與需求文件（**含不同模組目錄、檔名不同義者**）
    - 相關 Domain Entity 與 API Controller（只要清單與一句用途）
    - 舊系統（FoxPro／ERP 等）對應功能的業務規則
  out_file: {功能目錄}/analysis/background-scan.yml
  format: 每筆標 `source`（檔案路徑）與 `scanned_at`；找不到就寫「未找到」，不要臆造
```

<law>
**「這功能需新建」不能只靠 A 路的回報下結論。** 說新建之前必須另外查
Graphify 圖譜（可用者；同義文件常散在不同模組目錄、檔名不同義，grep 檔名會漏）與 Linear 既有票。
</law>

---

## B 路：資料庫結構 → `scout`（條件觸發）

**觸發**：需求涉及既有資料表，且專案提供唯讀 DB 查詢工具。純新表、純流程調整、無 DB 工具不派。

```
subagent_type: "sa-flow:scout"
prompt: |
  context: {使用者的需求描述}
  keywords: [{推測涉及的資料表清單}]
  db_connection: {目標連線名稱}
  scope: 只勘察資料表結構（欄位、型別、長度、可空、FK），不撈資料、不勘察 codebase 與文件
  out_file: {功能目錄}/analysis/db-analysis.yml
  format: 首段 `_index:` 列 tables 清單；每筆標 `source` 與 `scanned_at`
```

FRD 階段只查結構——FRD 不寫資料表結構，這裡查是為了
**驗證業務假設站不站得住**（欄位存在嗎、能不能為空、長度夠不夠）。
需要實際資料佐證業務規則時，另行向使用者確認後再抽樣，且只下 SELECT。

產出 `analysis/db-analysis.yml` 供下游 SAD／BFS 沿用——**SAD Step 3 會讀它並只補未涵蓋的部分**。

---

## C 路：現有畫面 → `browser-surveyor`（條件觸發）

**觸發**：需求涉及既有功能（調整、擴充、參考現有操作）。
`analysis/ui-survey.md` 已涵蓋 → 直接讀用，**不重問 URL、不重跑勘察**。

```
subagent_type: "sa-flow:browser-surveyor"
prompt: |
  mode: survey
  url: {使用者提供的 URL}
  env_class: {由 URL 判定}
  readonly: {production 或判不準一律 true}
  credentials: {登入設定檔絕對路徑，先 `ls` 驗存在}
  targets:
    - {要看的既有畫面逐項：畫面名、怎麼到達}
  out_file: {功能目錄}/analysis/ui-survey.md
  shot_dir: {功能目錄}/analysis/shots
  focus: 操作動線、業務層欄位語意、現行做法與痛點的具體樣子
  isolated_context: requirement-{功能名稱或序號}   # 同 session 派多個時各自不同，例 survey-01／survey-02
```

同 session 可平行派多個瀏覽器 agent，各給不同 `isolated_context`。

<law>
**勘察結果是現況擷取，不是需求。** 寫進 FRD 前須依
`${CLAUDE_PLUGIN_ROOT}/references/ui-analysis-guide.md` 檔頭對照表轉譯，**不得整段複製**。
用於：補充 §4 操作表與業務層欄位、驗證 §5 欄位名稱與型別、豐富 §3 操作步驟。
</law>

**不要 Read 截圖進 context**。

---

## 匯流與失敗處置

三路全部回報齊了才進 Step 3。**任一路失敗都不阻斷 FRD 撰寫**：

| 失敗 | 處置 |
|---|---|
| A 路回傳「未找到」 | 照常續行；但「需新建」的結論仍要過上方 `<law>` 的 Graphify ＋ Linear 查證 |
| B 路 DB 工具不可用 | 跳過，涉及資料的業務假設在 FRD §8 開放議題標「未經 DB 驗證」 |
| C 路連不上／瀏覽器工具不可用 | 依 agent 回報處置；標「未取得畫面證據」續行，§4 改依探索摘要與對焦素材推導 |
