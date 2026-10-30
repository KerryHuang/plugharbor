# CLI 工作流程（設計資料庫搜尋）

## 前置需求（Prerequisites）

確認是否已安裝 Python：

```bash
python3 --version || python --version
```

若未安裝，依使用者的 OS 安裝：

**macOS：**
```bash
brew install python3
```

**Ubuntu/Debian：**
```bash
sudo apt update && sudo apt install python3
```

**Windows：**
```powershell
winget install Python.Python.3.12
```

> 註：CLI 依賴本 skill 內附的 `scripts/`（search.py 等）與 `data/`（設計資料庫 CSV）。若這兩個目錄不在，CLI 無法運作——此時仍可直接參照本文件的速查、專業 UI 規則與交付前檢查表。

---

## 使用流程

當使用者提出 UI/UX 工作（design、build、create、implement、review、fix、improve）時，依此流程進行：

### Step 1：分析使用者需求

從使用者請求中萃取關鍵資訊：
- **Product type**：SaaS、e-commerce、portfolio、dashboard、landing page 等
- **Style 關鍵字**：minimal、playful、professional、elegant、dark mode 等
- **Industry**：healthcare、fintech、gaming、education 等
- **Stack**：React、Vue、Next.js，或預設 `html-tailwind`

### Step 2：產生 Design System（必做）

**一律先用 `--design-system`** 取得帶推理依據的完整建議：

```bash
python3 skills/ui-ux-pro-max/scripts/search.py "<product_type> <industry> <keywords>" --design-system [-p "Project Name"]
```

此指令會：
1. 平行搜尋 5 個 domain（product、style、color、landing、typography）
2. 套用 `ui-reasoning.csv` 的推理規則選出最佳匹配
3. 回傳完整 design system：pattern、style、colors、typography、effects
4. 附上要避免的 anti-patterns

**範例：**
```bash
python3 skills/ui-ux-pro-max/scripts/search.py "beauty spa wellness service" --design-system -p "Serenity Spa"
```

### Step 2b：持久化 Design System（Master + Overrides 模式）

要跨 session 保存 design system 以利階層式取用，加上 `--persist`：

```bash
python3 skills/ui-ux-pro-max/scripts/search.py "<query>" --design-system --persist -p "Project Name"
```

會建立：
- `design-system/MASTER.md` — 全域 Source of Truth，含所有設計規則
- `design-system/pages/` — 頁面層級 override 的資料夾

**帶頁面層級 override：**
```bash
python3 skills/ui-ux-pro-max/scripts/search.py "<query>" --design-system --persist -p "Project Name" --page "dashboard"
```

會額外建立：
- `design-system/pages/dashboard.md` — 相對於 Master 的頁面專屬差異

**階層式取用如何運作：**
1. 建置特定頁面（例如 Checkout）時，先查 `design-system/pages/checkout.md`
2. 若該頁面檔存在，其規則**覆蓋** Master 檔
3. 若不存在，只用 `design-system/MASTER.md`

### Step 3：以細部搜尋補強（視需要）

取得 design system 後，用 domain 搜尋補充細節：

```bash
python3 skills/ui-ux-pro-max/scripts/search.py "<keyword>" --domain <domain> [-n <max_results>]
```

**何時用細部搜尋：**

| 需求 | Domain | 範例 |
|------|--------|---------|
| 更多 style 選項 | `style` | `--domain style "glassmorphism dark"` |
| Chart 建議 | `chart` | `--domain chart "real-time dashboard"` |
| UX best practices | `ux` | `--domain ux "animation accessibility"` |
| 替代字型 | `typography` | `--domain typography "elegant luxury"` |
| Landing 結構 | `landing` | `--domain landing "hero social-proof"` |

### Step 4：Stack Guidelines（預設：html-tailwind）

取得實作層級的 best practices。若使用者未指定 stack，**預設用 `html-tailwind`**。

```bash
python3 skills/ui-ux-pro-max/scripts/search.py "<keyword>" --stack html-tailwind
```

