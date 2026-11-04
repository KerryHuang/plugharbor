# backend

後端開發職責 plugin。SKILL.md 寫不綁技術的通用方法，技術寫法放「技術棧附錄」；換技術棧只要補一份附錄。

## 定位

`[職責]` 後端分層、用例、資料存取、API、背景作業、單元測試的做法。與流程類 plugin（如 `lifecycle`）、工作區工具（`workspace`）互不依賴，叫用都是可選。

## 安裝

```bash
claude plugin marketplace add https://github.com/KerryHuang/plugharbor.git
claude plugin install backend@plugharbor
```

## 技術棧附錄

每個 skill 開頭先偵測專案技術棧，載入對應附錄並在回報第一行標「附錄：<檔名>」。

| 技術棧 | 偵測線索 | 附錄 |
|---|---|---|
| .NET | `*.csproj`、`*.sln` | `references/stacks/dotnet.md`（共用）、各 skill 自己 references 目錄裡的 dotnet.md |
| 其他（Go、Python、Node 後端、Java 等） | `go.mod`、`pyproject.toml`、`package.json`、`pom.xml` | 目前沒有附錄 |

沒有對應附錄時：照 skill 的通用方法加上專案既有程式的寫法，做完會問要不要把這次的寫法整理成新附錄 `references/stacks/<stack>.md`。

## Skills（7）

| Skill | 用途 |
|-------|------|
| `layered-architecture` | 分層架構與依賴規則、新功能開發順序 |
| `cqrs` | Command／Query／Notification 用例、交易管線、分頁 |
| `data-access` | Repository、查詢物件、ORM 與 micro-ORM 取捨、分頁與排序白名單 |
| `domain-model` | 實體與資料表映射、legacy 欄位、擴充表策略 |
| `api-endpoint` | 標準 CRUD 端點、版本控制、回應模型、分頁契約 |
| `background-job` | 背景作業與排程設計、DI 註冊、自動重排 |
| `unit-testing` | 單元測試流程、價值複審剪枝、個資脫敏 |

## 與其他 plugin 的銜接（皆可選）

- 派 agent 審查／選型／測試：`lifecycle:architect`、`lifecycle:developer`、`lifecycle:reviewer`、`lifecycle:tester`、`lifecycle:debugger`；沒裝 lifecycle 就用 general-purpose agent，prompt 帶角色說明。
- 慣例優先、TDD 循環：`workspace:convention-first`、`workspace:debugging`；沒裝就照專案既有程式與 Red-Green-Refactor 自行進行。

## License

MIT
