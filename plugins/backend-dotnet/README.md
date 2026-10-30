# backend-dotnet

.NET Clean Architecture 後端能力 plugin — 收斂多個 .NET 專案共通的產碼樣板、測試做法與後端 agent。

## 定位

`[backend]` .NET 8/9 + Clean Architecture / CQRS / Repository / EF Core / Dapper 技術棧的產碼與審查能力。範例識別符已中性化（用 `Order`/`Customer` 等通用領域名），落地時替換成專案實際命名。

## Skills（9）

### 產碼
| Skill | 用途 |
|-------|------|
| `cqrs-handler` | MediatR CQRS Command/Query Handler 生成 |
| `repository-pattern` | 繼承共用泛型基底的 Repository 生成 |
| `webapi-controller` | ASP.NET Core CRUD Controller 生成 |
| `dapper-query` | Dapper 複雜查詢（CTE 分頁、排序白名單防注入） |
| `domain-entity` | EF Core Entity 映射（標準 `[Column]`、Ext 擴充表模式） |
| `clean-architecture` | Domain/Application/Infrastructure/WebJob 四層建立與依賴 |
| `hangfire-job` | Hangfire Job 建立/DI/排程範本 |

### 測試
| Skill | 用途 |
|-------|------|
| `unit-testing` | xUnit 測試（Handler/Validator/Repository），含 test-templates references |
| `tdd-cycle` | Red-Green-Refactor 循環 |

## Agents（5）

由三套後端專案的 agent 收斂而成：

| Agent | model | 職責 |
|-------|-------|------|
| `architect` | opus | 技術選型/架構決策/ADR |
| `developer` | sonnet | CQRS/Repository/Entity 實作 |
| `reviewer` | opus | 對照架構慣例審查（唯讀） |
| `debugger` | opus | build/測試/錯誤診斷 |
| `tester` | sonnet | 測試品質/TDD Red |

## License

MIT
