---
name: background-job
description: 背景作業與排程開發：Job 類別設計、DI 註冊、排程類型（固定 Cron、延遲、自動重排）、冪等與失敗處理。附 .NET（Hangfire）附錄。Use when 建立新背景作業、設定排程、需要 Job 開發範本、background job、recurring job、hangfire job、cron、排程作業。
---

# 背景作業與排程

## 0. 偵測技術棧與附錄

先看專案的 `*.csproj`（Hangfire／Quartz）、`go.mod`、`pyproject.toml`（Celery／APScheduler）、`package.json`（BullMQ／node-cron）、`pom.xml`（Quartz／Spring Scheduler）、既有 Job 目錄，對照下表載入附錄，並在回報第一行寫「附錄：<檔名>」。

| 偵測到 | 附錄 |
|---|---|
| `*.csproj`／`*.sln`（.NET，Hangfire） | `${CLAUDE_PLUGIN_ROOT}/references/stacks/dotnet.md`（共用）＋ `references/dotnet.md`（Job 類別、DI 註冊、Cron、自動重排） |
| `go.mod`、`pyproject.toml`、node 後端的 `package.json`、`pom.xml` 等 | 目前沒有附錄，走下方退路 |

沒有對應附錄：照本 skill 的通用方法，加上專案既有程式的寫法（先找 2–3 個同類檔當樣板；有裝 workspace 就照 `workspace:convention-first`（可選））。做完問使用者要不要把這次的寫法整理成新附錄 `references/stacks/<stack>.md`，回報寫「附錄：無（照既有程式）」。

## 1. Job 設計原則

1. **薄**：Job 只負責被排程叫起、轉呼叫 Application 服務；業務邏輯在服務（見 `layered-architecture`）。
2. **冪等**：重跑一次結果相同（排程重疊、重試、手動觸發都會發生）。
3. **可取消**：接收取消權杖，長迴圈中檢查。
4. **有紀錄**：開始、結束、處理筆數、失敗原因；用專案既有的 Job 日誌機制。
5. 失敗讓例外往上拋給排程框架記錄與重試，不要吞掉。
6. 範例領域用中性的 `Order`。

## 2. 註冊

- Job 類別與其相依註冊到 DI，生命週期與相依一致（Job 不得被 Singleton 持有而去用 Scoped 服務）。
- 註冊集中在專案既有的排程註冊檔，不散落。

## 3. 排程類型

| 類型 | 適用 | 注意 |
|------|------|------|
| 固定 Cron | 週期固定（每分鐘／小時／日） | 作業時間超過週期會重疊，需防重入或確保冪等 |
| 一次性延遲 | 事件觸發後延後執行 | 失敗重試次數要明確 |
| 自動重排 | 間隔不固定、依結果決定下次時間 | 先決定失敗是否仍重排；失敗重排要加延遲，避免狂跑 |

每個週期作業用**唯一 id** 註冊，同 id 會互相覆蓋。

## 4. 管理頁面分類（可選）

專案若有管理頁面分組（銷售、同步、維護……），沿用既有分類；沒有就不加。

## 5. 檢查清單

- [ ] Job 只轉呼叫服務，業務邏輯不在 Job
- [ ] 冪等、可取消、有紀錄
- [ ] DI 生命週期正確並已註冊
- [ ] 排程 id 唯一，重疊情境已處理
- [ ] 失敗路徑（重試、重排）有明確決定並測試
