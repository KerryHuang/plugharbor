# Changelog

格式：每次改動 `skills/`、`agents/`、`references/` 時，於最上方新增版本條目並同步 bump 版號（規則見 `.claude/rules/version-consistency.md`）。

## [1.5.1] - 2026-11-10

- docs: 4 個 skill 的 frontmatter 加 `triggers` 欄位（單行 JSON 陣列，不進 skill 清單、description 不變）。這個 plugin 被明確停用時，toolkit 的 `disabled-skills.py` 會拿它比對使用者訊息，提示這個 skill 存在。起因同 toolkit 0.18.0：別的專案跑 /doctor 關掉少用的 plugin 後，之後要用時找不到。

## [1.5.0] - 2026-11-09

- feat: 新增 `unattended`（無人值守模式）。使用者叫用或說要離開時，主控照路線連續推進工作單元，直到使用者回來（送出新訊息）為止：開場讀專案的 `.plugharbor/unattended.md`（範本 `skills/unattended/references/project-config.md`，沒有就趁使用者還在先問），裁決帳本分開記使用者與主控的決定，設計單元的使用者行為類決定標待確認，只在停下條件停，回來時交 `return-report.md`。跨家族審查有 `toolkit:agent-dispatch` 才用，沒有就退回同家新 context。起因是一個專案的專案層夜間 skill 實跑一次判斷點皆正確，通用流程與專案細節已分開，其他專案也需要；s2e 設計因方向在審查中翻盤多審 3 輪，促成「行為類先標待確認」。常駐 context 多一行 description，換掉該專案層 skill 的 description（隨後拆除）。

## [1.4.1] - 2026-11-09

- fix: agent-orchestration 的共用資源清單補上「同時跑會互搶 CPU 的測試」，與 user 層 `dispatch.md` 同步；`dispatch.md` 同時加上「長工作丟背景前先做或派不衝突的待辦，沒有才等、不輪詢」，並精簡其他措辭使總長不增。起因是一個專案的主控 session 把全套測試（約 10 分鐘）、部署（約 5 分鐘）、跨家族審查（20～40 分鐘）丟到背景後就停下來等，路線圖上可平行的工作沒做；兩支吃 CPU 的測試同時跑也曾讓測試逾時。

## [1.4.0] - 2026-11-09

- refactor: 方法類交給 superpowers，debugging 與 agent-orchestration 瘦身。debugging 開頭寫明裝了 superpowers 照 `systematic-debugging`／`test-driven-development`，本 skill 只留專案指令、症狀對照根因、改在正確的層、規格轉測試案例與輸出格式，一般方法敘述縮成幾行退路迴圈；`tdd-cycle.md` 的 Green／Refactor 說明精簡。agent-orchestration §6 由「專案資源優先」改成新分工（方法類 superpowers 優先，自家管 chain、output file 交棒、清理，herdr 與跨 CLI 用 `toolkit:agent-dispatch`），§0 保留。debugging、agent-orchestration、review 的 description 收掉與 superpowers 撞名的觸發詞（「systematic debugging」「TDD」「debug」「code review」「派 subagent」「orchestration」等），都比原本短。worktree、quality-check 檢查後不動。起因是近 14 天 workspace 的 debugging、agent-orchestration 叫用 0 次，方法類被 superpowers 接走，description 撞名讓兩邊搶觸發。

## [1.3.2] - 2026-11-09

- fix: commit、quality-check、tmp-scratch 的 description 加上主控自己動手時的觸發（自己要下 git commit、合併或 commit 前要跑 gate、要寫一次性腳本或開 `.tmp`），並刪掉重複的中英觸發詞，三個都比原本短。起因是一個 session 叫了 122 次 Skill，這三個一次都沒觸發：主控自己下了 76 次 commit、重複手寫 gate 指令 21 次，因為原本只寫使用者會講的話。

## [1.3.1] - 2026-11-09

- docs(agent-orchestration): 平行判準的共用資源補上「同一個 worktree」與「build／測試產物」。起因是同一個 worktree 裡跑 gate 測試與做修正的 subagent 同時在跑，互相干擾。

## [1.3.0] - 2026-11-05

- feat: `review` 新增「專案規範合規」審查面向：只比對路徑涵蓋變更檔的 `CLAUDE.md`／`AGENTS.md`，違規須引用規則原文（`skills/review/references/evidence.md` 第 7 節）。
- feat: `review` 審遠端 PR／MR 前先看留言，已有先前審查就問要不要重審；使用者要求留言但無發現時也留摘要（`skills/review/references/review-remote.md`）。
- 做法借鑒自 anthropics/claude-plugins-official 的 `plugins/code-review`（Apache-2.0），內容重新撰寫。

## [1.2.0] - 2026-11-04

- feat: `review` 新增 `skills/review/references/evidence.md`——預設只報告、變更檔歸屬表、「查無」前先證明查得到、被削弱的測試／拉長的 timeout／新 suppression 要列出、新套件查 registry；只排除改動前就存在的 suppression。
- fix: `quality-check` 的可選銜接改指 `lifecycle:implement`。

## [1.1.2] - 2026-11-04

- fix: 可選叫用與退路改指向 `lifecycle`（sa-flow／delivery-flow／dev-flow 已合併為 lifecycle）。

## [1.1.1] - 2026-11-03

- fix: `debugging` 的 tdd-cycle 角色分工補沒裝 dev-flow 時的退路，並要求把職責 plugin 的附錄路徑帶進派工 prompt。

## [1.1.0] - 2026-11-03

- feat: 新 skill `cross-platform`（跨平台路徑、換行、大小寫、shell 差異），改寫自 desktop-avalonia 的同名 skill，不再綁 Avalonia。
- feat: `debugging` 吸收 backend-dotnet 的 `tdd-cycle`（Red-Green-Refactor 通用做法放 `skills/debugging/references/tdd-cycle.md`，.NET 指令移到 backend 的附錄）。
- feat: `review` 吸收 frontend-vue 的 `review-remote`（審查遠端 PR／MR，`skills/review/references/review-remote.md`）。

## [1.0.1] - 2026-11-03

- fix: `dual-tool-mirror` 同步時略過含 `.plugharbor-root` 的目錄（plugharbor install-project 複製模式的 skill 複本），不再把它們當成多餘副本刪掉；加 node 測試。

## [1.0.0] - 2026-11-03

- feat: 新 plugin，自 dev-flow 0.3.0 拆出 12 個與規格流程無關、任何專案都用得到的 skill：`commit`、`worktree`、`triage-branch-cleanup`、`submodule-relay`、`tmp-scratch`、`context-hygiene`、`agent-orchestration`、`dual-tool-mirror`、`convention-first`、`debugging`、`review`、`quality-check`。內容不變；叫用 dev-flow 的地方（`quality-check` 銜接 `work-on`、`submodule-relay` 銜接 `release`）改寫成 `dev-flow:` 並標可選。
- feat: 加 `package.json`（`pi.skills`），pi 也載入得到。
