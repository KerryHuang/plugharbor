> 本檔是 `templates/bfs.md` 的範例集，**按需讀取**：撰寫該章且不確定寫法時才讀。

# BFS §6 API 介面規格 — 完整範例

## 巢狀物件命名慣例（參照實際程式碼）

- 廠商：Vendor → GetLightVendorResponse { VendorId, VendorName }
- 幣別：Currency → CurrencyInfo { Code, Name }
- 品項：Item → GetLightItemResponse { Id, ItemCode, ItemName }
- 倉庫：Warehouse → GetLightWarehouseResponse { WarehouseId, WarehouseNo, WarehouseName }
- 請購單：PurchaseRequisition → GetLightRequisitionResponse { Id, RequisitionNo }
- 訂單：SalesOrder → GetLightSalesOrderResponse { SalesOrderId, SalesOrderNo }
- 明細序號：LineNo（flat string，非巢狀）
- 修改時間：LastModifiedTime（非 LastModifiedDate）

對應 `templates/bfs.md` §6.2～§6.9、§6.N+1 的完整範例（模板內已改為欄位表＋骨架＋指路註解）。
以下 JSON 範例使用「採購單（PurchaseOrder）」情境示範。撰寫時請替換為對應功能的真實資料
（可用 MCP 工具查詢 DB 取得實際值）。JSON key 使用 camelCase，模型屬性定義使用 PascalCase。

## §6.2 端點 1：GET /api/{module}/{entity} 完整範例

**Response：** `Get{Entity}Response[]`

```json
[
  {
    "id": "00000000-0000-0000-0000-000000000000",
    "{no}": "{NO_VALUE}",
    "{foreignEntity}": {
      "id": "{FK_VALUE}",
      "name": "{FK_NAME}"
    },
    "{date}": "2024-01-01",
    "{amount}": 100.50,
    "lastModifiedBy": "{USER}",
    "lastModifiedDate": "2024-01-01T10:30:00"
  }
]
```

## §6.3 端點 2：GET /api/{module}/{entity}/{id} 完整範例

**Request：** Path 參數 `{id}` (文字／唯一識別碼)

**Response：** `Get{Entity}Response`

> **示範說明**：採購單 PO-20240315-001，廠商青禾貿易有限公司，含 1 筆鋁合金板明細（數量 150 × 單價 12.6667 = 1,900.01，四捨五入 2 位）。

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "orderNo": "PO-20240315-001",
  "orderDate": "2024-03-15",
  "vendor": {
    "vendorId": "a1b2c3d4-0001-0001-0001-000000000001",
    "vendorNo": "VND-001",
    "vendorName": "青禾貿易有限公司"
  },
  "requisition": {
    "requisitionId": "b2c3d4e5-0002-0002-0002-000000000002",
    "requisitionNo": "PR-20240315-001"
  },
  "status": "Draft",
  "remark": "急件，需於 3/20 前到貨",
  "totalAmount": 1900.01,
  "lastModifiedBy": "張三",
  "lastModifiedTime": "2024-03-15T10:30:00.123",
  "items": [
    {
      "itemNo": "01",
      "item": {
        "id": "c3d4e5f6-0003-0003-0003-000000000003",
        "itemCode": "ALP",
        "itemName": "鋁合金板"
      },
      "quantity": 150,
      "unitPrice": 12.6667,
      "amount": 1900.01
    }
  ]
}
```

## §6.4 端點 3：GET /api/{module}/{entity}/Paged 完整範例

**Request：** Query 參數

```
GET /api/{module}/{entity}/Paged?
  {filterField1}={value}&
  {dateFrom}=2024-01-01&
  {dateTo}=2024-12-31&
  Keywords={keyword}&
  CurrentPage=1&
  PagesSize=20&
  SortBy={sortField}&
  SortOrder=DESC
