# Changelog

格式：每次改動 `skills/`、`agents/`、`references/` 時，於最上方新增版本條目並同步 bump 版號（規則見 `.claude/rules/version-consistency.md`）。

## [0.2.0] - 2026-11-03

- feat: `review-remote` 選定 MR/PR 後先看狀態；新增「誤報排除與驗證」（每條要求修改的發現派獨立唯讀 subagent 驗證）與留言規則（每問題一則、完整 head SHA 連結（附 GitHub／GitLab 格式與取法）、只有能完整修好的小改動才附 suggestion）。

## [0.1.1] - 2026-11-02

- docs: `vue-composables` 的 description 拿掉角括號（Claude Code 清單會顯示成 `&gt;`）。

## [0.1.0] - 2026-10-01

- 首次建立 CHANGELOG；此前的變更未逐版記錄。
