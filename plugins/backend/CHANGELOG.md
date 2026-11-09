# Changelog

格式：每次改動 `skills/`、`agents/`、`references/` 時，於最上方新增版本條目並同步 bump 版號（規則見 `.claude/rules/version-consistency.md`）。

## [1.0.3] - 2026-11-10

- docs: 7 個 skill 的 frontmatter 加 `triggers` 欄位（單行 JSON 陣列，不進 skill 清單、description 不變）。這個 plugin 被明確停用時，toolkit 的 `disabled-skills.py` 會拿它比對使用者訊息，提示這個 skill 存在。起因同 toolkit 0.18.0：別的專案跑 /doctor 關掉少用的 plugin 後，之後要用時找不到。

## [1.0.2] - 2026-11-04

- fix: 派工與退路改指向 `lifecycle`（sa-flow／delivery-flow／dev-flow 已合併為 lifecycle）。

## [1.0.1] - 2026-11-03

- fix: 派 `dev-flow` agent（或 general-purpose 退路）時，把 §0 載入的附錄絕對路徑寫進派工 prompt；`unit-testing` 補沒裝 dev-flow 時的退路。

## [1.0.0] - 2026-11-03

- feat: 新 plugin，自 backend-dotnet 改寫成「通用方法＋技術棧附錄」。skill 對照：`clean-architecture`→`layered-architecture`、`cqrs-handler`→`cqrs`、`repository-pattern`＋`dapper-query`→`data-access`、`domain-entity`→`domain-model`、`webapi-controller`→`api-endpoint`、`hangfire-job`→`background-job`、`unit-testing`→`unit-testing`。
- feat: .NET 寫法（MediatR、EF Core、Dapper、ASP.NET Core、Hangfire、xUnit／Moq 與範例程式）搬進附錄 `references/stacks/dotnet.md` 與各 skill 自己 references 目錄裡的 dotnet.md；每份附錄含「常見坑」。沒有對應附錄的技術棧走「照專案既有程式」退路。
- feat: `tdd-cycle` 的通用 Red-Green-Refactor 併入 `workspace:debugging`；.NET 專屬指令併入 .NET 附錄。
- refactor: 五個技術版 agent（architect、developer、reviewer、tester、debugger）改為不綁技術的通用版，移到 `dev-flow` 的 `agents/`。
- feat: 加 `package.json`（`pi.skills`），pi 也載入得到。
