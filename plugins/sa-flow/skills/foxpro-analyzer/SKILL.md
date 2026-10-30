---
name: foxpro-analyzer
description: >-
  完整分析 FoxPro 舊系統：畫面佈局、欄位規格、驗證規則、事件處理(CRUD)、實際資料比對、使用者操作流程、業務領域邏輯。
  適用於需要從 FoxPro APP/PRG 檔案提取完整分析報告，作為 Web 版遷移的依據。
  Use when user says "分析 FoxPro", "FoxPro 遷移", "analyze FoxPro", "舊系統分析", "FoxPro APP 分析", "PRG 檔案分析".
argument-hint: "{FoxPro 檔案路徑或功能代碼}"
---

> 非 Claude Code（如 Pi）執行時，先讀 `../../references/harness-terms.md`（相對本檔；Claude Code 為 `${CLAUDE_PLUGIN_ROOT}/references/harness-terms.md`，照字面執行可略過），把 Claude 專屬工具與路徑換成對應項。

## 核心原則：不猜測

**遇到不清楚或有疑問的地方，絕不猜測，依以下順序處理：**

1. **先找答案** — 在 FoxPro 原始碼、DB 結構、專案文件中搜尋，嘗試自行找到答案
2. **找不到就問** — 使用 `AskUserQuestion` 詢問使用者，**必須附上建議的解決方案**供選擇
3. **確認後才寫** — 所有疑問解決後才開始撰寫分析報告
4. **寫前總清查** — 報告撰寫前，重新檢查所有已收集的資訊，確認無遺漏疑問

**禁止**：使用 `[需要澄清]` 標記帶過問題。所有問題必須在寫報告前解決。

## 解析流程（必須嚴格遵循）

> **規則依賴**：`${CLAUDE_SKILL_DIR}/../../references/analysis-standards.md`（業務領域、資料比對、操作流程標準）

### Step 1：確認 FoxPro 系統位置與功能

請使用者提供：根目錄路徑 + 功能代碼或檔案路徑。

一個功能可能包含多個 APP 檔案，需一併分析：

| 後綴 | 說明 | 優先級 |
|------|------|--------|
| 無 | 主表頭作業 | ⭐⭐⭐ 必須 |
| `A` | 沖轉/新增 | ⭐⭐⭐ 必須 |
| `E` | 明細編輯 | ⭐⭐⭐ 必須 |
| `Q` | 查詢 | ⭐⭐ 建議 |
| `P` | 列印 | ⭐ 選擇性 |

### Step 2：使用 Python 腳本解析

**必須**使用 `${CLAUDE_SKILL_DIR}/scripts/parse_foxpro.py`（cp950 解碼 + PROCEDURE 結構提取）：

```bash
python ${CLAUDE_SKILL_DIR}/scripts/parse_foxpro.py <path> --output markdown  # 完整報告
python ${CLAUDE_SKILL_DIR}/scripts/parse_foxpro.py <path> --list             # 列出程序
python ${CLAUDE_SKILL_DIR}/scripts/parse_foxpro.py <path> --proc <name>      # 查看程序
```

**禁止**跳過腳本直接讀取二進位檔案或用 latin-1 解碼。

### Step 3：深入分析關鍵程序

用 `--proc` 查看 CMDSAVE.Click、CMDDEL.Click、Valid 等關鍵程序原始碼。

### Step 4：畫面佈局完整擷取

**必須**產出：ASCII 畫面結構圖、畫面元素清單表、畫面區域分組表。

詳細格式 → [references/analysis-templates.md](references/analysis-templates.md) Step 5

### Step 5：使用者操作流程記錄

**必須**記錄 CRUD 完整流程（新增/修改/刪除/查詢），含：前置條件、OPMODE、驗證時機、交易管理、成功/失敗回應、連動操作。

產出 CRUD 事件生命週期表（觸發事件順序→涉及程序→資料表操作）。

詳細格式 → [references/analysis-templates.md](references/analysis-templates.md) Step 6

### Step 6：實際資料比對

**必須**使用可用的資料庫工具查詢 DB（如 MCP 資料庫工具）：

1. **結構比對**：FoxPro 欄位 vs DB 欄位（型態/長度/NULL）
2. **資料值抽樣**：列舉 DISTINCT 值、編號格式、數值範圍、日期範圍
3. **比對結果**：標記一致/差異/遺漏

