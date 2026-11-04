# Task 3 資訊流驗證檢查清單

> 對應 SKILL.md Task 3.1 ~ 3.4。

## 3.1 API 端點架構

| 檢查項目 | 等級 |
|---------|------|
| 路由符合專案 API 路由規範 | CRITICAL |
| 每個端點有 Request/Response 表格 + JSON 範例 | CRITICAL |
| 模型 PascalCase、JSON camelCase | CRITICAL |
| Response 參照欄位（廠商、幣別、倉庫等）使用巢狀 Light Response，非 flat 字串（依 `response-structure-standards.md`） | CRITICAL |

## 3.2 讀寫邏輯設計可行性

| 檢查項目 | 等級 |
|---------|------|
| 查詢邏輯與修改邏輯明確分離 | CRITICAL |
| 列表/報表端點有 §6.0 DoR 表，每適用維度標「依循慣例(路徑)/自定義(值)」 | CRITICAL |
| DoR 無 hand-wave（比照既有/反查回填/對齊報表/依需要分頁） | CRITICAL |
| 排序有可排序欄位白名單；1:N 取值、聚合母體、日期邊界已明確 | CRITICAL |
| 操作後續動作（副作用）的觸發時機已說明 | WARNING |

## 3.3 驗證規則完整性

| 檢查項目 | 等級 |
|---------|------|
| 每個必填欄位有驗證規則 | CRITICAL |
| 字串欄位有長度/字節驗證 | CRITICAL |
| 每條業務邏輯有對應業務規則 | CRITICAL |
| 唯一性驗證排除已刪除資料 | CRITICAL |
| 刪除前置檢查涵蓋所有 FK 子表 | CRITICAL |
| 驗證規則有語意明確的錯誤訊息 | WARNING |

## 3.4 現有系統整合

用 Grep/Glob 搜尋，逐表盤點：

| 檢查項目 | 等級 |
|---------|------|
| 同模組已有相似 API（避免重複） | CRITICAL |
| Entity 已存在（需直接使用） | CRITICAL |
| Light API 已存在（規格書引用的參照表） | CRITICAL |
| 路由與現有 Controller 衝突 | CRITICAL |
| 修改的 Entity 被其他模組引用 | CRITICAL |

詳細搜尋指令 → [existing-resources-check.md](existing-resources-check.md)。
