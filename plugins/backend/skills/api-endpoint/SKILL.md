---
name: api-endpoint
description: 對外 API 端點開發：標準 CRUD 端點、版本控制、回應模型與狀態碼、分頁契約、Request 驗證。附 .NET（ASP.NET Core Controller）附錄。Use when 建立新 API Controller、新增 REST 端點、實作 API versioning、api endpoint、webapi controller、crud controller、REST API。
---

# API 端點

## 0. 偵測技術棧與附錄

先看專案的 `*.csproj`（ASP.NET Core）、`go.mod`、`pyproject.toml`（FastAPI／Django）、`package.json`（Express／Nest）、`pom.xml`（Spring）、既有 Controller／router 目錄，對照下表載入附錄，並在回報第一行寫「附錄：<檔名>」。

| 偵測到 | 附錄 |
|---|---|
| `*.csproj`／`*.sln`（.NET） | `${CLAUDE_PLUGIN_ROOT}/references/stacks/dotnet.md`（共用）＋ `references/dotnet.md`（Controller 範本、版本控制、回應模型） |
| `go.mod`、`pyproject.toml`、node 後端的 `package.json`、`pom.xml` 等 | 目前沒有附錄，走下方退路 |

沒有對應附錄：照本 skill 的通用方法，加上專案既有程式的寫法（先找 2–3 個同類檔當樣板；有裝 workspace 就照 `workspace:convention-first`（可選））。做完問使用者要不要把這次的寫法整理成新附錄 `references/stacks/<stack>.md`，回報寫「附錄：無（照既有程式）」。

## 1. 原則

1. 繼承或套用共用基底，取得授權、追蹤 ID（TraceId）等共通行為。
2. 端點只做：解析輸入 → 送出用例（見 `cqrs`）→ 轉成 HTTP 回應；**無業務邏輯**。
3. 設定 API 版本，路由含版本與模組區域。
4. 每個動作宣告可能的回應型別與狀態碼（文件與契約）。
5. 範例以中性領域 `Order` 示範。

## 2. 標準端點

| HTTP | 路徑 | 用途 | 成功回應 |
|------|------|------|----------|
| GET | `/` | 取得全部（可篩選） | 200 清單 |
| GET | `/{id}` | 取得單一 | 200，找不到 404 |
| GET | `/paged` | 分頁 | 200 分頁回應 |
| GET | `/light`、`/light/{id}`、`/light/paged` | 輕量版（下拉選單等） | 200 |
| POST | `/` | 建立 | 201 + 最新完整資料 |
| PUT | `/{id}` | 更新 | 200 + 最新完整資料 |
| DELETE | `/{id}` | 刪除 | 204，失敗 404 |

路由格式：`api/v{version}/{area}/{controller}`，例如 `api/v1.0/Sales/Order`。

## 3. 回應規則

| 動作 | 成功 | 失敗 |
|------|------|------|
| GET /{id} | 200 資料 | 404 |
| POST | 201，**重新查詢**後回傳最新完整資料 | 400 錯誤模型（含 TraceId） |
| PUT | 200，重新查詢後回傳 | 400 錯誤模型 |
| DELETE | 204 | 404 錯誤模型 |

- 回應模型分四類：400 一般錯誤、404 找不到、400 驗證錯誤、500 例外；格式統一。
- POST／PUT 成功後**必須 re-fetch**，回傳含伺服端產生欄位的最新資料。
- **禁止**把內部結果物件原樣回給前端。
- PUT 路由 id 與 body id 不一致 → 400。

## 4. 分頁契約

分頁 Request 欄位：目前頁、每頁筆數、排序欄陣列、排序方向陣列。回應欄位：項目清單、總筆數、目前頁、每頁筆數、總頁數。**沿用專案既有契約**，重點是前後端命名一致（欄位名叫什麼以專案既有為準，附錄有 .NET 範例命名）。

## 5. Request 驗證與伺服端欄位

- 輸入欄位加驗證（必填、長度），驗證失敗統一回驗證錯誤模型。
- 伺服端自產欄位（Create 的 Id、建立／修改時間）**不接受用戶端傳入**：標為序列化忽略。
- Update 的主鍵來自路由。

## 6. 檢查清單

- [ ] 端點無業務邏輯，只送用例
- [ ] 版本、路由、授權設定正確
- [ ] 每個動作宣告回應型別與狀態碼
- [ ] POST／PUT re-fetch；沒有回傳內部結果物件
- [ ] 分頁命名與前端一致
- [ ] 有測試（Controller 層驗狀態碼，見 `unit-testing`）
