# Verification Rules — Step 4 事實驗證細節

CR 票寫成時的程式碼狀態 ≠ 合併當下的程式碼狀態。本檔列出抽取規則、驗證手段、drift 處置矩陣的完整細節。

## 抽取參照清單（從票號檔內文）

| 類型 | 來源樣態 | 例 |
|---|---|---|
| 檔案路徑 | inline code 或表格內含 `/` 或 `\` | `src/Core/.../LeaveRepository.cs`、`db/.../LEAVE_REQUEST.sql` |
| 類別 / 介面 / 方法 | inline code 帶 `()` 或大駝峰 | `ILeaveFilterService`、`LeaveRepository.IsUniqueAsync` |
| API 端點 | `GET/POST/PUT/DELETE /api/...` | `GET /api/hr/leave-requests` |
| DB 物件 | schema-qualified 名稱 / `dbo.XXX` | `dbo.LEAVE_REQUEST`、`hr.EmployeeView` View |
| DB 欄位 | `TableName.COLUMN` 大寫格式 | `LEAVE_REQUEST.STATUS`、`EMPLOYEE.DEPT_ID` |
| 設定 / Rule 編號 | `Rule \d+`、設定表鍵 | `Rule 48`、`SETTINGS.COMPANY_NAME` |

## 對應驗證手段

| 參照類型 | 驗證手段 |
|---|---|
| 檔案路徑 | Glob 或 `Read` 嘗試；不存在 → 標 drift |
| 類別 / 介面 / 方法 | Grep `class XXX`、`interface XXX`、方法簽名；找不到 → drift |
| API 端點 | Grep Controller `[HttpGet("...")]` 等屬性；找不到 → drift |
| DB 物件 / 欄位 | 專案提供的唯讀 DB 工具查欄位定義（沒有就比對 migration／entity 定義）；欄位不存在或型態不符 → drift |
| Rule 編號 | Glob 專案 `.claude/rules/` 對應檔是否存在 |

## 驗證範圍

- **核心改動目標必驗**：CR 票主敘事直接涉及的 entity / repository / handler / API / DB 物件 100% 驗證
- **次要提及抽樣**：附錄技術參照表抽樣 30%，避免過度驗證拖慢流程
- **大量參照時**：可派發 `general-purpose` subagent 並行驗證

## Drift 處置矩陣

| 驗證結果 | 處置 |
|---|---|
| ✅ 全部命中 | 進入正常合併流程 |
| ⚠️ 1-3 處 drift（路徑微改、方法重命名）| 報告標示「需人工確認 drift」，預設**不自動合併**；使用者可加 `--force-merge-with-drift` 強制執行 |
| ❌ 核心參照 drift > 3 處 或 DB schema 不符 | **強制阻擋合併**，標「規格已過時，需 SA review」；引導使用者跑 `/sa-flow:verifying-specs` 或直接重寫 |

## 報告區塊樣板

```markdown
## 🔬 事實驗證

### {ticket}_{...}.md
- 驗證項目：{N}
- 命中：{M}
- Drift：{K}

**Drift 清單**：
- `LeaveRepository.IsUniqueAsync` — 預期：方法簽名 `(string, string?)`，實際：`(string, string?, CancellationToken)` ⚠️
- `db/.../LeaveAll_1.sql` — 預期存在，實際已刪除 ❌

**建議動作**：標 drift，等使用者確認 / 跑 verifying-specs / 加 --force-merge-with-drift
```

## 跳過驗證

- 使用者下 `/sa-flow:consolidate-docs --skip-verify` 可跳過 Step 4
- 報告必須顯著標註 ⚠️ **未驗證** 紅旗
- 不建議用於正式 commit，僅供探索性 dry-run
