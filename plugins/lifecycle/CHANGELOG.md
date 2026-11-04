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
- feat: `implement` 依改動大小縮減派工——單一 task、影響檔案少時規劃由主 session 做、審查只派一個 reviewer；使用者可要求走完整流程。
- feat: `release`（含 hotfix）新增本機模式：無 remote／無 CI 時跳過 push 類關卡、手動建 annotated tag，版號檔不綁 `package.json`。
- feat: 無畫面功能（純後端、CLI、批次）不產 FFS，FRD 分流時確認並在 `analysis/_context.yml` 記 `ffs: skipped`；下游 spec-check、spec-chain 認得此值。
- fix: lean 時探索摘要與規格同目錄（`<spec.dir>/<feature>_探索摘要.md`），`spec` 寫明去哪找；lean 不問模組，full 新專案無既有模組時直接請使用者命名。
- fix: `implement` 未提交變更只有規格／探索摘要時，先開功能分支並 commit 成第一個 commit，不再停下；審查範圍含未提交變更；spec-check 回 ⚠️ 一律修正後才開發；G6 規格回填不算修正 commit。
- fix: `spec-check` verify 接受功能目錄、補 FFS 與實際檔名判斷、lite 鏈改比 FRD↔BFS、8.8 只擋同視角重畫流程圖、規定驗證報告路徑、無 DB 工具時標「未查證」不擋。
- fix: `ticket-create` 派工帶專案根、寫明父子回填與相依落地方式；規格已存在時 PM 子票預設 `in-review`；設定缺漏改由 ticket-ops 問並寫入。
- fix: CR 範本「Linear Ticket」改「票號」；移除不存在的 `linear-ticket-defaults.md` 引用；`sdlc-docs-path` 改讀 `spec.dir`，`sdlc-*` 專案鍵改 `lifecycle-*`（舊名仍認）。
- feat: `reviewer` agent 加 Write 工具，只把審查報告寫到呼叫端指定的檔，回傳結論行與路徑（主 session 不再讀整份報告）。
