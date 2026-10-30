# 現有資源盤點指引

## 概述

開發前必須確認專案中已有哪些可重用的資源，避免重複開發或與現有系統衝突。

> **注意**：以下指令以「分層式專案（Presentation／Application／Domain／Infrastructure）＋ C#／EF」為**範例**，其他技術棧請依專案結構與慣用語言改寫對應搜尋；路徑佔位符需依專案實際目錄結構調整：
> - `{presentation_layer}` → 專案的 Presentation 層路徑（如 `src/WebAPI`）
> - `{application_layer}` → 專案的 Application 層路徑（如 `src/Application`）
> - `{domain_entities}` → 專案的 Domain Entity 路徑（如 `src/Domain/Entities`）
> - `{repository_layer}` → 專案的 Repository 路徑（如 `src/Infrastructure/Repositories`）
> - `{controllers}` → 專案的 Controller 路徑（如 `src/WebAPI/Controllers`）

---

## 1. 現有 API 端點搜尋

### 1.1 同模組 Controller 搜尋

```bash
# 搜尋同模組下所有 Controller（依專案實際目錄結構調整）
find {presentation_layer}/{Module}/ -name "*.cs"

# 搜尋特定 Entity 的 Controller
grep -r "class {Entity}Controller" {presentation_layer}/ --include="*.cs"
```

### 1.2 Light API 搜尋

```bash
# 搜尋已存在的 Light Response
grep -r "Get{Entity}Light" {application_layer}/ --include="*.cs"
grep -r "LightResponse" {application_layer}/{Module}/ --include="*.cs"
```

### 1.3 路由衝突檢查

```bash
# 搜尋相同路由前綴
grep -r '\[Route.*{module}.*{entity}\]' {presentation_layer}/ --include="*.cs"
grep -r '\[Area("{Module}"\)]' {presentation_layer}/ --include="*.cs"
```

---

## 2. 規格書涉及資料表的現有資源檢查

**從規格書 ER Diagram 提取所有資料表名稱，逐一檢查以下項目：**

### 2.0 逐表盤點流程

對規格書中每個資料表（含主表和參照表），依序執行：

```
對每個 {TableName}：
  1. Entity 是否已存在？ → 搜尋 Entities/ 目錄
  2. EF Configuration 是否已存在？ → 搜尋 Configurations/ 目錄
  3. AppDbContext 是否已註冊 DbSet？ → 搜尋 AppDbContext.cs
  4. Repository 是否已存在？ → 搜尋 Repositories/ 目錄
  5. 該表是否已有 CRUD 操作？ → 搜尋 Application/{Module}/
  6. 該表是否已有 Controller？ → 搜尋 Controllers/
  7. 該表的 Light API 是否已存在？ → 搜尋 Light Response
```

### 2.0.1 搜尋指令

```bash
# 對規格書中每個資料表 {TableName} 執行（依專案實際目錄結構調整）：

# Entity
find {domain_entities}/ -iname "{TableName}.cs"

# EF Configuration
find {domain_layer}/Data/Configurations/ -iname "{TableName}Configuration.cs"

# DbSet 註冊
grep -i "DbSet<{TableName}>" {domain_layer}/Data/AppDbContext.cs

# Repository
find {repository_layer}/ -iname "*{TableName}*"

# 業務操作元件（CRUD）
grep -ri "{TableName}" {application_layer}/ --include="*Handler.cs" -l

# Controller
grep -ri "class {TableName}Controller" {presentation_layer}/ --include="*.cs" -l

# Light API
grep -ri "Get{TableName}Light" {application_layer}/ --include="*.cs" -l
```

### 2.0.2 輸出格式

```markdown
### 規格書資料表現有資源盤點

| # | 資料表 | Entity | Configuration | DbSet | Repository | 業務操作 | Controller | Light API |
|---|--------|--------|--------------|-------|------------|---------|------------|-----------|
| 1 | PurchaseOrder | ✅ PurchaseOrder | ✅ | ✅ | ✅ | ✅ CRUD | ✅ v3 | ✅ |
| 2 | PurchaseOrderLine | ✅ PurchaseOrderLine | ✅ | ✅ | ❌ 需建立 | ❌ 需建立 | ❌ 需建立 | ❌ 需建立 |
| 3 | Supplier | ✅ Supplier | ✅ | ✅ | ✅ | ✅ | ✅ v3 | ✅ 可直接呼叫 |
| 4 | NewTable | ❌ 需建立 | ❌ 需建立 | ❌ 需建立 | ❌ 需建立 | ❌ 需建立 | ❌ 需建立 | — |
```

### 2.0.3 判定規則

> **注意：** 若 DB 表已存在，Entity 定義通常可自動產生，無需規格書重複定義。

