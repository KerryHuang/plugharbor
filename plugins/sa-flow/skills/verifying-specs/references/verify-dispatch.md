# 五維度平行驗證派工樣板

`verifying-specs` Task 2~6 的派工。五個維度**彼此獨立、都不寫檔**（結果進回報），
用 `general-purpose`（`model: sonnet`）**同批次一次送出**。

> 為什麼不新建專用 agent：這五個維度的差異全在「查什麼」，行為完全相同（讀規格、
> 對照現況、回缺失清單）。差異是輸入不是行為——**沒有素材性質不同的理由就不要拆定義**。

## 共用 prompt 骨架

```
subagent_type: "general-purpose"
model: sonnet
prompt: |
  你是規格驗證的單一維度檢查員。只查指定維度，不擴散到其他維度。

  文件：{規格絕對路徑}（類型 {FRD/SAD/BFS/FFS}）
  維度：{下表其一}
  檢查清單：{下表對應的 reference 絕對路徑}

  <讀取紀律>
  規格一律定向讀取，不整檔載入：grep -n 'SPEC-INDEX v1' 定位索引 →
  grep -n "^## " 取章起行 → Read 帶 offset/limit 只讀本維度要驗的章。
  範本同理：sed -n '/^## 6\./,/^## /p' {範本路徑}。
  **必須對照範本比對，不可憑記憶。**
  </讀取紀律>

  <回報格式>
  只回缺失清單，每條四欄：等級（CRITICAL/WARNING/INFO）｜位置（章節＋行號）｜
  問題一句話｜證據（引用原文或查詢結果，最多兩行）。
  無缺失就回「本維度 0 缺失，已檢查 N 項」。

  **禁止**貼規格原文、DB 查詢的完整結果、檔案內容進回報——呼叫端要的是結論與定位。
  **禁止**下「整體可否開發」的結論，那是呼叫端彙整五個維度後才判得出來的。
  </回報格式>

  <紀律>
  ${CLAUDE_PLUGIN_ROOT}/references/dispatch-conventions.md §五
  量化斷言（數量、範圍、筆數）要自己複核一次再寫進回報。
  </紀律>
```

## 五個維度

| 維度 | 查什麼 | 檢查清單 reference | 條件 |
|---|---|---|:--:|
| **D2 資料流** | DB 結構逐欄比對、實際資料真實性、資料流向追蹤、表頭-明細一致性 | `references/data-flow-checklists.md` | 一律 |
| **D3 資訊流** | API 端點架構、讀寫邏輯可行性、驗證規則完整性、現有系統整合、外部服務、例外處理 | `references/info-flow-checklists.md` ＋ `references/existing-resources-check.md` | 一律 |
| **D4 架構可行性** | 見 task-checklists.md Task 4 段落 | `references/task-checklists.md` | 一律 |
| **D5 舊系統交叉比對** | 畫面欄位→Request/Response、驗證規則→VR/BR、CRUD 事件→API、實際資料三方比對 | `references/checklist-details.md` | 舊系統遷移時 |
| **D6 領域一致性** | 生命週期定位、狀態流轉、前後置依賴、金額／數量歸集、主檔與明細結構、跨模組 FK | `${CLAUDE_PLUGIN_ROOT}/references/analysis-standards.md` | 一律 |

## 各維度的額外輸入

**D2** 要帶：

```
  先讀 {功能目錄}/analysis/db-analysis.yml——結構事實（欄位、型別、長度、可空性、約束）
  以該檔為準，命中即用、不重查；缺項才用唯讀 DB 查詢工具補查。
  ⚠ 但「實際資料驗證」不適用快取——對已存在且有資料的表**必須當場查詢實際資料**，
  因為驗的正是「規格假設與現實資料是否相符」，需要的是此刻的資料而非勘察當時的結構。
  發現 canonical 欄位描述與證據不符 → 不中斷驗證，缺失判定以證據語意為準，並在報告中註記。
```

> D2 需要唯讀 DB 查詢工具（如專案有提供），派工時確認 `general-purpose` 拿得到（它是 `*` 工具集，應該有）；沒有則該維度走下方「D2 工具不可用」處置。

**D3** 要帶：

```
  先讀 {功能目錄}/analysis/reuse-scan.yml——既有路由、Handler／Entity 對照、Light API 現況
  多半已由 SAD／BFS 盤過，命中即用。scanned_at 早於本次規格最後修訂、
  或該檔未涵蓋本次新增的資源 → 才用 Grep/Glob 補查。
```

**D5** 要帶：

```
  先讀 {功能目錄}/analysis/vr-results.yml（舊系統分析階段已跑過的實測結果，若有）
  與 analysis/diff-report.md——已實測過的驗證規則**不重跑 SQL**，
  直接引用結論並標註來源與日期。只對未涵蓋的項目執行比對。
```

## 匯流

五個維度全部回報齊了才進 Task 7。任一維度失敗的處置：

| 失敗 | 處置 |
|---|---|
| D2（唯讀 DB 查詢工具不可用） | 該維度全標「未驗證 — 唯讀 DB 查詢工具不可用」，**報告最終結論自動降為 ⚠️** |
| D3（Grep/Glob 找不到資源） | 標「現有資源未找到」，不視為 CRITICAL |
| D5（無舊系統） | 該維度標 N/A，不派 |
| 任一 agent 回報異常或空白 | 重派一次；仍失敗則在報告標明該維度未涵蓋 |

<law>
**彙整時要複核量化斷言。** 曾出現 agent 宣稱「分析報告實為 VR-001~024」，實查是 **025**。
五個維度回報的數量、範圍、筆數，抽驗後再寫進報告。
</law>