詳細 SQL 與表格格式 → [references/analysis-templates.md](references/analysis-templates.md) Step 7

### Step 7：業務領域分析

**依據 `${CLAUDE_SKILL_DIR}/../../references/analysis-standards.md`**：

1. **生命週期定位**：此功能在業務流程（依產業調整，例：需求→設計→生產→交付→維護→終止）中的位置
2. **單據與流程步驟**：單據類型、步驟順序、作業別代碼、回報方式（若適用）
3. **成本與計價**：成本類型、計價方式、幣別/稅務（若適用）
4. **跨模組資料流**：上游/下游模組的資料交換

詳細表格格式 → [references/analysis-templates.md](references/analysis-templates.md) Step 8

### Step 8：疑問點總清查（寫報告前必做）

在開始撰寫分析報告前，**逐一檢查**以下面向是否仍有未解決的疑問：

| 面向 | 檢查問題 |
|------|---------|
| 畫面 | 所有畫面元素都已識別？佈局完整？ |
| 操作流程 | CRUD 每個流程的步驟和驗證都記錄？ |
| 欄位 | 每個欄位的來源、格式、驗證都確認？ |
| 業務邏輯 | 每條邏輯的判斷條件都從原始碼驗證？ |
| 資料比對 | DB 實際資料與 FoxPro 定義一致？差異都已標記？ |
| 跨功能 | 連動操作和跨模組影響都已識別？ |

**若仍有任何疑問**：回到 Step 1-7 重新分析或詢問使用者，直到全部解決。
**全部解決後**：才進入 Step 9 撰寫報告。

### Step 9：產出完整分析報告

報告 11 章：基本資訊 → 畫面佈局 → 操作流程 → CRUD 生命週期 → 資料表欄位 → 驗證規則 → 業務邏輯 → 資料比對 → 業務領域分析 → 錯誤訊息 → 遷移建議。

完整章節格式 → [references/analysis-templates.md](references/analysis-templates.md)

完成後依動線用 AskUserQuestion 建議下一步：`sa-flow:requirement {功能名稱}`（本報告是舊系統移植鏈的起點）；使用者同意才接著跑，不自動執行。

---

## 檔案類型與讀取方式

| 副檔名 | 讀取方式 |
|-------|---------|
| `.APP` | Python binary → cp950 → PROCEDURE 提取 |
| `.PRG` | cp950 直接讀取 |
| `.SCX/.SCT/.VCX/.VCT` | Python binary → cp950 → PROCEDURE 提取 |

## 程序分類與重要性

| 分類 | 說明 | 重要性 |
|------|------|--------|
| `button_event` | CMDSAVE, CMDADD, CMDDEL | ⭐⭐⭐ |
| `validation` | Valid, When 事件 | ⭐⭐⭐ |
| `business_logic` | p_save, p_add | ⭐⭐⭐ |
| `form_event` | Init, Load | ⭐⭐ |
| `data_access` | p_load, display | ⭐⭐ |
| `utility` | sql_error, check_right | ⭐ |

## 驗證模式快速識別

| 關鍵字 | 驗證類型 |
|-------|---------|
| `EMPTY(THISFORM.xxx)` | 必填 |
| `SEEK(值, 別名)` | 唯一性 |
| `SQLEXEC + RECCOUNT > 0` | SQL 唯一性 |
| `MESSAGEBOX('...不能刪除...')` | 刪除限制 |
| `BETWEEN(值, 下限, 上限)` | 範圍 |
| `SUM(欄位)` | 加總 |

詳細模式對照 → [references/validation-patterns.md](references/validation-patterns.md)

## 注意事項

1. 腳本已處理 Big5/cp950 編碼，禁止手動解碼
2. 輸出**禁止**包含 FoxPro 原始碼
3. 同名 PROCEDURE（如 Valid）可能有多個實例
4. 同功能多個 APP 必須一併分析
5. **必須**用資料庫工具查 DB 實際資料，不可僅憑程式碼推測

## References

- [analysis-templates.md](references/analysis-templates.md) — Step 4-8 詳細範本
- [validation-patterns.md](references/validation-patterns.md) — 驗證模式對照
- [output-templates.md](references/output-templates.md) — 輸出格式範本
- [table-mapping.md](references/table-mapping.md) — 資料表對應
- [analysis-standards.md](${CLAUDE_SKILL_DIR}/../../references/analysis-standards.md) — 業務領域分析標準
