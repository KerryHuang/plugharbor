# 規格書命名規則與 API 規範

## Entity 命名原則（核心）

**Entity 名稱必須反映業務語義，禁止沿用舊系統或資料庫的縮寫與簡化命名。**

| 禁止 | 正確 | 原因 |
|------|------|------|
| `CustMst` | `Customer` | DB table 縮寫，非業務語言 |
| `OrdHdr` | `SalesOrder` | 舊系統慣例縮寫 |
| `PrdInfo` | `Product` | 無法從名稱判斷業務含義 |
| `Mat` | `Material` | 過度縮寫，語義不清 |
| `WO` | `WorkOrder` | 首字母縮寫，非通用詞彙 |

**命名規則**：
- **使用完整英文業務詞彙**，PascalCase，不縮寫（`WorkOrder` ✅，`WO` / `WkOrd` ❌）
- **以領域語言命名**，反映使用者與業務的說法，而非 DB schema 的歷史積累
- **舊系統翻新專案**：不繼承原有命名，重新以現代領域模型定義 Entity
- **若 DB 欄位與業務語義不符**，以業務語義為準，在 BFS 中明確標注轉換對應



## 命名規則速查

| 概念 | 命名規則 | 範例 |
|-----|---------|------|
| 主鍵 | `{Entity}Id` | `SalesOrderId` |
| 編號 | `{Entity}No` | `PurchaseOrderNo` |
| 外鍵 | `{Role}Id` | `VendorId`, `CustomerId` |
| 日期 | `{Purpose}Date` | `DeliveryDate` |
| 金額 | `{Purpose}Amount` | `TotalAmount` |
| 布林 | `Is{State}` | `IsCompleted` |

**轉換規則**：
- DB → Model：`CUST_NO` → `CustNo`（PascalCase）
- Model → JSON：`VendorId` → `vendorId`（camelCase）

## Request/Response 規範

**Request**：關聯欄位使用 Id

```json
{ "vendorId": "4AR", "currencyCode": "NTD" }
```

**Response**：使用巢狀物件

```json
{
  "vendor": { "id": "4AR", "name": "供應商名稱" },
  "currency": { "code": "NTD", "name": "新台幣" }
}
```

**巢狀物件標準結構**：

| 物件 | 結構 |
|-----|------|
| vendor/customer | `{ id, name }` |
| currency | `{ code, name }` |
| {type} | `{ id, code, name }` |
| {role}Employee | `{ id, name }` |

## API 端點標準

```
/{module}/{entity}           ← 列表 / 新增
/{module}/{entity}/{id}      ← 單筆查詢 / 更新 / 刪除
/{module}/{entity}/Paged     ← 分頁查詢
/{module}/{entity}/Light     ← 選擇器
/{module}/{entity}/Batch     ← 批量建立/更新/刪除（條件式，逐項獨立）
```

| 操作 | 成功狀態碼 | 成功 Response body | 額外 header | 失敗 |
|-----|-----------|-------------------|------------|------|
| GET | 200 | 完整物件 / 物件陣列 / PagedResponse | — | 404 |
| POST | 201 | 建立後完整物件（Get{Entity}Response） | `Location: .../{id}` | 400/409 |
| PUT | 200 | 更新後完整物件（Get{Entity}Response） | — | 400/404/409 |
| DELETE | 204 | 無 body | — | 400/404 |
| BATCH | 207 | BatchResultResponse（逐項 success/error） | — | 400 |

> **PATCH 不納入** — 部分更新一律走 PUT 整筆更新。BATCH 部分成功契約（207 + BatchResultResponse）見 `references/response-structure-standards.md`。

## 語義化命名

Request/Response 屬性**必須**使用語義化業務名稱，**禁止**直接使用資料庫欄位名稱。

| 禁止 | 正確 | 說明 |
|------|------|------|
| `custNo` | `vendorId` | 使用角色語義 |
| `date1` | `shipDate` | 使用用途語義 |
| `qty1` | `quantity` | 使用業務語義 |
