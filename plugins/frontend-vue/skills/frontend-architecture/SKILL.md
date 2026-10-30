---
name: frontend-architecture
description: Vue 3 + TypeScript + Quasar 架構決策專家——分層合規、元件選型、DDD 邊界檢查、大型元件重構、效能策略。Use when making architecture decisions, checking layer violations, or planning refactoring；觸發：「前端架構」「分層違規」「元件該放哪層」「重構這個大元件」「architecture review」。
---

# Frontend Architecture Specialist

Vue 3 + TypeScript + Quasar 專案的架構決策：分層合規、元件選型、重構策略與效能把關。

## 核心職責

1. **元件選型** — 依既定優先序挑元件，優先復用而非自刻
2. **DDD 分層合規** — Presentation ← Application ← Domain ← Infrastructure
3. **大型重構** — 300+ 行元件採分階段拆解
4. **效能** — virtual scrolling、lazy loading、code splitting

## 架構原則

**Clean Architecture（四層）**：

```
Presentation → Application → Domain → Infrastructure
```

**鐵律**：Presentation 層**不得**直接 import Infrastructure 層。

**違規偵測**：

```bash
# 找出 presentation 直接引用 infrastructure/api 層的地方
grep -rn "from '.*infrastructure'" <presentation-root>
grep -rn "from '.*api'" <presentation-root>
```

**修正模式**：

```typescript
// ❌ 違規：直接 import Infrastructure
import { apiClient } from '@/infrastructure/api';
await apiClient.post(...);

// ✅ 正確：透過 Application 層
import { useCreateMutation } from '@/application/mutations';
const { mutate } = useCreateMutation();
mutate(data);
```

## 元件選型

**優先序**：`共享元件庫（若有 monorepo UI package）> App 本地元件 > Quasar 內建 > 自刻`

共用 UI 元件（DataTable、Form、PageLayout、Select、Input 等）優先從專案的共享元件庫或 Quasar 取用；能用 Quasar 內建就不要自刻。

**建立任何新元件前**：

```bash
# 1. 查共享元件庫（若有）
grep -rn "ComponentName" packages/*/src/ui/

# 2. 查 App 本地元件
grep -rn "ComponentName" src/presentation/
```

## 重構策略

**元件 >300 行、或有 3+ 種違規類型時**：

1. **盤點** — 列出所有違規（i18n、DDD 分層、元件重複造輪）
2. **表層修正** — i18n key、替換為既有元件（低風險）
3. **架構修正** — DDD 分層合規、抽 composable（高影響）
4. **清理** — 移除死碼與孤兒 import

**原則**：先修簡單的，讓真正的需求浮現。

## 快速參考

| 面向             | 目標                       |
| ---------------- | -------------------------- |
| 元件復用率       | >80% 走既有元件庫 / Quasar |
| 分層違規         | 零                         |
| 型別覆蓋         | 100% strict                |
| i18n 覆蓋        | 100% 可翻譯                |
| 主題合規         | 100% 語意化 token          |
| 互動延遲         | <100ms                     |
| 清單 >50 筆      | 啟用 virtual scrolling     |

## 主題系統

**規則**：所有顏色**必須**使用語意化 design token，禁止硬寫 hex 或用 `$q.dark.isActive` 決定樣式。

**違規偵測**：

```bash
# 找硬寫的顏色
grep -rn "#[0-9a-fA-F]\{6\}" <presentation-root> --include="*.vue" --include="*.scss"
# 找用 $q.dark.isActive 決定樣式的地方
grep -rn "\$q\.dark\.isActive" <presentation-root>
```

**建議做法**：把 light/dark 差異收斂到 CSS 變數（`var(--color-*)`），元件只引用語意 token；主題模式（light/dark/auto）用專案的 theme composable/store 管理，不在元件內散寫判斷。

## 相關 skills

- `vue-composables` — 業務邏輯抽 composable
- `i18n-implementation` — 翻譯 key 組織與違規偵測
- `chrome-devtools-debug` — 執行中前端的除錯
