# frontend

前端開發方法＋技術棧附錄：架構分層、元件邏輯抽取、i18n、執行期除錯。通用原則寫在 skill，框架寫法放附錄。

## 定位

`[stack]` 職責 plugin。由 skill 偵測 `package.json` 載入對應附錄；換技術棧只要補一份附錄。

## 技術棧附錄

| 偵測到 | 附錄 |
|---|---|
| `vue` | `references/stacks/vue.md`（Vue 3＋TypeScript＋Quasar＋Pinia＋TanStack Query） |
| `react`、`svelte`、`@angular/core` | 目前沒有；照通用方法加專案既有寫法，做完可請 skill 整理成新附錄 |

## 安裝

```bash
claude plugin marketplace add https://github.com/KerryHuang/plugharbor.git
claude plugin install frontend@plugharbor
```

## Skills（4）

| Skill | 用途 |
|-------|------|
| `frontend-architecture` | 分層合規、元件選型、狀態與資料取得、重構、效能 |
| `component-logic` | 業務邏輯從元件抽成可復用單元（Vue composable 見附錄） |
| `i18n` | 硬寫字串偵測、翻譯 key 組織 |
| `runtime-debug` | 用 chrome-devtools MCP 查執行中的前端問題 |

## 搭配（皆可選）

- `lifecycle:reviewer`／`lifecycle:tester`：審查與測試；沒裝就用 general-purpose subagent 附角色說明。
- `workspace:convention-first`：沒有附錄時找既有樣板；沒裝就自己 grep。

## License

MIT
