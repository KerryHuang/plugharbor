---
name: vue-composables
description: 把業務邏輯從 Vue 元件抽成可復用 composable 的設計模式——單一職責、reactive 參數、side effect 隔離、清楚的介面型別。Use when extracting business logic >50 lines or creating reusable composables；觸發：「抽 composable」「這段邏輯太長要拆」「可復用的 hook」「composable 設計」。
---

# Vue Composables Specialist

把業務邏輯抽成介面乾淨、可獨立測試的 composable。

## 先查既有 composable

動手前先確認要抽的邏輯是否已有現成 composable——專案的共享元件庫 / utils 層、或既有 `src/composables` 常已提供 `useConfirmDialog`、`useBreakpoint`、`useTheme` 之類的通用 composable。**先查再建**，別重複造輪子。

## 抽取業務邏輯的時機

**適用**：業務邏輯 >50 行，或會被多個元件復用。

**不要抽**：單純事件處理（<10 行、單一使用點）。

**設計原則**：

1. **單一職責**：一個 composable 只管一件邏輯關注點
2. **Reactive 參數**：接 `Ref<T>` 取得反應性，而非在內部自建 state
3. **清楚介面**：明確的 params interface 與回傳型別
4. **Side effect 隔離**：所有副作用（Loading、Notify、API 呼叫）收在 composable 內
5. **JSDoc 範例**：附使用範例

**Template**：

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

**好處**：

- 可獨立測試（不需 component context）
- 跨不同 UI 情境復用
- state 所有權留在父元件
- state 與行為清楚分離

## Composable 常見類型

### 主題模式 composable（`useTheme`）

管理 light / dark / auto 主題模式與 computed 主題狀態。通常由專案的共享元件庫或 host app 透過 provide/inject 提供，元件端統一取用、不各自散寫判斷：

```typescript
const { isDark, mode, setMode, toggle, getTokenValue } = useTheme();

if (isDark.value) { /* dark 模式邏輯 */ }
setMode('dark');                       // 'light' | 'dark' | 'auto'
toggle();                              // light/dark 互切
const bgColor = getTokenValue('surface-default'); // 圖表需要實際 CSS token 值時
```

### 語意狀態色彩 composable（`useStateColor`）

當某個 domain 狀態（如流程/訂單/裝置狀態）需要對應顏色時，抽一個 composable 集中管理，回傳 theme-aware 的 CSS 變數樣式，避免在各元件硬寫顏色：

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

> 狀態清單依專案 domain 定義；重點是把「狀態 → 顏色」的對應集中在一處，元件只引用語意 token。

## 成效指標

- **邏輯抽取**：>50 行業務邏輯抽進 composable
- **復用度**：composable 被 2+ 元件使用
- **型別安全**：參數與回傳 100% 標型別
