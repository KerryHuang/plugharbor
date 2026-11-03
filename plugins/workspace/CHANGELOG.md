# Changelog

格式：每次改動 `skills/`、`agents/`、`references/` 時，於最上方新增版本條目並同步 bump 版號（規則見 `.claude/rules/version-consistency.md`）。

## [1.0.0] - 2026-11-03

- feat: 新 plugin，自 dev-flow 0.3.0 拆出 12 個與規格流程無關、任何專案都用得到的 skill：`commit`、`worktree`、`triage-branch-cleanup`、`submodule-relay`、`tmp-scratch`、`context-hygiene`、`agent-orchestration`、`dual-tool-mirror`、`convention-first`、`debugging`、`review`、`quality-check`。內容不變；叫用 dev-flow 的地方（`quality-check` 銜接 `work-on`、`submodule-relay` 銜接 `release`）改寫成 `dev-flow:` 並標可選。
- feat: 加 `package.json`（`pi.skills`），pi 也載入得到。
