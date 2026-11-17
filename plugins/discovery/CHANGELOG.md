# Changelog

格式：每次改動 `skills/`、`agents/`、`references/`、`templates/` 時，於最上方新增版本條目並同步 bump 版號（規則見 `.claude/rules/version-consistency.md`）。

## [1.1.0] - 2026-11-17

起因：使用者 2026-11-17 轉用 Herdr.app，派工流程在 app 內無法開 worker。

- 同上：`references/advisor-discussion.md`、`consultant-desk.md`、`shared-preludes.md`、`scripts/advisor_last_reply.py` 從 lifecycle 4.2.0 的同名檔依對照表同步（只差 agent 名稱）；新增 `scripts/mux.py`、`scripts/app_layout.py`、`scripts/herdr_layout.py`（版面腳本，與 toolkit `agent-dispatch` 正本位元組相同；顧問 pane 排進主 session 旁；版面不依賴 toolkit，hc 下讀顧問 transcript 需 toolkit 的 SessionStart hook，沒有就改走 subagent 模式）。
- 同上（最終審查）：同步 lifecycle 4.2.0 的 `advisor-discussion.md` 修正（`session` 為 null 最多重試 3 次，缺 hook 改走 subagent 模式）與 `mux.py`、`app_layout.py` 副本更新。

## [1.0.1] - 2026-11-16

起因：lifecycle 4.1.0 把設計文件改成新章節格式（設計見 `docs/superpowers/specs/2026-11-15-lifecycle-split-design.md`，第三批），本 plugin 的共用 references 副本跟著改讀新章節。

**改動**

- `references/` 共用副本（config、shared-preludes、shared-preludes-details、analysis-rigor、consultant-desk、legacy-parity）改讀新章節，舊章節以「（舊範本 §n）」括號別名保留。

## [1.0.0] - 2026-11-15

起因：lifecycle 22 個 skill 兩週內實際只用到 7 個；只想要會議記錄的人得裝整包。設計見 `docs/superpowers/specs/2026-11-15-lifecycle-split-design.md`，第二批「拆 plugin」，discovery 是第二個拆出來的（第一個是 tickets）。

- 自 lifecycle 3.0.0 搬入：skills `meeting-minutes`、`interview-prep`、`survey-existing-system`、`prototype-html`；`templates/` 三檔（`interview-outline.md`、`meeting-minutes.md`、`requirement-synthesis.md`）。叫用名由 `lifecycle:<名稱>` 改為 `discovery:<名稱>`。
- 能單獨安裝，所以帶一份共用 references／scripts 副本（`harness-terms`、`config`、`shared-preludes*`、`consultant-desk` 等核心包）；canonical 在 lifecycle，漂移由 validate 的共用副本檢查擋。`meeting-minutes` 的 `second-opinion.md` 以 discovery 為 canonical，tickets 的 `triage` 帶副本。
- 四個 agent 以副本帶入並改名（`<plugin>-<原名>` 規則）：`discovery-scout`（`scout`）、`discovery-domain-advisor`（`domain-advisor`）、`discovery-report-writer`（tickets 的 `report-writer`）、`discovery-silent-failure-hunter`（tickets 的 `silent-failure-hunter`）；skill 內的派發名跟著改。
- 新增 `scripts/test_skill_contracts.py`（自 lifecycle 搬來 `prototype-html`、`interview-prep` 相關的契約）。
