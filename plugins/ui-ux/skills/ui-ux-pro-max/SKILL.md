---
name: ui-ux-pro-max
description: "UI/UX 設計知識庫與智能建議。涵蓋 67 種 styles、96 組 color palettes、56 組 font pairings、98 條 UX guidelines、25 種 charts，橫跨 13 種技術棧（React、Next.js、Vue、Svelte、SwiftUI、React Native、Flutter、Tailwind、shadcn/ui）。觸發詞：UI 設計、UI/UX、版面、配置、配色、色彩、typography、字體搭配、排版、可及性、accessibility、動畫、互動、hover、陰影、漸層、風格選擇、design system；plan／build／create／design／implement／review／fix／improve／optimize／refactor UI code。適用專案：website、landing page、dashboard、admin panel、e-commerce、SaaS、portfolio、blog、mobile app、.html／.tsx／.vue／.svelte。元件：button、modal、navbar、sidebar、card、table、form、chart。風格：glassmorphism、claymorphism、minimalism、brutalism、neumorphism、bento grid、dark mode、responsive、skeuomorphism、flat design。整合 shadcn/ui MCP 進行元件搜尋與範例查詢。"
---
# UI/UX Pro Max — 設計知識庫

Web 與 mobile 應用的完整設計指南。內含 67 種 styles、96 組 color palettes、56 組 font pairings、98 條 UX guidelines、25 種 chart types，橫跨 13 種技術棧。以可搜尋的資料庫搭配優先級導向的建議規則。

## 何時套用

以下情境參照本知識庫：
- 設計新的 UI 元件或頁面
- 挑選 color palettes 與 typography
- 審查程式碼的 UX 問題
- 製作 landing page 或 dashboard
- 落實 accessibility 需求

## 規則類別（依優先級）

| 優先級 | 類別 | 影響 | Domain |
|----------|----------|--------|--------|
| 1 | Accessibility | CRITICAL | `ux` |
| 2 | Touch & Interaction | CRITICAL | `ux` |
| 3 | Performance | HIGH | `ux` |
| 4 | Layout & Responsive | HIGH | `ux` |
| 5 | Typography & Color | MEDIUM | `typography`、`color` |
| 6 | Animation | MEDIUM | `ux` |
| 7 | Style Selection | MEDIUM | `style`、`product` |
| 8 | Charts & Data | LOW | `chart` |

## 速查（Quick Reference）

### 1. Accessibility（CRITICAL）

- `color-contrast` — 正文最低 4.5:1 對比
- `focus-states` — 互動元素要有可見的 focus ring
- `alt-text` — 有意義的圖片要有描述性 alt text
- `aria-labels` — icon-only 按鈕要加 aria-label
- `keyboard-nav` — Tab 順序與視覺順序一致
- `form-labels` — 用 label 搭配 for 屬性

### 2. Touch & Interaction（CRITICAL）

- `touch-target-size` — 觸控目標最小 44x44px
- `hover-vs-tap` — 主要互動用 click／tap，不倚賴 hover
- `loading-buttons` — async 操作進行中禁用按鈕
- `error-feedback` — 錯誤訊息清楚、貼近問題發生處
- `cursor-pointer` — 可點擊元素加上 cursor-pointer

### 3. Performance（HIGH）

- `image-optimization` — 使用 WebP、srcset、lazy loading
- `reduced-motion` — 檢查 prefers-reduced-motion
- `content-jumping` — 為 async 內容預留空間，避免版面跳動

### 4. Layout & Responsive（HIGH）

- `viewport-meta` — width=device-width initial-scale=1
- `readable-font-size` — mobile 正文最小 16px
- `horizontal-scroll` — 內容須容納於 viewport 寬度內
- `z-index-management` — 定義 z-index scale（10、20、30、50）

### 5. Typography & Color（MEDIUM）

- `line-height` — 正文用 1.5–1.75
- `line-length` — 每行限制 65–75 字元
- `font-pairing` — heading／body 字型個性要匹配

### 6. Animation（MEDIUM）

- `duration-timing` — micro-interaction 用 150–300ms
- `transform-performance` — 用 transform／opacity，勿動 width／height
- `loading-states` — skeleton screen 或 spinner

### 7. Style Selection（MEDIUM）

- `style-match` — style 要匹配產品類型
- `consistency` — 全站頁面用同一套 style
- `no-emoji-icons` — 用 SVG icon，不用 emoji

### 8. Charts & Data（LOW）

- `chart-type` — chart 類型要匹配資料類型
- `color-guidance` — 使用符合 accessibility 的色盤
- `data-table` — 提供 table 替代方案以利 accessibility

