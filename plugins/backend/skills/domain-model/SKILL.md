---
name: domain-model
description: 領域實體（Entity）定義：欄位與資料表映射、legacy 欄位名映射、驗證規則、型別對照、主表不可動時的擴充表策略。附 .NET（EF Core）附錄。Use when 建立新資料庫 Entity、定義 Domain Model、映射舊資料庫欄位、擴充表、entity mapping、data annotation、ef core entity。
---

# 領域實體（Entity）

## 0. 偵測技術棧與附錄

先看專案的 `*.csproj`（EF Core）、`go.mod`、`pyproject.toml`、`package.json`（ORM schema）、`pom.xml`、migration 目錄、既有 Entity 目錄，對照下表載入附錄，並在回報第一行寫「附錄：<檔名>」。

| 偵測到 | 附錄 |
|---|---|
| `*.csproj`／`*.sln`（.NET） | `${CLAUDE_PLUGIN_ROOT}/references/stacks/dotnet.md`（共用）＋ `references/dotnet.md`（Data Annotations、legacy 欄位映射、Ext 表） |
| `go.mod`、`pyproject.toml`、node 後端的 `package.json`、`pom.xml` 等 | 目前沒有附錄，走下方退路 |

沒有對應附錄：照本 skill 的通用方法，加上專案既有程式的寫法（先找 2–3 個同類檔當樣板；有裝 workspace 就照 `workspace:convention-first`（可選））。做完問使用者要不要把這次的寫法整理成新附錄 `references/stacks/<stack>.md`，回報寫「附錄：無（照既有程式）」。

## 1. 做法

1. 明確標記主鍵；無主鍵的唯讀來源（View、舊表）標成「無鍵、只查詢」，不拿來更新。
2. **舊系統欄位名保留在資料庫端，屬性名採專案語言慣例**，用映射標註連起來（屬性 `OrderId` ↔ 欄位 `ORDER_NO`）。
3. 顯示名稱（給 UI／文件）與驗證規則（必填、最小／最大長度、編碼）寫在實體或驗證層；錯誤訊息走集中資源（localization），不散落字串。
4. 每個屬性有說明註解。
5. 範例領域用中性的 `Order`（訂單）示範，實作時換成實際實體名。

## 2. 型別對照原則

| 資料特性 | 做法 |
|---------|------|
| 字串 | 明確長度；非 Unicode 欄位（varchar）要標示，避免隱性轉換拖慢索引 |
| 金額／數量 | 定點小數並明寫精度（如 18,2），不用浮點 |
| 日期時間 | 可為空與否要和欄位一致；明寫資料庫型別 |
| 布林 | 對應 bit／boolean；刪除標記用布林旗標 |
| 版本戳（rowversion／timestamp） | 位元組陣列，作樂觀鎖 |

## 3. 關聯欄位

- 外鍵 ID：映射 legacy 欄位名。
- 從其他表帶入的顯示名稱（非本表欄位）：註解標明來源表與欄位，且不當作可寫入欄位。

## 4. 擴充表（Ext／Satellite）策略

**舊系統主表不可新增欄位**（避免影響舊程式或跨系統相依）時，新欄位放對應擴充表（如 `OrderExt`），與主表 1:1 主鍵相對。

若新欄位需同時被主表 DTO 接收（API binding）：

1. Ext 表建立實體與其映射設定。
2. 主表 DTO 加屬性但**不加欄位映射標註**（讓 SQL 產生器自動略過），由 Handler 決定寫入哪張表。
3. Handler 注入 `I{Entity}ExtRepository`；**禁止**在 Handler 直接注入 DbContext 操作 Ext 表。
4. 評估副作用：欄位切換會觸發其他實體建立、重算 → 建專屬 Handler＋獨立 endpoint，不塞進 Create／Update 主流程。
5. 物件映射保護：對 Ext 欄位設忽略，防止系統端同步誤覆寫。
6. 測試：Handler 路由分支（欄位有值／為空）、映射設定合法性、迴歸（Ext 欄位已有值時呼叫主表更新不爆 SQL）。

## 5. 目錄結構（示意）

```
Domain/Entities/
├── {ModuleA}/   # 模組實體
├── {ModuleB}/
└── dbo/         # 舊系統原生資料表（保留 legacy 命名）
```

## 6. 檢查清單

- [ ] 主鍵或「無鍵只讀」已標明
- [ ] legacy 欄位都有映射，屬性名符合專案慣例
- [ ] 型別精度與長度明寫
- [ ] 驗證訊息走集中資源
- [ ] 動到舊主表欄位前，確認是否該改用擴充表