可用 stacks：`html-tailwind`、`react`、`nextjs`、`vue`、`svelte`、`swiftui`、`react-native`、`flutter`、`shadcn`、`jetpack-compose`

---

## 搜尋參考（Search Reference）

### 可用 Domain

| Domain | 用途 | 範例關鍵字 |
|--------|---------|------------------|
| `product` | 產品類型建議 | SaaS、e-commerce、portfolio、healthcare、beauty、service |
| `style` | UI styles、colors、effects | glassmorphism、minimalism、dark mode、brutalism |
| `typography` | Font pairings、Google Fonts | elegant、playful、professional、modern |
| `color` | 依產品類型的 color palettes | saas、ecommerce、healthcare、beauty、fintech、service |
| `landing` | 頁面結構、CTA 策略 | hero、hero-centric、testimonial、pricing、social-proof |
| `chart` | Chart 類型、library 建議 | trend、comparison、timeline、funnel、pie |
| `ux` | Best practices、anti-patterns | animation、accessibility、z-index、loading |
| `react` | React／Next.js 效能 | waterfall、bundle、suspense、memo、rerender、cache |
| `web` | Web 介面準則 | aria、focus、keyboard、semantic、virtualize |
| `prompt` | AI prompts、CSS 關鍵字 | (style name) |

### 可用 Stack

| Stack | 重點 |
|-------|-------|
| `html-tailwind` | Tailwind utilities、responsive、a11y（DEFAULT） |
| `react` | State、hooks、performance、patterns |
| `nextjs` | SSR、routing、images、API routes |
| `vue` | Composition API、Pinia、Vue Router |
| `svelte` | Runes、stores、SvelteKit |
| `swiftui` | Views、State、Navigation、Animation |
| `react-native` | Components、Navigation、Lists |
| `flutter` | Widgets、State、Layout、Theming |
| `shadcn` | shadcn/ui components、theming、forms、patterns |
| `jetpack-compose` | Composables、Modifiers、State Hoisting、Recomposition |

---

## 範例流程

**使用者請求：** 「為專業護膚服務做一個 landing page」

### Step 1：分析需求
- Product type：Beauty／Spa service
- Style 關鍵字：elegant、professional、soft
- Industry：Beauty／Wellness
- Stack：html-tailwind（預設）

### Step 2：產生 Design System（必做）

```bash
python3 skills/ui-ux-pro-max/scripts/search.py "beauty spa wellness service elegant" --design-system -p "Serenity Spa"
```

**輸出：** 完整 design system，含 pattern、style、colors、typography、effects 與 anti-patterns。

### Step 3：以細部搜尋補強（視需要）

```bash
# 取得 animation 與 accessibility 的 UX 準則
python3 skills/ui-ux-pro-max/scripts/search.py "animation accessibility" --domain ux

# 視需要取得替代 typography 選項
python3 skills/ui-ux-pro-max/scripts/search.py "elegant luxury serif" --domain typography
```

### Step 4：Stack Guidelines

```bash
python3 skills/ui-ux-pro-max/scripts/search.py "layout responsive form" --stack html-tailwind
```

**接著：** 綜合 design system 與細部搜尋結果，實作設計。

---

## 輸出格式（Output Formats）

`--design-system` 支援兩種輸出格式：

```bash
# ASCII box（預設）— 適合 terminal 顯示
python3 skills/ui-ux-pro-max/scripts/search.py "fintech crypto" --design-system

# Markdown — 適合寫進文件
python3 skills/ui-ux-pro-max/scripts/search.py "fintech crypto" --design-system -f markdown
```

---

## 取得更佳結果的訣竅

1. **關鍵字要具體** — 「healthcare SaaS dashboard」優於「app」
2. **多搜幾次** — 不同關鍵字帶出不同洞察
3. **組合 domain** — Style + Typography + Color = 完整 design system
4. **一定要查 UX** — 搜「animation」「z-index」「accessibility」找常見問題
5. **善用 stack flag** — 取得實作層級的 best practices
6. **反覆迭代** — 首次搜尋不匹配就換關鍵字
