# Changelog

格式：每次改動 `skills/`、`agents/`、`references/` 時，於最上方新增版本條目並同步 bump 版號（規則見 `.claude/rules/version-consistency.md`）。

## [1.0.0] - 2026-11-03

- feat!: 吸收 kid-ui plugin。`designing-kid-ui` → `designing-ui`、`auditing-kid-ui` → `auditing-ui`（skill 改名，舊名不再存在）。
- feat: 兒童專屬規範（文字／念題、防誤觸、彈窗、版面尺寸表、要一致的元件、審查加項、常見坑）移至 plugin 根 `references/audience-kids.md`；skill 開頭改為「偵測受眾」，只有使用者明確說兒童或專案標明兒童受眾才載入，一般專案不套兒童規範。
- feat: `designing-ui`、`auditing-ui` 寫受眾無關的通用規範與清單（`auditing-ui/references/checklist.md`）。
- feat: 加 `package.json`（`pi.skills`）。
- `ui-ux-pro-max` 內容不變。

## [0.1.1] - 2026-10-01

- refactor: `ui-ux-pro-max` 的 CLI 工作流程（前置需求、使用流程、搜尋參考、範例、輸出格式、訣竅）移至 `skills/ui-ux-pro-max/references/cli-workflow.md`，SKILL.md 降至 300 行以內（內容不變）。

## [0.1.0] - 2026-10-01

- 首次建立 CHANGELOG；此前的變更未逐版記錄。