## 如何使用

透過下方 CLI 工具搜尋特定 domain。

---

## CLI 工作流程（選配）

本 skill 內附 CLI（`scripts/search.py`）與設計資料庫（`data/`）時，可產生完整 Design System 並做細部搜尋：
前置需求、四步使用流程、可用 domain／stack、範例、輸出格式與訣竅見 `references/cli-workflow.md`。

CLI 不在時直接使用本文件的速查、專業 UI 通用規則與交付前檢查表即可。

---

## 專業 UI 通用規則

以下是常被忽略、卻會讓 UI 顯得不專業的問題：

### Icons 與視覺元素

| 規則 | Do | Don't |
|------|----|----- |
| **No emoji icons** | 用 SVG icon（Heroicons、Lucide、Simple Icons） | 拿 emoji（🎨 🚀 ⚙️）當 UI icon |
| **穩定的 hover 狀態** | 用 color／opacity 過渡 | 用 scale transform 造成版面位移 |
| **正確的品牌 logo** | 從 Simple Icons 找官方 SVG | 亂猜或用錯誤的 logo 路徑 |
| **一致的 icon 尺寸** | 固定 viewBox（24x24）搭配 w-6 h-6 | 隨意混用不同 icon 尺寸 |

### 互動與游標

| 規則 | Do | Don't |
|------|----|----- |
| **Cursor pointer** | 所有可點擊／可 hover 的 card 加 `cursor-pointer` | 互動元素留預設游標 |
| **Hover feedback** | 提供視覺回饋（color、shadow、border） | 完全看不出元素可互動 |
| **平滑過渡** | 用 `transition-colors duration-200` | 瞬間切換或太慢（>500ms） |

### Light／Dark Mode

優先使用 design system 的 semantic tokens／CSS variables（如 surface、text、border、muted 等語意色），**不要 hardcode** 十六進位色碼或框架固定色階；dark mode 靠 token 自動切換，避免在樣式邏輯裡寫 dark 模式的條件分支。若專案未提供 token 系統，至少確保下列對比：

| 規則 | Do | Don't |
|------|----|----- |
| **Glass card 淺色模式** | 用 `bg-white/80` 或更高不透明度 | 用 `bg-white/10`（過度透明） |
| **淺色模式文字對比** | 正文用 `#0F172A`（slate-900） | 用 `#94A3B8`（slate-400）當正文 |
| **淺色模式 muted 文字** | 至少 `#475569`（slate-600） | 用 gray-400 或更淺 |
| **邊框可見度** | 淺色模式用 `border-gray-200` | 用 `border-white/10`（看不見） |

### Layout 與 Spacing

| 規則 | Do | Don't |
|------|----|----- |
| **Floating navbar** | 加 `top-4 left-4 right-4` 間距 | 貼死 `top-0 left-0 right-0` |
| **Content padding** | 為固定 navbar 高度預留空間 | 讓內容藏在 fixed 元素後面 |
| **一致的 max-width** | 統一用 `max-w-6xl` 或 `max-w-7xl` | 混用不同的容器寬度 |

---

## 交付前檢查表

交付 UI 程式碼前，逐項確認：

### 視覺品質
- [ ] 沒有拿 emoji 當 icon（改用 SVG）
- [ ] 所有 icon 出自同一套 icon set（Heroicons／Lucide）
- [ ] 品牌 logo 正確（已從 Simple Icons 核對）
- [ ] Hover 狀態不造成版面位移
- [ ] 直接用 theme 色（如 bg-primary），非 var() 包裝

### 互動
- [ ] 所有可點擊元素都有 `cursor-pointer`
- [ ] Hover 狀態提供清楚的視覺回饋
- [ ] 過渡平滑（150–300ms）
- [ ] 鍵盤操作有可見的 focus 狀態

### Light／Dark Mode
- [ ] 優先使用 semantic tokens／CSS variables，未 hardcode 色碼
- [ ] 淺色模式文字對比足夠（最低 4.5:1）
- [ ] Glass／透明元素在淺色模式下可見
- [ ] 邊框在兩種模式下都可見
- [ ] 交付前兩種模式都測過

### Layout
- [ ] Floating 元素與邊緣有適當間距
- [ ] 沒有內容被 fixed navbar 遮住
- [ ] 在 375px、768px、1024px、1440px 皆 responsive
- [ ] mobile 無水平捲動

### Accessibility
- [ ] 所有圖片有 alt text
- [ ] 表單 input 有 label
- [ ] 顏色不是唯一的辨識指標
- [ ] 尊重 `prefers-reduced-motion`
