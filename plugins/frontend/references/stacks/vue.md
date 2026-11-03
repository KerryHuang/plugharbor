# 附錄：Vue 3 + TypeScript + Quasar + Pinia + TanStack Query

偵測線索：`package.json` dependencies 有 `vue`。以下寫法由舊 `frontend-vue` plugin 搬來，供 `frontend-architecture`、`component-logic`、`i18n`、`runtime-debug` 與審查共用。

## 架構（frontend-architecture）

### 分層違規修正

```typescript
// ❌ 違規：直接 import Infrastructure
import { apiClient } from '@/infrastructure/api';
await apiClient.post(...);

// ✅ 正確：透過 Application 層
import { useCreateMutation } from '@/application/mutations';
const { mutate } = useCreateMutation();
mutate(data);
```

### 元件選型

優先序：`共享元件庫（若有 monorepo UI package）> App 本地元件 > Quasar 內建 > 自刻`。共用 UI（DataTable、Form、PageLayout、Select、Input 等）優先從共享元件庫或 Quasar 取用。元件復用率目標 >80% 走既有元件庫／Quasar。

### 主題違規偵測

規則：顏色使用語意化 design token，禁止硬寫 hex 或用 `$q.dark.isActive` 決定樣式。

```bash
grep -rn "#[0-9a-fA-F]\{6\}" <presentation-root> --include="*.vue" --include="*.scss"
grep -rn "\$q\.dark\.isActive" <presentation-root>
```

建議：light／dark 差異收斂到 CSS 變數（`var(--color-*)`），元件只引用語意 token；主題模式（light／dark／auto）用專案的 theme composable／store 管理。

### 狀態管理（Pinia + TanStack Query）

- 伺服器資料走 TanStack Query（`useQuery`／`useMutation`），不複製進 Pinia；mutation 成功後 `invalidateQueries` 相關 key。
- 跨頁 client 狀態用 Pinia store；單頁狀態用元件內 `ref`／`reactive`。
- 衍生資料用 `computed`，不另存。
- 清單 >50 筆啟用 Quasar 的 virtual scroll。

## 元件邏輯（component-logic）：Composable

動手前先查專案共享元件庫／utils 層或 `src/composables` 是否已有 `useConfirmDialog`、`useBreakpoint`、`useTheme` 之類 composable。

範本：

```typescript
/**
 * 處理清單項目的批次確認邏輯
 *
 * @example
 * const { handleConfirm } = useBatchConfirm({
 *   selectedItems,
 *   currentUser,
 *   showResultModal,
 * });
 */

interface BatchConfirmParams {
  selectedItems: Ref<ItemType[]>;
  currentUser: Ref<UserType | null>;
  showResultModal: Ref<boolean>;
}

export const useBatchConfirm = (params: BatchConfirmParams) => {
  const { selectedItems, currentUser, showResultModal } = params;
  const { t } = useI18n();

  const handleConfirm = async (): Promise<void> => {
    // 所有副作用收在 composable 內
    Loading.show({ message: t('loading') });

    try {
      // 業務邏輯...
      Notify.create({ message: t('success'), color: 'positive' });
    } catch (error) {
      logger.error('Error:', error);
      Notify.create({ message: t('error'), color: 'negative' });
    } finally {
      Loading.hide();
    }
  };

  return { handleConfirm };
};
```

重點：參數收 `Ref<T>`、副作用（`Loading`、`Notify`、API）收在 composable 內、參數與回傳都標型別、JSDoc 附 `@example`。

### 主題模式 composable（`useTheme`）

管理 light／dark／auto 與 computed 主題狀態，通常由共享元件庫或 host app 以 provide／inject 提供：

```typescript
const { isDark, mode, setMode, toggle, getTokenValue } = useTheme();

if (isDark.value) { /* dark 模式邏輯 */ }
setMode('dark');                       // 'light' | 'dark' | 'auto'
toggle();                              // light/dark 互切
const bgColor = getTokenValue('surface-default'); // 圖表需要實際 CSS token 值時
```

### 語意狀態色彩 composable（`useStateColor`）

domain 狀態需要對應顏色時集中管理，回傳 theme-aware 的 CSS 變數樣式：

```typescript
const { getStyle, getSubtleStyle, getValue } = useStateColor();

// 給 style binding（theme-aware CSS 變數）
const activeStyle = getStyle('active');
// { backgroundColor: 'var(--color-state-active-bg)', color: '...', borderColor: '...' }

// subtle 變體
const idleSubtle = getSubtleStyle('idle');

// 給圖表用（實際 computed 值）
const chartColors = [getValue('active'), getValue('idle'), getValue('error')];
```

