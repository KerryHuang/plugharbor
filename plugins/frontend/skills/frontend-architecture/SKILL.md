---
name: frontend-architecture
description: 前端架構決策——分層合規、元件選型、依賴方向檢查、大型元件重構、狀態管理與資料取得原則、效能策略。附 Vue 3 附錄。Use when making frontend architecture decisions, checking layer violations, or planning refactoring；觸發：「前端架構」「分層違規」「元件該放哪層」「重構這個大元件」「architecture review」「狀態放哪」。
---

# Frontend Architecture

前端專案的架構決策：分層合規、元件選型、狀態與資料取得、重構策略與效能把關。

## 0. 偵測技術棧與附錄

先看專案的 `package.json` dependencies（`vue`、`react`、`svelte`、`@angular/core` 等）與目錄結構，對照下表載入附錄，並在回報第一行寫「附錄：<檔名>」。

| 偵測到 | 附錄 |
|---|---|
| dependencies 有 `vue` | `${CLAUDE_PLUGIN_ROOT}/references/stacks/vue.md` |
| `react`、`svelte`、`@angular/core` | 目前沒有附錄，走下方退路 |

沒有對應附錄：照本 skill 的通用方法，加上專案既有程式的寫法（先找 2–3 個同類檔當樣板；有裝 workspace 就照 `workspace:convention-first`（可選，沒裝就自己 grep 既有實作當樣板））。做完問使用者要不要把這次的寫法整理成新附錄 `references/stacks/<stack>.md`，回報寫「附錄：無（照既有程式）」。

## 核心職責

1. **元件選型**：依既定優先序挑元件，優先復用而非自刻
2. **分層合規**：依賴只能由外往內
3. **大型重構**：300+ 行元件分階段拆解
4. **狀態與資料取得**：各類狀態放對地方
5. **效能**：大清單虛擬化、lazy loading、code splitting

## 分層與依賴方向

```
Presentation → Application → Domain → Infrastructure
```

- 鐵律：Presentation 層不得直接 import Infrastructure 層（API client、storage、SDK），一律經 Application 層（use case、mutation／query、service）。
- 專案分層命名不同時，先對照既有目錄把四層對上，再檢查。

違規偵測（路徑依專案調整）：

```bash
grep -rn "from '.*infrastructure'" <presentation-root>
grep -rn "from '.*api'" <presentation-root>
```

修正方向：把 presentation 裡直接呼叫 API 的程式，換成 Application 層暴露的 mutation／query／service，元件只拿結果與狀態。範例見附錄。

## 狀態管理與資料取得

| 狀態類型 | 放哪 | 原則 |
|---|---|---|
| 伺服器資料（API 回應） | 資料取得層（query cache） | 不複製進全域 store；快取、重試、失效交給 cache 層 |
| 跨頁面共用的 client 狀態 | 全域 store | 只放真正跨頁共用的；有明確所有者 |
| 單一元件／單一頁面狀態 | 元件本地 | 預設選項；不要因為「可能會共用」就上提 |
| URL 可還原的狀態（篩選、分頁） | router query／params | 可分享、可重新整理還原 |

- 資料取得集中在 Application／Infrastructure，不在元件內散落 fetch。
- mutation 成功後明確失效相關 query，不手動同步多份副本。
- 衍生資料用 computed／selector，不另存一份。

## 元件選型

優先序：`共享元件庫（若有）> App 本地元件 > UI framework 內建 > 自刻`。能用 UI framework 內建就不要自刻。

建立任何新元件前先查：

```bash
grep -rn "ComponentName" packages/*/src/ui/   # 共享元件庫（若有）
grep -rn "ComponentName" src/presentation/    # App 本地元件
```

## 重構策略

元件 >300 行、或有 3+ 種違規類型時：

1. **盤點**：列出所有違規（i18n、分層、重複造輪）
2. **表層修正**：i18n key、替換為既有元件（低風險）
3. **架構修正**：分層合規、抽出元件邏輯（見 `component-logic`）（高影響）
4. **清理**：移除死碼與孤兒 import

原則：先修簡單的，讓真正的需求浮現。

## 主題系統

所有顏色使用語意化 design token，禁止硬寫 hex 或在元件內依 dark mode 旗標決定樣式。light／dark 差異收斂到 CSS 變數，元件只引用語意 token；主題模式用專案的 theme composable／store／hook 管理，不在元件內散寫判斷。違規偵測指令見附錄。

## 快速參考

| 面向 | 目標 |
|---|---|
| 元件復用率 | >80% 走既有元件庫 |
| 分層違規 | 零 |
| 型別覆蓋 | 100% strict |
| i18n 覆蓋 | 100% 可翻譯 |
| 主題合規 | 100% 語意化 token |
| 互動延遲 | <100ms |
| 清單 >50 筆 | 啟用虛擬捲動 |

## 審查與測試

需要獨立審查或補測試時，叫 `lifecycle:reviewer`／`lifecycle:tester`（可選）；沒裝就用 general-purpose subagent，附上角色說明（審查：分層、型別、i18n、主題；測試：元件與邏輯單元測試）。派工 prompt 要帶上 §0 載入的附錄絕對路徑（`${CLAUDE_PLUGIN_ROOT}` 展開後），agent 才讀得到；general-purpose 退路也一樣。

## 相關 skills

- `component-logic`：業務邏輯抽出元件
- `i18n`：翻譯 key 組織與違規偵測
- `runtime-debug`：執行中前端的除錯
