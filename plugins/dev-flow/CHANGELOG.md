# Changelog

格式：每次改動 `skills/`、`agents/`、`references/` 時，於最上方新增版本條目並同步 bump 版號（規則見 `.claude/rules/version-consistency.md`）。

## [1.1.1] - 2026-11-03

- fix: 5 個 agent 不再自己 Glob 找附錄（plugin 在 CLI 快取裡，從專案根找不到），改由呼叫端在派工 prompt 帶附錄絕對路徑；沒給就照專案既有程式並在回報註明。

## [1.1.0] - 2026-11-03

- feat: 新增 5 個不綁技術的 agent——`architect`、`developer`、`reviewer`、`tester`、`debugger`，改寫自 backend-dotnet 的同名 agent；`reviewer`／`tester` 另吸收 frontend-vue 的 `code-reviewer`／`test-engineer`。先偵測技術棧並讀職責 plugin（backend、frontend 等）的附錄，沒有附錄就照專案既有程式。第③批隨 dev-flow 併入 lifecycle。
- feat: `release` 吸收 frontend-vue 的 `release-workflow`，加 `skills/release/references/rebase-sync.md`（發版前與上游同步）。

## [1.0.0] - 2026-11-03

- BREAKING: 12 個 skill 移到新 plugin workspace（user 層）：`commit`、`worktree`、`triage-branch-cleanup`、`submodule-relay`、`tmp-scratch`、`context-hygiene`、`agent-orchestration`、`dual-tool-mirror`、`convention-first`、`debugging`、`review`、`quality-check`。dev-flow 只留 `spec`、`feature`、`implement`、`work-on`、`release`。
- refactor: 剩下的 skill 叫用搬走的 skill 改寫成 `workspace:<skill>`，並註明沒裝 workspace 時的退路。

## [0.3.0] - 2026-11-03

- feat: `review` 審 PR 前先看狀態（closed／merged 不審）；新增「發現驗證與誤報排除」——排除既有問題、linter 會抓的、已靜音的、吹毛求疵，🚫／⚠️ 每條派獨立唯讀 subagent 驗證後才進報告。
- feat: `implement` 步驟 9 彙整分級後先套 `review` 的發現驗證，再委派修正。

## [0.2.2] - 2026-11-03

- docs: `agent-orchestration` 拿掉「同時已有 3 個活著的 worker 先問使用者」；派工數量不再設門檻。

## [0.2.1] - 2026-11-02

- docs: `convention-first`、`tmp-scratch` 的 description 拿掉角括號（Claude Code 清單會顯示成 `&lt;`）。

## [0.2.0] - 2026-10-22

- feat: 新增 `submodule-relay` skill——子模組 commit→push→上層 pointer bump 接力；`M` 方向判讀（index 落後才 bump、超前要 pull、未推遠端與分叉不動）；禁根目錄 `submodule update --recursive`；push 失敗不得接 bump；pull／rebase 後驗領先 commit 與 pointer。子模組清單一律從 `.gitmodules` 讀。
- feat: 新增 `tmp-scratch` skill——session scratchpad 與專案 `.tmp/<YYYYMMDD>-<slug>/` 兩層分工、禁裸檔、ASCII 命名、任務結束當輪清、被派出的 worker 不自刪。
- feat: 新增 `dual-tool-mirror` skill——`.claude/` 單一來源鏡像到 `.agents/skills`、`.codex/agents`、`.agents/rules`，Codex SessionStart 注入 rules；附 `sync-codex-mirror.mjs`、`codex-rules.mjs`（`--root`／`--no-user`）。
- feat: `commit` 加「多 agent 並行安全」——暫存複驗獨立一步、`git rm` 改 `rm`、共用分支禁 amend／`rebase -i`、別人有未推 commit 時改用 worktree、hook 擋下不自行繞過。
- feat: `quality-check` 加「commit 前驗證原則」——只跑專案自帶 script（從 README／CI 設定找）、輸出落檔、禁管線吞崩潰、只認 exit code。
- feat: `agent-orchestration` 加「派工判準」——自己做／subagent／獨立 worker 三分、平行看共用資源、該不該拆、派工 prompt 自足。
- docs: `context-hygiene` 新增 config-layering reference（現屬 workspace；設定落 user／專案／plugin 的判準、rules 只放紅線、權威只放一處）；`release` 的子模組 reference 改指向 `submodule-relay`。

## [0.1.1] - 2026-10-01

- refactor: `release` skill 的 Hotfix、子模組處理、版號疑難排解移至 `skills/release/references/`，SKILL.md 降至 300 行以內（內容不變）。

## [0.1.0] - 2026-10-01

- 首次建立 CHANGELOG；此前的變更未逐版記錄。
