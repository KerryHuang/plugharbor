---
name: i18n-implementation
description: 前端 i18n 違規偵測與翻譯 key 組織——系統性掃出硬寫字串、依 feature 而非元件組織 key、處理 template literal 的部分硬寫。Use when refactoring pages, creating new features, or fixing i18n violations；觸發：「i18n 違規」「這頁還有硬寫中文」「翻譯 key 怎麼組織」「補 i18n」。
---

# i18n Implementation Specialist

掃出 i18n 違規，並以可維護的方式組織翻譯 key。

**前提**：`useI18n`、locale 切換、`LocaleSelect` 等通常由 i18n framework（如 vue-i18n）或專案的共享元件庫提供；元件端統一取用，不各自 new instance。

## i18n 違規偵測

**適用**：重構頁面或開發新功能時。

**例外**：純開發用 debug 文字（非 user-facing）。

**偵測策略**：

1. 掃 template 裡的硬寫字串（中文、英文、日文）
2. 檢查所有 user-facing 情境：
   - 表格 header 與 caption
   - 表單 label 與 placeholder
   - 錯誤 / 成功訊息
   - tooltip 與 help text
   - 空狀態訊息
   - template literal（例如 "材質: {{ value }}"）

**組織模式**：

```
[domain].[feature].[area].*
├── pageTitle
├── tabs.*
├── sections.*
│   ├── columns.*
│   ├── filters.*
│   └── empty.*
├── actions.*
└── messages.*
    ├── success.*
    └── errors.*
```

**依 feature 領域組織，而非依元件** — 這樣相關元件能共用 key、結構也好維護。

**Template literal 模式**：

```vue
<!-- 錯：硬寫前綴 -->
<div>材質: {{ material }}</div>

<!-- 對：前綴也走 i18n -->
<div>{{ t('columns.materialName') }}: {{ material }}</div>
```

**理由**：即使只有部分硬寫也算違規。依 feature 組織讓相關元件共用 key，結構才可維護。

## 成效指標

- **i18n 覆蓋**：100% user-facing 文字可翻譯
- **key 組織**：依 feature 結構（非依元件）
- **template literal**：零硬寫前綴 / 後綴
