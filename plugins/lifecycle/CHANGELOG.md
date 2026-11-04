# Changelog

格式：每次改動 `skills/`、`agents/`、`references/`、`templates/` 時，於最上方新增版本條目並同步 bump 版號（規則見 `.claude/rules/version-consistency.md`）。

## [1.0.0] - 2026-11-04

- BREAKING: 由 `sa-flow`（4.1.2）、`delivery-flow`（0.8.2）、`dev-flow`（1.1.1）合併而成；命名空間一律改為 `lifecycle:`。舊版歷史見 git log 中三個舊 plugin 的 CHANGELOG。
- BREAKING: 專案設定檔改名 `.plugharbor/delivery-flow.yml` → `.plugharbor/lifecycle.yml`（鍵不變）；只有舊檔時 `config.py` 退出碼 2 並提示改名。
- feat: 設定新鍵 `scale`（`lean`｜`full`，預設 `lean`）與 `spec.dir`（預設 `docs/specs`）。
- refactor: 三個 plugin 的共用素材（harness-terms、dispatch-conventions、shared-preludes）併成一份。
