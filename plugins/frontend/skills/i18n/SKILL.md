---
name: i18n
description: 前端 i18n 違規偵測與翻譯 key 組織——系統性掃出硬寫字串、依 feature 而非元件組織 key、處理 template literal 的部分硬寫。附 Vue 3 附錄。Use when refactoring pages, creating new features, or fixing i18n violations；觸發：「i18n 違規」「這頁還有硬寫中文」「翻譯 key 怎麼組織」「補 i18n」「國際化」。
---

# i18n

掃出 i18n 違規，並以可維護的方式組織翻譯 key。

## 0. 偵測技術棧與附錄

先看專案的 `package.json` dependencies（`vue`、`react`、`svelte`、`@angular/core` 等）與目錄結構，對照下表載入附錄，並在回報第一行寫「附錄：<檔名>」。

| 偵測到 | 附錄 |
|---|---|
| dependencies 有 `vue` | `${CLAUDE_PLUGIN_ROOT}/references/stacks/vue.md` |
| `react`、`svelte`、`@angular/core` | 目前沒有附錄，走下方退路 |

沒有對應附錄：照本 skill 的通用方法，加上專案既有程式的寫法（先找 2–3 個同類檔當樣板；有裝 workspace 就照 `workspace:convention-first`（可選，沒裝就自己 grep 既有實作當樣板））。做完問使用者要不要把這次的寫法整理成新附錄 `references/stacks/<stack>.md`，回報寫「附錄：無（照既有程式）」。

前提：translate 函式、locale 切換、語系選擇元件通常由 i18n framework 或專案共享元件庫提供；元件端統一取用，不各自 new instance。

## 違規偵測

適用：重構頁面或開發新功能時。例外：純開發用 debug 文字（非 user-facing）。

1. 掃 template 裡的硬寫字串（中文、英文、日文）
2. 檢查所有 user-facing 情境：
   - 表格 header 與 caption
   - 表單 label 與 placeholder
   - 錯誤／成功訊息
   - tooltip 與 help text
   - 空狀態訊息
   - template literal（例如 "材質: {{ value }}"）

即使只有部分硬寫（前綴、後綴）也算違規。

## key 組織

依 feature 領域組織，而非依元件，相關元件才能共用 key：

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

## template literal

前綴也要走 i18n：把「材質:」硬寫在 template 裡是錯的，正確寫法是用翻譯函式取得標籤後再接動態值。各框架的語法見附錄。

## 成效指標

- 100% user-facing 文字可翻譯
- key 依 feature 結構（非依元件）
- template literal 零硬寫前綴／後綴