| 狀態 | 規格書動作 | 嚴重等級 |
|------|-----------|---------|
| Entity 已存在，規格書欄位與 Entity 屬性一致 | 直接使用，無需修改 | — |
| Entity 已存在，但規格書有新增欄位 | 規格書說明需新增欄位，DB 變更後 Entity 重新產生 | WARNING |
| Entity 已存在，但規格書欄位型態不符 | 以 DB 為準，修正規格書 | CRITICAL |
| Entity 不存在，DB 表已存在 | 規格書說明需匯入現有 DB 表 | CRITICAL |
| Entity 不存在，DB 表也不存在 | 規格書說明需新建 DB 表與對應資料模型 | CRITICAL |
| 參照表已有 Light API | 規格書可直接引用，無需重建 | INFO |
| 參照表無 Light API | 需確認是否要新建或用其他方式 | WARNING |

---

## 3. 現有程式碼搜尋

### 2.1 Entity 搜尋

```bash
# 搜尋 Entity 是否已存在（依專案實際目錄結構調整）
find {domain_entities}/ -name "{Entity}.cs"

# 搜尋 Entity 被引用的位置（評估影響範圍）
grep -r "using.*Entities.*{Entity}" {application_layer}/ --include="*.cs" -l
```

### 2.2 Repository 搜尋

```bash
# 搜尋 Repository 介面與實作（依專案實際目錄結構調整）
find {domain_layer}/Repositories/ -path "*{Entity}*"
find {repository_layer}/ -path "*{Entity}*"
```

### 2.3 業務操作模式參考

```bash
# 搜尋同模組的業務操作元件（作為規格參考，依專案實際目錄結構調整）
find {application_layer}/{Module}/ -name "*Handler.cs"

# 搜尋相似的業務邏輯模式
grep -r "class Create{SimilarEntity}" {application_layer}/ --include="*Handler.cs"
```

### 2.4 共用 Service/Helper

```bash
# 搜尋可重用的共用服務（依專案實際目錄結構調整）
find {application_layer}/Common/ -name "*.cs"
find {domain_layer}/Helpers/ -name "*.cs"

# 搜尋特定功能的 Helper（如編號產生、計算邏輯）
grep -r "NumberGenerator\|SerialNumber\|AutoNumber" {application_layer}/ --include="*.cs" -l
```

### 2.5 EF Configuration

```bash
# 搜尋 Entity Configuration 是否已存在（依專案實際目錄結構調整）
find {domain_layer}/Data/Configurations/ -name "{Entity}Configuration.cs"

# 確認 AppDbContext 是否已註冊 DbSet
grep -r "DbSet<{Entity}>" {domain_layer}/Data/AppDbContext.cs
```

---

## 4. 跨模組影響分析

### 4.1 Entity 引用分析

```bash
# 搜尋哪些模組引用了目標 Entity（依專案實際目錄結構調整）
grep -r "{Entity}" {application_layer}/ --include="*.cs" -l

# 搜尋哪些 Response DTO 包含該 Entity 的欄位
grep -r "{Entity}" {application_layer}/ --include="*Response.cs" -l
```

### 4.2 外鍵依賴分析

```bash
# 搜尋其他 Entity 是否有外鍵指向目標表（依專案實際目錄結構調整）
grep -r "{EntityId}\|{ENTITY_ID}" {domain_entities}/ --include="*.cs" -l
```

### 4.3 Validator 影響分析

```bash
# 搜尋現有 Validator 中對目標 Entity 的引用（依專案實際目錄結構調整）
grep -r "{Entity}" {application_layer}/ --include="*Validator.cs"
```

---

## 5. 輸出格式

### 5.1 現有資源盤點表

```markdown
### 現有資源盤點結果

| # | 資源類型 | 名稱 | 路徑 | 可重用性 | 備註 |
|---|---------|------|------|---------|------|
| 1 | Controller | VendorController | {controllers}/Purchasing/ | 參考模式 | 同模組 CRUD 範例 |
| 2 | Entity | Vendor | {domain_entities}/Vendor.cs | 直接使用 | 已存在 |
| 3 | Repository | VendorRepository | {repository_layer}/Purchasing/ | 直接使用 | 已有複雜查詢實作 |
| 4 | Light API | GetVendorLight | {application_layer}/Purchasing/ | 直接呼叫 | 規格書參照表用 |
| 5 | Helper | StringByteHelper | {domain_layer}/Helpers/ | 重用 | varchar 驗證用 |
```

### 5.2 衝突/影響清單

```markdown
### 跨模組影響

| # | 影響項目 | 影響範圍 | 嚴重等級 | 處理建議 |
|---|---------|---------|---------|---------|
| 1 | Vendor Entity 被 3 個模組引用 | Purchasing, Tool, Production | CRITICAL | 修改需同步更新 |
| 2 | 路由 /api/purchasing/vendor 已存在 | VendorController | CRITICAL | 不可重複定義 |
```
