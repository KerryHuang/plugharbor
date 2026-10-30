# Response 結構化欄位規範

> 適用於撰寫規格書、驗證規格書

## 原則

所有 API Response 中的參照欄位（客戶、幣別、商品、部門等），**必須**使用巢狀 Light Response 結構，不可回傳 flat 字串。

撰寫 BFS 前，**必須**先搜尋專案中既有的同類 Response 結構（如訂單、報價相關端點）作為參考基準。

## 巢狀結構對照表

| 參照類型 | DB 欄位 | Request 屬性 | Response 巢狀結構 | Light Response 類別 |
|---------|---------|-------------|-------------------|-------------------|
| 客戶 | customer_no | CustomerNo (string) | `customer: { customerId, customerName }` | `GetLightCustomerResponse` |
| 幣別 | currency_code | CurrencyCode (string) | `currency: { currencyId, currencyName, exchangeRate }` | `GetLightCurrencyResponse` |
| 部門 | dept_code | DeptCode (string) | `department: { id, deptCode, deptName }` | `GetLightDepartmentResponse` |
| 商品 | product_no | ProductNo (string) | `product: { id, productNo, productName }` | `GetLightProductResponse` |
| 訂單 | order_no | SalesOrderNo (string) | `salesOrder: { salesOrderId, salesOrderNo }` | `GetLightSalesOrderResponse` |

## 撰寫規格書時

1. 識別所有參照欄位（FK 或 code 欄位）
2. 搜尋現有 Light Response 是否已存在：`grep -r "GetLight{Type}Response" {application_layer}/`
3. Response 包含完整的參照物件資訊（不只返回 ID），便於前端顯示；Request 模型使用 flat code/id
4. JSON 範例中呈現巢狀物件

## HTTP 回應契約（各 Method）

> 各 Method 的成功狀態碼、成功 body 形狀、額外 header；速查另見 `skills/specify-backend/references/naming-conventions.md`「API 端點標準」。撰寫 BFS §6 時每個端點**必須明寫成功狀態碼**，不可只靠 §3 sequence 圖隱含。

| Method | 成功狀態碼 | 成功 Response body | 額外 header | 常見失敗 |
|--------|-----------|-------------------|------------|---------|
| GET（單筆/列表/分頁） | 200 | 完整物件 / 物件陣列 / `PagedResponse<T>` | — | 404 |
| POST | **201** | 建立後完整物件（`Get{Entity}Response`） | `Location: .../{id}` | 400 / 409 |
| PUT | 200 | 更新後完整物件（`Get{Entity}Response`） | — | 400 / 404 / 409 |
| DELETE | 204 | 無 body | — | 400 / 404 |
| BATCH（逐項獨立） | **207** | `BatchResultResponse`（逐項 success/error） | — | 400（整批請求格式錯誤） |

> **PATCH 不納入規範** — 部分更新一律走 PUT 整筆更新。功能確有部分更新需求時，於 BFS 明確提出再評估，不可逕自新增 PATCH 端點。

## 批量回應結構（BatchResultResponse）

批量端點採「逐項獨立」語意時，**必須**回 `207 Multi-Status` + 下列結構，讓前端能精準標出哪幾筆失敗：

| 屬性 | 型態 | 說明 |
|------|------|------|
| successCount | int | 成功筆數 |
| failureCount | int | 失敗筆數 |
| results | `BatchItemResult[]` | 逐項結果（順序對應 Request items） |
| results[].index | int | 對應 Request items 索引（0 起） |
| results[].success | bool | 該筆是否成功 |
| results[].id | string? | 成功回資源 id，失敗為 null |
| results[].error | `{ code, message }?` | 失敗回錯誤碼與訊息，成功為 null |

採「整批交易（全有全無）」語意時改回 `200`（全成功）/ `400`/`409`（一筆失敗全 rollback），不用 207；BFS 須註明 rollback 範圍。

## 驗證規格書時

增加檢查項（CRITICAL）：

| 檢查項目 | 等級 |
|---------|------|
| Response 中參照欄位使用巢狀 Light Response（非 flat 字串） | CRITICAL |
| 巢狀結構與專案既有同類端點一致 | CRITICAL |
| JSON 範例正確呈現巢狀物件 | WARNING |
| 每個端點明寫成功 HTTP 狀態碼（POST=201、PUT=200、DELETE=204、BATCH=207） | CRITICAL |
| POST 端點標明 `Location` header | WARNING |
| 批量端點明確定義部分成功行為（207 逐項 或 整批交易），未留白 | CRITICAL |
| 未經確認出現 PATCH 端點 | WARNING |
