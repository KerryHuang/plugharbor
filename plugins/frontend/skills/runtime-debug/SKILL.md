---
name: runtime-debug
description: 用瀏覽器 DevTools（chrome-devtools MCP）除錯執行中的前端——console error 分流、API request 檢查、前端 state 檢視、realtime 連線、視覺回歸、表單互動、router。附 Vue 3 附錄（Vue DevTools、Pinia、TanStack Query 檢視）。Use when debugging the running frontend via browser DevTools；觸發：「除錯執行中的前端」「頁面壞了幫我看」「看 console error」「檢查 API 請求」「inspect state」。
---

# Runtime Debug

用瀏覽器 DevTools 類工具（chrome-devtools MCP）除錯執行中的前端（dev server，例如本機 `https://localhost:<port>/`）。

## 0. 偵測技術棧與附錄

先看專案的 `package.json` dependencies（`vue`、`react`、`svelte`、`@angular/core` 等）與目錄結構，對照下表載入附錄，並在回報第一行寫「附錄：<檔名>」。

| 偵測到 | 附錄 |
|---|---|
| dependencies 有 `vue` | `${CLAUDE_PLUGIN_ROOT}/references/stacks/vue.md` |
| `react`、`svelte`、`@angular/core` | 目前沒有附錄，走下方退路 |

沒有對應附錄：照本 skill 的通用方法，加上專案既有程式的寫法（先找 2–3 個同類檔當樣板；有裝 workspace 就照 `workspace:convention-first`（可選，沒裝就自己 grep 既有實作當樣板））。做完問使用者要不要把這次的寫法整理成新附錄 `references/stacks/<stack>.md`，回報寫「附錄：無（照既有程式）」。

附錄裡是框架專屬的 state 檢視（元件實例、store、query cache、router 物件）；以下流程與框架無關。

## 前置條件

- Dev server 執行中（依專案設定，注意 http／https 與 port）
- chrome-devtools MCP 已安裝並啟用
- 需登入的頁面：改用可驅動既有登入 session 的瀏覽器工具（如 `claude-in-chrome`），沒有就請使用者先在受控瀏覽器登入

## 工具對照

不同 MCP 的工具名稱略有差異；chrome-devtools MCP 的工具為 `mcp__chrome-devtools__*`，另一套 `browser_*` 命名的對應如下：

| 動作 | chrome-devtools MCP | 另一套命名 |
|---|---|---|
| 導航 | `navigate_page` | `browser_navigate` |
| 頁面結構快照（a11y tree） | `take_snapshot` | `browser_snapshot` |
| 截圖 | `take_screenshot` | `browser_take_screenshot` |
| 點擊／輸入 | `click`／`fill` | `browser_click`／`browser_type` |
| 執行 JS | `evaluate_script` | `browser_evaluate` |
| Console | `list_console_messages` | `browser_console_messages` |
| Network | `list_network_requests` | `browser_network_requests` |
| 等待 | `wait_for` | `browser_wait_for` |
| 按鍵／分頁 | `press_key`／`select_page` | `browser_press_key`／`browser_tabs` |

## 基本流程

1. 導航到 `{route}`
2. 等關鍵文字／元素出現
3. 取快照，拿到帶 UID 的頁面結構
4. 用 UID 互動或檢查

互動前一律先重新快照：UID 在每次頁面更新後會變。

## 除錯情境

### 1. Console error 分流

導航到目標頁，列出 error 等級訊息。常見方向：

- `401 Unauthorized`：身分驗證 token 過期，重新登入
- `Network Error`：後端未啟動或 CORS
- `Cannot read properties of undefined`：API 回傳結構與前端型別不符，對照 API schema／型別定義
- 框架 warning：元件 prop 型別不符等（細節看附錄）

### 2. API request 除錯

觸發動作後列 network requests（過濾靜態資源）：

- 失敗請求（4xx／5xx）：對照前端的 API 呼叫定義
- 缺少請求：動作沒觸發到 API 呼叫
- payload 問題：用執行 JS 工具檢視 request body

### 3. 前端 state 檢視

元件實例、全域 store、query cache 的取法依框架而異，見附錄。通用原則：用執行 JS 工具讀取後轉成純資料（如 `JSON.parse(JSON.stringify(...))`）再回傳，避免回傳響應式代理或循環參照。

### 4. Realtime 連線（WebSocket／SignalR 等）

檢查連線物件的 state、connectionId、baseUrl；物件掛在哪依專案注入方式調整（Vue 範例見附錄）。連不上時對照 network 的 WS／長連線請求與 console error。

### 5. 視覺回歸／版面檢查

導航到目標頁後截圖（一般、全頁、指定元素：先快照找 UID 再截該元素）。

### 6. 表單／互動測試

快照取欄位 UID → 點擊 focus → 輸入 → 點送出 → 查 console error → 查 network 驗證 API 呼叫。

### 7. Router／導航除錯

取目前 route 的 path、name、params、query、matched。取法見附錄。

## 常見錯誤

| 錯誤 | 修正 |
|---|---|
| 頁面變動後仍用舊 UID | 重新快照 |
| 頁面還沒載完就檢查 console | 先等待關鍵元素 |
| 用錯 protocol／port | 確認 dev server 實際位址 |
| 未登入就檢視需授權頁 | 改用能沿用登入 session 的瀏覽器工具 |
| 讀爆量 network log | 過濾靜態資源 |

## 相關 skills

- `frontend-architecture`：除錯揭露的是分層問題時
- `component-logic`：邏輯抽出後在執行期驗證
