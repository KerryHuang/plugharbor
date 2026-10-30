# Changelog

格式：每次改動 `skills/`、`agents/`、`references/` 時，於最上方新增版本條目並同步 bump 版號（規則見 `.claude/rules/version-consistency.md`）。

## [0.2.0] - 2026-10-22

- feat: 新增 `submodule-relay` skill——子模組 commit→push→上層 pointer bump 接力；`M` 方向判讀（index 落後才 bump、超前要 pull、未推遠端與分叉不動）；禁根目錄 `submodule update --recursive`；push 失敗不得接 bump；pull／rebase 後驗領先 commit 與 pointer。子模組清單一律從 `.gitmodules` 讀。
- feat: 新增 `tmp-scratch` skill——session scratchpad 與專案 `.tmp/<YYYYMMDD>-<slug>/` 兩層分工、禁裸檔、ASCII 命名、任務結束當輪清、被派出的 worker 不自刪。
- feat: 新增 `dual-tool-mirror` skill——`.claude/` 單一來源鏡像到 `.agents/skills`、`.codex/agents`、`.agents/rules`，Codex SessionStart 注入 rules；附 `sync-codex-mirror.mjs`、`codex-rules.mjs`（`--root`／`--no-user`）。
- feat: `commit` 加「多 agent 並行安全」——暫存複驗獨立一步、`git rm` 改 `rm`、共用分支禁 amend／`rebase -i`、別人有未推 commit 時改用 worktree、hook 擋下不自行繞過。
- feat: `quality-check` 加「commit 前驗證原則」——只跑專案自帶 script（從 README／CI 設定找）、輸出落檔、禁管線吞崩潰、只認 exit code。
- feat: `agent-orchestration` 加「派工判準」——自己做／subagent／獨立 worker 三分、平行看共用資源、該不該拆、派工 prompt 自足。
- docs: `context-hygiene` 新增 `skills/context-hygiene/references/config-layering.md`（設定落 user／專案／plugin 的判準、rules 只放紅線、權威只放一處）；`release` 的子模組 reference 改指向 `submodule-relay`。

## [0.1.1] - 2026-10-01

- refactor: `release` skill 的 Hotfix、子模組處理、版號疑難排解移至 `skills/release/references/`，SKILL.md 降至 300 行以內（內容不變）。

## [0.1.0] - 2026-10-01

- 首次建立 CHANGELOG；此前的變更未逐版記錄。
