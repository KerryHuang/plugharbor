---
name: chrome-devtools-debug
description: 用 Chrome DevTools MCP 除錯執行中的 Vue 3 前端——Vue/Pinia state 檢視、API request 除錯、console error 分流、TanStack Query 快取檢查、realtime 連線狀態、視覺回歸。Use when debugging the running frontend via Chrome DevTools MCP；觸發：「除錯執行中的前端」「頁面壞了幫我看」「看 console error」「檢查 API 請求」「inspect Pinia state」。
---

# Chrome DevTools Debug

用 Chrome DevTools MCP 的 `browser_*` 工具，除錯執行中的 Vue 3 前端（dev server，例如 `https://localhost:8080/`）。

## 前置條件

- Dev server 執行中（依專案設定，注意 http/https 與 port）
- Chrome DevTools MCP 已安裝並啟用
- 需登入的頁面：改用可驅動既有登入 session 的瀏覽器 MCP

## 工具對照

| 動作 | 工具 |
|--------|------|
| 導航 | `browser_navigate` |
| 快照（a11y tree） | `browser_snapshot` |
| 截圖 | `browser_take_screenshot` |
| 點擊 | `browser_click` |
| 輸入 | `browser_type` |
| 執行 JS | `browser_evaluate` |
| Console logs | `browser_console_messages` |
| Network | `browser_network_requests` |
| 等待 | `browser_wait_for` |
| 按鍵 | `browser_press_key` |
| 分頁 | `browser_tabs` |

## 工作流程：連線與檢視

```
1. browser_navigate → https://localhost:8080/{route}
2. browser_wait_for → 等關鍵文字/元素出現
3. browser_snapshot → 取得帶 UID 的頁面結構
4. 用快照裡的 UID 進行互動或檢查
```

**互動前一律先 snapshot** — UID 會在每次頁面更新後變動。

## 除錯情境

### 1. Console error 分流

```
browser_navigate → 目標頁
browser_console_messages (level: "error")
```

常見錯誤與方向：
- `401 Unauthorized` — 身分驗證 token 過期，需重新登入
- `Network Error` — 後端未啟動或 CORS 問題
- `Cannot read properties of undefined` — API 回傳結構與前端型別不符，對照 API schema/型別定義
- Vue warnings — 元件 prop 型別不符

### 2. API request 除錯

```
browser_navigate → 目標頁（觸發動作）
browser_network_requests (includeStatic: false)
```

檢查：
- **失敗請求**（4xx/5xx）— 對照前端的 API 呼叫定義
- **缺少請求** — 動作沒觸發到 API 呼叫
- **payload 問題** — 用 `browser_evaluate` 檢視 request body

### 3. Vue / Pinia state 檢視

```js
// browser_evaluate — 取所有 Pinia store state
() => {
  const app = document.querySelector('#app').__vue_app__
  const pinia = app.config.globalProperties.$pinia
  const stores = {}
  for (const [id, store] of pinia._s) {
    stores[id] = JSON.parse(JSON.stringify(store.$state))
  }
  return stores
}
```

```js
// browser_evaluate — 取指定 store
() => {
  const pinia = document.querySelector('#app').__vue_app__.config.globalProperties.$pinia
  const store = pinia._s.get('{storeId}')
  return store ? JSON.parse(JSON.stringify(store.$state)) : 'Store not found'
}
```

```js
// browser_evaluate — 透過 Vue 內部取元件 props/setup state
(el) => {
  const instance = el.__vue_parent_component || el.__vueParentComponent
  if (!instance) return 'No Vue instance'
  return {
    props: JSON.parse(JSON.stringify(instance.props)),
    data: JSON.parse(JSON.stringify(instance.setupState || {}))
  }
}
```

### 4. TanStack Query 快取檢查

```js
// browser_evaluate — 列出所有 query key 與狀態
() => {
  const app = document.querySelector('#app').__vue_app__
  const queryClient = app.config.globalProperties.$queryClient
  if (!queryClient) return 'No queryClient found'
  const cache = queryClient.getQueryCache().getAll()
  return cache.map(q => ({
    key: q.queryKey,
    status: q.state.status,
    dataUpdatedAt: new Date(q.state.dataUpdatedAt).toISOString(),
    isStale: q.isStale(),
    error: q.state.error?.message
  }))
}
```

### 5. Realtime 連線檢查（WebSocket / SignalR 等）

```js
// browser_evaluate — 檢查 realtime hub 連線狀態
() => {
  const app = document.querySelector('#app').__vue_app__
  const gp = app.config.globalProperties
  // 依實際注入的屬性名調整
  const connection = gp.$signalR || gp.$hub || gp.$ws
  if (!connection) return 'No realtime connection found on globalProperties'
  return {
    state: connection.state,
    connectionId: connection.connectionId,
    baseUrl: connection.baseUrl
  }
}
```

### 6. 視覺回歸 / 版面檢查

```
browser_navigate → 目標頁
browser_take_screenshot (type: "png")            # 一般截圖
browser_take_screenshot (type: "png", fullPage: true)  # 全頁
```

指定元素：
```
browser_snapshot → 找到元素 UID
browser_take_screenshot (type: "png", ref: "{uid}", element: "target element")
```

### 7. 表單 / 互動測試

```
browser_snapshot → 取表單欄位 UID
browser_click (ref: "{uid}") → focus 欄位
browser_type (ref: "{uid}", text: "test value")
browser_click (ref: "{submit-uid}") → 送出
browser_console_messages (level: "error") → 檢查錯誤
browser_network_requests (includeStatic: false) → 驗證 API 呼叫
```

### 8. Router / 導航除錯

```js
// browser_evaluate — 取目前 route 資訊
() => {
  const app = document.querySelector('#app').__vue_app__
  const router = app.config.globalProperties.$router
  const route = router.currentRoute.value
  return {
    path: route.path,
    name: route.name,
    params: route.params,
    query: route.query,
    matched: route.matched.map(r => r.name)
  }
}
```

## 常見錯誤

| 錯誤 | 修正 |
|---------|-----|
| 頁面變動後仍用舊 UID | 重新 `browser_snapshot` |
| 頁面還沒載完就檢查 console | 先 `browser_wait_for` |
| 用錯 protocol/port | 確認 dev server 實際位址（http/https、port） |
| 未登入就檢視需授權頁 | 改用能沿用登入 session 的瀏覽器 MCP |
| 讀爆量 network log | 設 `includeStatic: false` 過濾雜訊 |
