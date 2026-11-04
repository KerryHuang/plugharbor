# FoxPro 資料表對照表

## 檔案位置

預設路徑：`C:\legacy-app\`（以實際安裝位置為準）

## 業務模組資料表

> 以下為中性範例，用來示範對照表的寫法。實際分析時以專案的 FoxPro 資料表清單取代（FoxPro 資料表命名、主鍵、子表後綴各專案不同）。

### Sales（銷售模組）

| FoxPro 表格 | 說明 | 主鍵 | 相關子表 |
|------------|------|------|---------|
| CUSTOMERS | 客戶主檔 | CUST_NO | CUST_CONTACTS, CUST_PAYTERMS |
| CUST_CONTACTS | 客戶聯絡人 | CUST_NO + SEQ | - |
| CUST_PAYTERMS | 付款條件 | CUST_NO + ITEM_NO | - |
| ORDERS | 銷售訂單主檔 | ORDER_NO | ORDER_ITEMS |
| ORDER_ITEMS | 銷售訂單明細 | ORDER_NO + SEQ | - |
| QUOTES | 報價單主檔 | QUOTE_NO | QUOTE_ITEMS |
| QUOTE_ITEMS | 報價單明細 | QUOTE_NO + SEQ | - |

### Inventory（庫存模組）

| FoxPro 表格 | 說明 | 主鍵 | 相關子表 |
|------------|------|------|---------|
| PRODUCTS | 商品主檔 | PROD_NO | PRODUCT_UNITS |
| PRODUCT_UNITS | 商品單位換算 | PROD_NO + UNIT | - |
| STOCK_MOVES | 庫存異動 | MOVE_NO | STOCK_MOVE_ITEMS |
| STOCK_MOVE_ITEMS | 庫存異動明細 | MOVE_NO + SEQ | - |

### Purchasing（採購模組）

| FoxPro 表格 | 說明 | 主鍵 | 相關子表 |
|------------|------|------|---------|
| VENDORS | 供應商主檔 | VEND_NO | VENDOR_CONTACTS |
| VENDOR_CONTACTS | 供應商聯絡人 | VEND_NO + SEQ | - |
| PURCHASES | 採購單主檔 | PO_NO | PURCHASE_ITEMS |
| PURCHASE_ITEMS | 採購單明細 | PO_NO + SEQ | - |

### System（系統模組）

| FoxPro 表格 | 說明 | 主鍵 | 用途 |
|------------|------|------|------|
| SYS_PARAMS | 系統參數 | PARAM_NO | 系統設定 |
| CODE_TABLE | 代碼主檔 | CODE_TYPE + CODE | 下拉選單 |
| EMPLOYEES | 員工主檔 | EMP_NO | 人員資料 |
| DEPARTMENTS | 部門主檔 | DEPT_NO | 組織架構 |

## 常見欄位對照

### 共用欄位

| FoxPro 欄位 | 說明 | 型態 | 目標屬性名 |
|------------|------|------|----------|
| DEL_FLAG | 刪除標記（軟刪） | char(1) | IsDeleted (bool) |
| UTIME | 更新時間 | datetime | UpdatedAt |
| UUSER | 更新人員 | char(10) | UpdatedBy |
| CTIME | 建立時間 | datetime | CreatedAt |
| CUSER | 建立人員 | char(10) | CreatedBy |

### 客戶相關

| FoxPro 欄位 | 說明 | 型態 | 目標屬性名 |
|------------|------|------|----------|
| CUST_NO | 客戶編號 | char(15) | CustomerId |
| CUST_NAME | 客戶名稱 | varchar(100) | CustomerName |
| SUBNAME | 簡稱 | char(12) | CustomerSubname |
| CONTACTER | 主聯絡人 | varchar(28) | PrimaryContact |
| TEL1 | 電話1 | varchar(30) | Phone1 |
| TEL2 | 電話2 | varchar(30) | Phone2 |
| FAX | 傳真 | varchar(30) | Fax |
| EMAIL | 電子郵件 | varchar(100) | Email |
| ADDRESS | 地址 | varchar(200) | Address |
| CURRENCY | 交易幣別 | char(3) | CurrencyId |
| TAX_RATE | 稅率 | decimal(5,2) | TaxRate |
| TRADE_TERM | 貿易條件 | char(10) | TradeTermId |
| REMARK | 備註 | text | Remark |

### 聯絡人相關

| FoxPro 欄位 | 說明 | 型態 | 目標屬性名 |
|------------|------|------|----------|
| SEQ | 序號 | char(3) | Sequence |
| CONTACT_NAME | 聯絡人姓名 | varchar(28) | ContactName |
| DEPT | 部門 | varchar(30) | Department |
| TITLE | 職稱 | varchar(30) | Title |
| MOBILE | 手機 | varchar(20) | Mobile |
| IS_MASTER | 是否主要 | char(1) | IsPrimary |
| BIRTHDAY | 生日 | date | Birthday |
| LEAVE_STATUS | 離職狀態 | char(1) | LeaveStatus |

### 付款條件相關

| FoxPro 欄位 | 說明 | 型態 | 目標屬性名 |
|------------|------|------|----------|
| ITEM_NO | 項目序號 | char(2) | ItemNo |
| ITEM_NAME | 項目名稱 | varchar(10) | ItemName |
| RATE | 比例 | decimal(5,2) | Rate |
| DAYS | 天數 | int | Days |

## 索引結構

### 主要索引類型

| 索引類型 | 說明 | 範例 |
|---------|------|------|
| Primary | 主鍵索引 | CUST_NO |
| Unique | 唯一索引 | CUST_NO + DEL_FLAG |
| Regular | 一般索引 | SUBNAME |
| Candidate | 候選索引 | EMAIL |

### 常見複合索引

| 表格 | 索引欄位 | 用途 |
|------|---------|------|
| CUST_CONTACTS | CUST_NO + SEQ | 客戶聯絡人查詢 |
| CUST_PAYTERMS | CUST_NO + ITEM_NO | 付款條件查詢 |
| ORDER_ITEMS | ORDER_NO + SEQ | 訂單明細查詢 |

## 關聯關係

```
CUSTOMERS (客戶主檔)
├── CUST_CONTACTS (客戶聯絡人) [1:N via CUST_NO]
├── CUST_PAYTERMS (付款條件) [1:N via CUST_NO]
├── ORDERS (銷售訂單) [1:N via CUST_NO] ← 刪除限制
└── QUOTES (報價單) [1:N via CUST_NO]

VENDORS (供應商主檔)
├── VENDOR_CONTACTS (供應商聯絡人) [1:N via VEND_NO]
└── PURCHASES (採購單) [1:N via VEND_NO]
```
