# CR 文件交叉驗證規則

## 觸發條件

Task 1 識別文件類型包含任何 `CR-*` 文件時**必須**執行。

---

## 1. 參照文件存在性驗證

| 驗證項目 | 嚴重等級 |
|---------|---------|
| 原始文件路徑可以找到（FRD/BFS/FFS） | CRITICAL |
| 原始文件版本號與參照一致 | WARNING |
| CR-BFS 參照的 CR-FRD 存在 | CRITICAL |
| CR-FFS 參照的 CR-BFS 存在 | CRITICAL |

---

## 2. CR-BFS 與 CR-FFS 交叉驗證

| 驗證項目 | 嚴重等級 |
|---------|---------|
| CR-BFS 的每個新增/修改端點，在 CR-FFS API 對接清單中有對應 | CRITICAL |
| CR-BFS 標記的 Breaking Change，在 CR-FFS 也有對應標記 | CRITICAL |
| CR-BFS 新增的必填 Request 欄位，在 CR-FFS 欄位驗證中有對應 | WARNING |
| CR-FFS 移除的元件，對應 CR-BFS 移除的端點 | WARNING |

---

## 3. 變更影響分析

### 3.1 向後相容性檢查

| 檢查項目 | 嚴重等級 |
|---------|---------|
| 是否移除現有 Response 欄位（禁止） | CRITICAL |
| 是否變更現有欄位型別（禁止） | CRITICAL |
| 新增欄位是否為 nullable（必須） | CRITICAL |
| 是否影響現有 API 路由 | CRITICAL |

### 3.2 資料遷移檢查

| 檢查項目 | 嚴重等級 |
|---------|---------|
| 新增 NOT NULL 欄位是否有預設值或遷移計畫 | CRITICAL |
| 欄位型態變更是否有資料轉換策略 | CRITICAL |
| 欄位刪除是否有資料保留策略 | WARNING |