狀態清單依專案 domain 定義；重點是把「狀態 → 顏色」集中在一處。

## i18n（vue-i18n）

`useI18n`、locale 切換、`LocaleSelect` 通常由 vue-i18n 或共享元件庫提供，元件端統一取用。

template literal 的前綴也要走 i18n：

```vue
<!-- 錯：硬寫前綴 -->
<div>材質: {{ material }}</div>

<!-- 對：前綴也走 i18n -->
<div>{{ t('columns.materialName') }}: {{ material }}</div>
```

## 執行期除錯（runtime-debug）

以下皆用 `evaluate_script`（或 `browser_evaluate`）執行。

### Vue 警告

元件 prop 型別不符等 Vue warning 會出現在 console，依警告的元件名定位。

### Pinia state

```js
// 取所有 Pinia store state
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
// 取指定 store
() => {
  const pinia = document.querySelector('#app').__vue_app__.config.globalProperties.$pinia
  const store = pinia._s.get('{storeId}')
  return store ? JSON.parse(JSON.stringify(store.$state)) : 'Store not found'
}
```

### 元件 props／setup state

```js
// 傳入元素，經 Vue 內部取元件 props/setup state
(el) => {
  const instance = el.__vue_parent_component || el.__vueParentComponent
  if (!instance) return 'No Vue instance'
  return {
    props: JSON.parse(JSON.stringify(instance.props)),
    data: JSON.parse(JSON.stringify(instance.setupState || {}))
  }
}
```

### TanStack Query 快取

```js
// 列出所有 query key 與狀態
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

### Realtime 連線

```js
// 檢查 realtime hub 連線狀態；屬性名依實際注入調整
() => {
  const app = document.querySelector('#app').__vue_app__
  const gp = app.config.globalProperties
  const connection = gp.$signalR || gp.$hub || gp.$ws
  if (!connection) return 'No realtime connection found on globalProperties'
  return {
    state: connection.state,
    connectionId: connection.connectionId,
    baseUrl: connection.baseUrl
  }
}
```

### Router

```js
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

## 審查 checklist（Vue 檔變更時）

對照 composable 模式：

| 檢查 | 準則 |
|---|---|
| 邏輯抽取 | 業務邏輯 >50 行 → 抽成 composable |
| 單一職責 | 一個 composable 一個關注點 |
| Reactive 參數 | 接 `Ref<T>` |
| Side effect 隔離 | Loading／Notify／API 收在 composable 內 |
| 型別安全 | 明確 params interface＋回傳型別 |

另查：無硬寫字串（i18n）、Presentation 不直接 import Infrastructure、無硬寫顏色。

## 發版與 CI 指令

發版前品質閘（依專案 package manager，bun／pnpm／npm 擇一）：type-check（如 `bun type-check`）、lint（如 `bun lint`）。`CHANGELOG.md` 與 `package.json` 是 release metadata 檔。

## 常見坑

- 症狀：Pinia／元件檢視回傳 `undefined` 或拋 circular structure。
  原因：`#app` 選擇器不對、`__vue_app__` 不存在，或直接回傳了 reactive proxy。
  修法：確認掛載點 selector；回傳前 `JSON.parse(JSON.stringify(...))`。
- 症狀：`$queryClient` 取不到。
  原因：專案沒把 queryClient 掛在 `globalProperties`（可能用 `provide`）。
  修法：改從專案實際注入處取，或在 app 初始化處暫掛 `window.__qc` 除錯，用完移除。
- 症狀：元件內到處散寫 `$q.dark.isActive` 判斷樣式，切主題後局部顏色錯。
  原因：樣式不是走語意 token。
  修法：改引用 `var(--color-*)`，主題判斷收進 `useTheme`。
- 症狀：把 API 回應同時存進 Pinia 與 TanStack Query，兩邊資料不一致。
  原因：伺服器資料有兩個來源。
  修法：只留 query cache；mutation 成功後 `invalidateQueries`。
- 症狀：composable 內自建 state，父元件拿不到最新值。
  原因：參數收了純值而非 `Ref<T>`，或 state 所有權放錯。
  修法：參數收 `Ref<T>`，state 留在父元件。
- 症狀：snapshot 的 UID 點下去沒反應或點錯元素。
  原因：Vue 重新渲染後 UID 已變。
  修法：互動前重新快照。
