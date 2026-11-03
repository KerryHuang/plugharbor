---
name: layered-architecture
description: 分層架構（Domain / Application / Infrastructure / 進入層）開發：依賴規則、新功能開發順序、各層該放什麼、DI 註冊位置。附 .NET 附錄。Use when 新增功能、建立實體、定義介面、實作服務／Repository、遵循分層架構規範、clean architecture、layered architecture、分層開發、依賴方向檢查。
---

# 分層架構開發

## 0. 偵測技術棧與附錄

先看專案的 `*.csproj`／`*.sln`、`go.mod`、`pyproject.toml`、`package.json`、`pom.xml`、解決方案／模組目錄結構，對照下表載入附錄，並在回報第一行寫「附錄：<檔名>」。

| 偵測到 | 附錄 |
|---|---|
| `*.csproj`／`*.sln`（.NET） | `${CLAUDE_PLUGIN_ROOT}/references/stacks/dotnet.md`（專案結構、各層範本、DI 註冊位置） |
| `go.mod`、`pyproject.toml`、node 後端的 `package.json`、`pom.xml` 等 | 目前沒有附錄，走下方退路 |

沒有對應附錄：照本 skill 的通用方法，加上專案既有程式的寫法（先找 2–3 個同類檔當樣板；有裝 workspace 就照 `workspace:convention-first`（可選））。做完問使用者要不要把這次的寫法整理成新附錄 `references/stacks/<stack>.md`，回報寫「附錄：無（照既有程式）」。

## 1. 四層與依賴規則

| 層級 | 放什麼 | 可依賴 | 禁止依賴 |
|------|--------|--------|----------|
| Domain | Entity、領域規則、Repository／服務**介面** | 無 | 任何其他層、任何框架 |
| Application | 用例（Service／Handler）、DTO、驗證 | Domain | Infrastructure、進入層 |
| Infrastructure | Repository 實作、DB 存取、外部服務 client | Domain、Application | 進入層 |
| 進入層 | API Controller／Job／CLI／UI | 全部 | - |

依賴方向一律**由外向內**：外層知道內層，內層不知道外層。Domain 不引用框架（純物件＋介面）。專案層數不同（例如合併 Application 與 Infrastructure）時，保留「內層不依賴外層」這條不變量即可。

## 2. 新功能開發順序

```
1. Domain         → Entity + 介面
2. Application    → Service／Handler
3. Infrastructure → Repository 實作
4. 進入層         → Controller／Job
```

由內向外做，每層完成就能單獨編譯與測試。

## 3. 邏輯放哪

- 業務規則只放 Application（或 Domain 內的實體方法），**不放** Repository、Controller。
- Repository 介面定義在 Domain（或 Application），實作在 Infrastructure；Application 只認介面。
- 跨 Entity 用 ID 參照，不直接持有物件引用。
- 進入層只做：解析輸入、呼叫用例、轉換輸出；不做業務判斷。
- DI 註冊集中在各層自己的擴充檔，新增元件時同步註冊（位置見附錄）。

## 4. 驗證依賴方向

依專案能用的方式檢查，擇一或並用：

- 專案／模組參照（內層是否出現指向外層的參照）。
- import／using 掃描：Domain 檔案裡出現框架或 Infrastructure 命名空間即違規。
- 專案自帶的架構測試或 lint 規則。

發現違規先修方向，再談功能；系統性違規（橫跨多模組）→ 派 `dev-flow:architect` 評估（可選；沒裝 dev-flow 就用 general-purpose agent，prompt 帶角色說明：「你是架構顧問，給 2–3 個方案與 trade-off，不寫實作程式碼」）。派工 prompt 要帶上 §0 載入的附錄絕對路徑（`${CLAUDE_PLUGIN_ROOT}` 展開後），agent 才讀得到；general-purpose 退路也一樣。

## 5. 檢查清單

- [ ] 新檔案放在正確的層，沒有反向依賴
- [ ] Domain 沒有框架相依
- [ ] 介面在內層、實作在外層，且已註冊 DI
- [ ] 業務邏輯不在 Repository／Controller
- [ ] 沿用既有命名與目錄慣例（找 2–3 個同類檔對照）
- [ ] 用專案自帶指令建置並跑相關測試

## 相關 skill

- 資料存取細節：`data-access`；實體定義：`domain-model`；用例拆分：`cqrs`；對外介面：`api-endpoint`；背景作業：`background-job`。
