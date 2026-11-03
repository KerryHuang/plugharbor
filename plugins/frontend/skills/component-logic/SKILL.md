---
name: component-logic
description: 把業務邏輯從前端元件抽成可復用單元的做法——單一職責、reactive 輸入、side effect 隔離、清楚介面型別。附 Vue 3 composable 寫法附錄。Use when extracting business logic over 50 lines or creating reusable component logic；觸發：「抽 composable」「抽 hook」「這段邏輯太長要拆」「可復用邏輯」「component logic」。
---

# Component Logic

把業務邏輯從元件抽成介面乾淨、可獨立測試的單元（Vue 叫 composable、React 叫 hook、Svelte 叫 store／function）。

## 0. 偵測技術棧與附錄

先看專案的 `package.json` dependencies（`vue`、`react`、`svelte`、`@angular/core` 等）與目錄結構，對照下表載入附錄，並在回報第一行寫「附錄：<檔名>」。

| 偵測到 | 附錄 |
|---|---|
| dependencies 有 `vue` | `${CLAUDE_PLUGIN_ROOT}/references/stacks/vue.md` |
| `react`、`svelte`、`@angular/core` | 目前沒有附錄，走下方退路 |

沒有對應附錄：照本 skill 的通用方法，加上專案既有程式的寫法（先找 2–3 個同類檔當樣板；有裝 workspace 就照 `workspace:convention-first`（可選，沒裝就自己 grep 既有實作當樣板））。做完問使用者要不要把這次的寫法整理成新附錄 `references/stacks/<stack>.md`，回報寫「附錄：無（照既有程式）」。

## 先查既有

動手前先確認要抽的邏輯是否已有現成單元：共享元件庫、utils 層、既有 composables／hooks 目錄常已提供確認對話框、breakpoint、主題之類的通用邏輯。先查再建，別重複造輪子。

## 何時抽

- 適用：業務邏輯 >50 行，或會被多個元件復用。
- 不要抽：單純事件處理（<10 行、單一使用點）。

## 設計原則

1. **單一職責**：一個單元只管一件邏輯關注點
2. **Reactive 輸入**：接受響應式的輸入（ref／signal／props），不在內部自建重複 state
3. **清楚介面**：明確的參數型別與回傳型別
4. **Side effect 隔離**：副作用（loading、通知、API 呼叫）收在單元內，元件只管渲染
5. **附使用範例**：註解中放一段呼叫範例
6. **State 所有權留在父元件**：單元接收 state、回傳行為，不偷偷持有

好處：可脫離元件 context 獨立測試、跨 UI 情境復用、state 與行為分離。

## 常見類型

- **主題模式**：light／dark／auto 與衍生狀態，由共享層提供，元件統一取用，不各自判斷。
- **語意狀態色彩**：domain 狀態（流程、訂單、裝置）對應顏色集中在一處，回傳 theme-aware 的 CSS 變數樣式，元件只引用語意 token，不硬寫顏色。

兩者的 Vue 寫法見附錄。

## 成效指標

- >50 行業務邏輯已抽出
- 抽出的單元被 2+ 元件使用
- 參數與回傳 100% 標型別

## 相關 skills

- `frontend-architecture`：分層與重構整體策略
- `runtime-debug`：抽出後在執行期驗證行為
