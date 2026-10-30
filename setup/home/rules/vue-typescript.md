---
paths:
  - "**/*.vue"
  - "**/composables/**/*.ts"
  - "**/stores/**/*.ts"

# 不掛 **/*.ts、**/*.tsx：本檔是 Vue/Quasar 專屬指引，
# 而多數 .tsx／不少 .ts 屬 React／Next 專案，掛上去會給出錯誤指引。
# .ts 只掛 Vue 慣用目錄（composables／stores），不寫任何 repo 名——user 層規則不綁專案。
---

# Vue 3 + TypeScript

- 套件管理器認 lockfile（bun / pnpm / npm），不混用——混用會裝出不一致的依賴樹。
- 型別從 API schema／既有 types 引用，不重複手刻一份。
- 專案自有元件庫、UI 框架（Quasar 等）有的元件與樣式 token 就直接用（專案 rule 有優先序就照它），不手刻同功能的。
- API 呼叫走既有 service／composable 或產生的 client 層，元件內不直接 fetch／axios。
