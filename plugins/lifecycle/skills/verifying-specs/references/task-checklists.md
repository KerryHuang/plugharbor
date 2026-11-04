# Task 3.5 / 3.6 / Task 4 詳細檢查項

## Task 3.5：外部服務整合（BFS §11 非 N/A 時）

| 檢查項目 | 等級 |
|---|---|
| 每個外部服務有整合方式與呼叫時機說明 | CRITICAL |
| 每個外部服務有服務不可用的錯誤處理策略 | CRITICAL |

## Task 3.6：例外處理完整性（BFS 文件適用）

對照 `${CLAUDE_PLUGIN_ROOT}/templates/bfs.md` Section 8 逐一驗證：

| 檢查項目 | 等級 |
|---|---|
| 每個 API 端點有定義錯誤情境清單 | CRITICAL |
| 每個錯誤情境有對應 HTTP 狀態碼 | CRITICAL |
| 業務例外與系統例外有明確區分 | CRITICAL |
| 錯誤回應格式符合專案統一 schema | CRITICAL |
| 交易操作有說明失敗處理策略（rollback/補償） | WARNING |
| 並發衝突情境有說明（有狀態流轉功能必填；無狀態純查詢 API 可 N/A） | CRITICAL |

## Task 4：架構可行性

| 檢查項目 | 等級 |
|---|---|
| 遵循專案分層架構（如 Clean Architecture） | CRITICAL |
| 資料存取透過 Repository 介面 | CRITICAL |
| 新增 NOT NULL 欄位有預設值/遷移策略 | CRITICAL |
| 不移除現有 Response 欄位（向後相容） | CRITICAL |
| 不變更現有欄位型別 | CRITICAL |
| 新增欄位為 nullable | CRITICAL |
| 是否需要資料庫 Migration | WARNING |
| 索引規劃合理 | WARNING |
