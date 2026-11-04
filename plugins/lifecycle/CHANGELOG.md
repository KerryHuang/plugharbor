# Changelog

格式：每次改動 `skills/`、`agents/`、`references/`、`templates/` 時，於最上方新增版本條目並同步 bump 版號（規則見 `.claude/rules/version-consistency.md`）。

## [1.0.0] - 2026-11-04

- BREAKING: 由 `sa-flow`（4.1.2）、`delivery-flow`（0.8.2）、`dev-flow`（1.1.1）合併而成；命名空間一律改為 `lifecycle:`。舊版歷史見 git log 中三個舊 plugin 的 CHANGELOG。
- BREAKING: 專案設定檔改名 `.plugharbor/delivery-flow.yml` → `.plugharbor/lifecycle.yml`（鍵不變）；只有舊檔時 `config.py` 退出碼 2 並提示改名。
- feat: 設定新鍵 `scale`（`lean`｜`full`，預設 `lean`）與 `spec.dir`（預設 `docs/specs`）。
- refactor: 三個 plugin 的共用素材（harness-terms、dispatch-conventions、shared-preludes）併成一份。
- BREAKING: 規格類合併——`requirement`／`system-analysis`／`specify-backend`／`specify-frontend`／`spec-docs` 併入 `spec`（`--stage frd|sad|bfs|ffs|index`，沒給就看 `scale`：lean 產一份 `<spec.dir>/<feature>.md`）；`verifying-specs`／`dev-readiness`／`sample-verify` 併入 `spec-check`（verify 預設、`--readiness`、`--sample`）；`spec-chain` 改手動。
- BREAKING: 票務類改名合併——`linear-create` → `ticket-create`、`linear-reply` → `ticket-reply`、`linear-triage`＋`issue-triage` → `triage`、`ticket-daily-report`＋`ticket-weekly-report` → `ticket-report`（`daily`／`weekly`，手動）；全部經 `ticket-ops` 的抽象階段，不寫死 Linear，Linear 專屬欄位（team、label、estimate、SLA）移除。
- BREAKING: 開發交付類——`feature`、`work-on` 併入 `implement`（ledger 落 `.tmp/implement/`、每 task 全新 subagent、收尾關卡 G1–G7）；`release` 改關卡 R0–R8 並記「已檢查 SHA」，merge 前比對。
- BREAKING: `qa-sweep` 併入 `qa-verify --sweep`；移除 `foxpro-analyzer` 與 superpowers 整合設計文件；FoxPro、OpenSpec、特定技術的預設情境改為不指定技術，`chain_origin: foxpro` 改為 `legacy`。
- BREAKING: 沒設文件路徑時 `{docs-root}` 預設從 `docs/` 改為 `spec.dir`（預設 `docs/specs`）；後端驗證帳密改讀 `.plugharbor/qa.local.md`。
- feat: `consolidate-docs`、`write-doc`、`dev-feedback`、`operation-manual`、`interview-prep`、`plugin-healthcheck`、`spec-chain`、`ticket-report` 改為手動（`disable-model-invocation`）；`dev-feedback` 改輸出報告檔、不再 `--apply`，並相容舊票源 flag `sa-flow:linear-create`。
- refactor: 流程不再引用 Superpowers（裝 lifecycle 的專案會停用它）；`pipeline.md` 改寫為 lifecycle 動線。
