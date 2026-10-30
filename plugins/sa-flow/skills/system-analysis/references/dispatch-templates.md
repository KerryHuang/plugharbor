# Step 3 三路平行派工樣板

`system-analysis` Step 3 的派工 prompt 範本。三路**同一批次一次送出**，
彼此無共用狀態；唯一的串接是 A 路內部（3.1 與 3.3 都寫 `reuse-scan.yml`，不可拆成兩個 agent）。

`{}` 為呼叫端填入值。派工前務必把 `{功能目錄}` 展開成**絕對路徑**——
agent 拿相對路徑會寫錯地方。

---

## A 路：既有程式碼與跨模組影響 → `scout`

```
subagent_type: "sa-flow:scout"
prompt: |
  context: {功能描述與 FRD 摘要}
  keywords: [{Entity 名}, {資料表名}, {功能關鍵字}]
  docs_root: {sdlc-docs-path}
  scan:
    - 相關資料模型（Entity 定義）
    - 相關 API（Controller 路由清單）
    - 相關業務邏輯元件（Handler）
    - 相關資料存取元件（Repository）
    - Light API（選項下拉用的輕量查詢 API）現況
    - 跨模組引用點（Entity 與資料表被引用處）
  out_file: {功能目錄}/analysis/reuse-scan.yml
  format: 每筆標 `source`（檔案路徑）與 `scanned_at`
```

**回報後**：讀 `reuse-scan.yml` 取結論填 SAD §5 能力結論表與 §7 重用分析。
類別名、檔案路徑、行號**留在 yml**，不進 SAD 正文——那些變動速度快於規格生命週期。

---

## B 路：DB 結構 → `scout`（需有唯讀 DB 查詢工具）

```
subagent_type: "sa-flow:scout"
prompt: |
  context: {功能描述與 FRD 摘要}
  keywords: [{涉及資料表清單}]
  db_connection: {目標連線名稱}
  scope: {structure ｜ deep}
  out_file: {功能目錄}/analysis/db-analysis.yml
  format: 首段 `_index:` 列 tables 清單；每筆標 `source` 與 `scanned_at`
```

### `scope` 怎麼選

| 值 | 蒐什麼 | 何時用 |
|---|---|---|
| `structure`（預設） | 欄位、型別、長度、可空性、約束、FK | 一般情況 |
| `deep` | 加做狀態欄位抽樣（`SELECT DISTINCT … GROUP BY`）、狀態碼語意識別、必填語意判斷 | 需求涉及複雜狀態流轉／欄位業務規則不明確／需確認必填語意 |

### 前置：正式環境的取捨

要以**實際資料**佐證行為（`scope: deep` 多半會）時，連線優先選測試／預備環境；
只有正式環境可查時，先告知使用者並取得同意，全程只下 SELECT 且限筆數。
查 schema 結構（`scope: structure`）不受此限。

### 回報後

讀 `db-analysis.yml`，把 `status_columns`、`columns[*].semantic`
整合至 Step 6 資料流分析與 SAD 資料表章節。

發現欄位描述與分析證據不符（錯誤／過時／空白但語意已確立）→
**不中斷分析**；SAD 以證據語意為準並標注。

---

## C 路：現有畫面與 API → `browser-surveyor`（條件觸發）

**觸發條件**：分析涉及既有功能。
`analysis/ui-survey.md` 已涵蓋且未過期 → 直接讀用，**不重派**。

```
subagent_type: "sa-flow:browser-surveyor"
prompt: |
  mode: survey
  url: {系統 URL}
  env_class: {由 URL 判定：test / staging / production / unknown}
  readonly: {production 或判不準一律 true}
  credentials: {登入設定檔絕對路徑，先 `ls` 驗存在}
  targets:
    - {FRD §4 畫面清單逐項：畫面名、怎麼到達}
  out_file: {功能目錄}/analysis/ui-survey.md
  shot_dir: {功能目錄}/analysis/shots
  focus: 畫面結構、欄位、操作流程、**API 端點與參數**（供 §5 資訊流與 §7 重用分析）
  isolated_context: system-analysis-{功能名稱或序號}   # 同 session 派多個時各自不同，例 survey-01／survey-02
```

同 session 可平行派多個瀏覽器 agent，各給不同 `isolated_context`。

### 回報後

勘察結果用於補充 §4 工作流 / §5 資訊流 / §6 資料流 / §7 重用分析。

<law>
**寫入 SAD 前須依 `${CLAUDE_PLUGIN_ROOT}/references/ui-analysis-guide.md` 檔頭對照表轉譯，
不得整段複製**——那是現況擷取，不是分析結論。
</law>

**不要 Read 截圖進 context**——你要的是 `ui-survey.md` 裡的結構化欄位表。

---

## 匯流與失敗處置

三路全部回報齊了才進 Step 4。

| 失敗 | 處置 | 影響 |
|---|---|---|
| A 路（scout 回傳空） | 標「未找到相關元件」，續行 | SAD 中標注需新建 |
| B 路（唯讀 DB 查詢工具不可用） | 記錄警告，跳過 §3.2，以程式碼分析為主 | **報告最終結論降級並註明** |
| C 路（連不上／瀏覽器工具不可用） | 依 agent 回報處置 | 不阻斷——標「未取得畫面證據」續行 |

**沒落檔 = 下游會再查一遍**：`specify-backend` / `dev-readiness` / `verifying-specs`
都直接取用這三份檔，`scanned_at` 早於規格最後修訂時才補查。
