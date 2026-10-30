---
name: feature
description: 開新功能分支並做領域邊界規劃——分析受影響層級、建議檔案結構、產出實作鷹架。Use when starting new feature development with planning, "開新功能", "start feature", "規劃新功能", "建功能分支".
---

# 開始新功能

建立新功能分支，並委派規劃型 subagent 做智能領域規劃。

## 工作流程

1. **檢查 Git** — `git status` 確認工作目錄乾淨、確認當前分支。
2. **委派規劃** — 讓規劃型 subagent 完成下列分析後回報：
   1. 分析領域邊界，識別受影響的層級（Domain / Application / Infrastructure / Presentation）。
   2. 檢視現有程式碼，找類似模式與可重用元件。
   3. 建議遵循 Clean Architecture 的完整檔案結構。
   4. 產出含技術考量的實作檢查清單與逐步計劃。
   5. 標出整合點與潛在風險、邊緣案例。
3. **建立分支** — `git checkout -b feature/{name}`。
4. **基準驗證** — 建置與測試確認起點乾淨（以 .NET 為例 `dotnet build && dotnet test`）。
5. **呈現計劃** — 顯示規劃分析、建議檔案結構、實作檢查清單與後續步驟。

## 規劃考量

### Clean Architecture 層級

| 層級 | 內容 |
|------|------|
| Domain | Entities、Value Objects、領域服務介面、Repository 介面 |
| Application | 應用服務、Commands/Queries（CQRS）、DTOs、Mappers、Validators |
| Infrastructure | Repository 實作、資料存取、外部整合、訊息／背景排程 |
| Presentation | API Controllers、背景工作、對外端點 |

### 技術整合考量（依專案實際採用者填入）

- **外部 API 整合**：認證授權、重試、逾時、回應驗證。
- **背景排程**：排程設定、取消令牌支援、錯誤處理與重試、日誌記錄。
- **資料存取策略**：關聯式 vs 非關聯式的取捨、索引與查詢最佳化、避免 N+1。

> 上列為常見面向清單，非強制項；只挑本功能真正涉及的整合點深入。

## 檔案結構範例

以 `<Project>` 代稱方案名稱，結構隨專案慣例調整：

```
<Project>.Domain/
├── Entities/{Feature}Entity
├── ValueObjects/{Feature}ValueObject
└── Interfaces/I{Feature}Repository

<Project>.Application/
├── Services/{Feature}Service
├── Commands/{Feature}Command、Queries/{Feature}Query
└── DTOs/{Feature}Dto

<Project>.Infrastructure/
└── Repositories/{Feature}Repository（含外部整合，如需要）

<Project>.Presentation/
├── Controllers/{Feature}Controller（如需要）
└── Jobs/{Feature}Job（如需要）

Tests/
├── {Project}.Domain.Tests/{Feature}Tests
├── {Project}.Application.Tests/{Feature}ServiceTests
└── {Project}.IntegrationTests/{Feature}IntegrationTests
```

## 重要原則

- **依賴方向正確**：外層依賴內層，Domain 不依賴任何外部。
- **善用語言新特性**：nullable reference types、primary constructors 等，依目標框架版本。
- **測試優先**：規劃時同步安排測試檔案位置與覆蓋率目標。
- **完整錯誤處理**：異常處理與日誌記錄納入規劃，不留待事後補。

## 與其他 skill 銜接

- `spec` — 建立功能規格書
- `work-on` — 執行完整開發流程
- `quality-check` — 品質檢查
- `commit` — 提交變更