```

| 參數 | 型態 | 必填 | 預設值 | 說明 | 來源 |
|------|------|------|--------|------|------|
| CurrentPage | int | X | 1 | 頁碼 | 繼承自 PagedRequest |
| PagesSize | int | X | 10 | 每頁筆數（最大 100） | 繼承自 PagedRequest |
| SortBy | string[]? | X | {預設} | 排序欄位（陣列） | 繼承自 PagedRequest |
| SortOrder | string[]? | X | ["DESC"] | 排序方向（ASC/DESC 陣列） | 繼承自 PagedRequest |
| {FilterField1} | string? | X | - | 篩選：{欄位說明} | 自訂屬性 |
| {FilterField2} | 唯一識別碼（可空） | X | - | 篩選：{欄位說明} | 自訂屬性 |
| {DateFrom} | DateTime? | X | - | 日期起 | 自訂屬性 |
| {DateTo} | DateTime? | X | - | 日期迄 | 自訂屬性 |
| Keywords | string? | X | - | 關鍵字搜尋 | 自訂屬性 |

**Response：** `PagedResponse<Get{Entity}Response>`

```json
{
  "items": [
    {
      "id": "00000000-0000-0000-0000-000000000000",
      "{no}": "{NO_VALUE}",
      "{foreignEntity}": { "id": "{FK_VALUE}", "name": "{FK_NAME}" },
      "{date}": "2024-01-01",
      "{amount}": 100.50,
      "lastModifiedBy": "{USER}",
      "lastModifiedDate": "2024-01-01T10:30:00"
    }
  ],
  "totalCount": 50,
  "pagesSize": 20,
  "currentPage": 1,
  "totalPages": 3
}
```

> **注意**：`PagedResponse<T>` 的 JSON 序列化欄位僅包含 `items`、`totalCount`、`pagesSize`、`currentPage`、`totalPages`。`StartPage`、`EndPage`、`PageNumbers`、`MaxNavigationPages` 標記為 `[JsonIgnore]`，不會輸出至前端。

## §6.5 端點 4：GET /api/{module}/{entity}/Light 完整範例

Light Response 設計原則：僅包含 ID + 主要顯示名稱/代碼（最多 3-5 個屬性）；禁止包含 `List<>` 集合導航；可被其他 Response 複用作為巢狀物件。

**Response：** `GetLight{Entity}Response[]`

| 欄位 | 型別 | 說明 |
|------|------|------|
| {entity}Id | 唯一識別碼 | 主鍵 |
| {entity}No | string | 業務編號 |
| {entity}Name | string | 顯示名稱 |

```json
[
  {
    "{entity}Id": "00000000-0000-0000-0000-000000000000",
    "{entity}No": "{NO_VALUE}",
    "{entity}Name": "{NAME_VALUE}"
  }
]
```

## §6.6 端點 5：POST /api/{module}/{entity} 完整範例

> **User Story**：身為採購人員，我選擇廠商「青禾貿易有限公司（VND-001）」和請購單「PR-20240315-001」，
> 新增一筆鋁合金板採購，數量 150 片，單價 12.6667 元。

**Request：**

```json
{
  "orderDate": "2024-03-15",
  "vendorId": "a1b2c3d4-0001-0001-0001-000000000001",
  "requisitionId": "b2c3d4e5-0002-0002-0002-000000000002",
  "remark": "急件，需於 3/20 前到貨",
  "items": [
    {
      "itemId": "c3d4e5f6-0003-0003-0003-000000000003",
      "quantity": 150,
      "unitPrice": 12.6667
    }
  ]
}
```

**Response body：**

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "{no}": "{AUTO_GENERATED_NO}",
  "{foreignEntity}": { "id": "{FK_VALUE}", "name": "{FK_NAME}" },
  "{date}": "2024-01-01",
  "{amount}": 0.00,
  "lastModifiedBy": "{USER}",
  "lastModifiedDate": "2024-01-01T10:30:00",
  "items": []
}
```

## §6.7 端點 6：PUT /api/{module}/{entity}/{id} 完整範例

**Request：** `Update{Entity}Request`

| 屬性名稱 | 型態 | 必填 | 長度限制 | 說明 | 驗證規則 |
|----------|------|------|----------|------|----------|
| {PropertyName} | string | O | 50 | {說明} | VR-001 |
| {OptionalProperty} | string? | X | 100 | {說明} | VR-002 |

**Request Body：**

```json
{
  "{propertyName}": "{updated_value}",
  "{optionalProperty}": "{value}"
}
```

## §6.8 端點 7：DELETE /api/{module}/{entity}/{id} 完整範例

**說明：** 刪除 {Entity}（軟刪除 DELETED_FLAG='Y' 或實體刪除）
**Request：** Path 參數 `{id}` (文字／唯一識別碼)
**Response：** 204 No Content（成功）/ 400 Bad Request（業務錯誤）

**錯誤回應（400 業務錯誤）：**

```json
{
  "type": "business_error",
  "title": "業務規則錯誤",
  "status": 400,
  "detail": "{業務錯誤訊息}"
}
```

## §6.9 端點 8：POST /api/{module}/{entity}/Batch 完整範例

**Request：**

```json
{
  "items": [
    { "orderDate": "2024-03-15", "vendorId": "a1b2c3d4-0001-0001-0001-000000000001", "quantity": 150 },
    { "orderDate": "2024-03-15", "vendorId": "a1b2c3d4-0002-0002-0002-000000000002", "quantity": 0 }
  ]
}
```

**Response body：**

```json
{
  "successCount": 1,
  "failureCount": 1,
  "results": [
    { "index": 0, "success": true, "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6", "error": null },
    { "index": 1, "success": false, "id": null, "error": { "code": "VR-004", "message": "訂購數量 須大於 0" } }
  ]
}
```

## §6.N+1 錯誤回應格式 完整範例

#### ValidationResponseModel（400 Bad Request）

```json
{
  "type": "validation",
  "title": "驗證失敗",
  "status": 400,
  "errors": {
    "{fieldName}": ["{錯誤訊息1}", "{錯誤訊息2}"]
  }
}
```

#### NotFoundResponseModel（404 Not Found）

```json
{
  "type": "not_found",
  "title": "資料不存在",
  "status": 404,
  "detail": "{Entity} with id '{id}' was not found"
}
```

#### BusinessExceptionResponseModel（400 Bad Request）

```json
{
  "type": "business_error",
  "title": "業務規則錯誤",
  "status": 400,
  "detail": "{業務錯誤訊息}"
}
```
