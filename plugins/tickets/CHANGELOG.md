# Changelog

格式：每次改動 `skills/`、`agents/`、`references/`、`templates/` 時，於最上方新增版本條目並同步 bump 版號（規則見 `.claude/rules/version-consistency.md`）。

## [1.3.4] - 2026-11-23

起因：docs/retrospective/20261123-implement-bypass/report.md（R2、R3）——feature.md 票號先寫後開撞號 4 次；`workspace 的 review` 移除。
- fix：同步 lifecycle 4.3.2 的 `references/feature-checklist.md` 副本（新增項目與節先 create，行尾只寫回傳號碼）。
- docs：`references/pipeline.md` 的 workspace 說明移除 review。

## [1.3.3] - 2026-11-21

起因：Formwright 使用者 2026-11-21 裁決 roadmap 段表已完成的段狀態改以「✅ 」開頭（formwright bf13dd13），`feature_checklist.py --check` 因此把 5 個已上線段判成與清單不同步。
- fix：同步 lifecycle 4.3.1 的 `feature_checklist.py`、測試與 `feature-checklist.md` 副本（狀態開頭可有 ✅）。

## [1.3.2] - 2026-11-20

起因：plugharbor#59——Formwright 一次搬 58 張待辦成票，ticket-create 每張兩次互動確認，無人值守時無法照流程，只能繞過它直接跑 gh。
- feat：`ticket-create` 新增「批次模式」：清單輸入、整批共用階段／類型／labels、一次總表確認；無人值守（使用者不在且呼叫端明示不問）取推薦值直接建，總表落檔（使用者 2026-11-20 裁決採用）。

起因：plugharbor#61——排程用 `claude -p` 跑 `ticket-report daily`，subagent 寫 `report-{日期}.md` 被 Claude Code 拒絕（2026-11-20 本機重現：同一 subagent、同一權限模式，`report-*.md` 被拒、`daily-*.md` 寫入成功），主報表沒產出卻以為完成。
- fix：主報表檔名 `report-{日期}.md` 改 `daily-{日期}.md`、`report-{週會日}.md` 改 `weekly-{週會日}.md`（檔名改動，下游若依檔名讀取要跟著改；使用者 2026-11-20 裁決採用）。
- docs：錯誤處理表加「寫檔被拒」一列，要求明講未產出，不當成功收尾。

## [1.3.1] - 2026-11-20

起因：plugharbor#60——Formwright 的外洩清單因專案公開而放在 repo 外，以環境變數 `LEAK_DENYLIST` 指過去；`ticket_backend.py leak` 不讀它，退出碼 5，SKILL 規則要求公開 repo 停下，等於開不了票。
- fix：`ticket-ops` 的 `load_denylist` 先讀 `LEAK_DENYLIST` 指的檔（不存在才退回 repo 根目錄與主 checkout），附 3 個測試；SKILL.md 退出碼 5 的說明同步。

## [1.3.0] - 2026-11-19

起因：使用者 2026-11-19 回報 superpowers 腦力激盪、寫計畫時向使用者丟一長串設計題，全都不經 domain 顧問；顧問桌只在 `spec` 蒐證後開，介入太晚，使用者要求設計題先過顧問，顧問決定不了的才問。
- feat：同步 lifecycle 4.3.0 的副本：`references/consultant-desk.md`、`shared-preludes.md`、`config.md`，內容是顧問的設計提問分流（`mode: triage`）與新設定鍵 `advisor.escalate`。

## [1.2.1] - 2026-11-18

起因：Windows 桌機的 Herdr.app 終端跑 `mux.py env` 直接丟 `AttributeError: module 'socket' has no attribute 'AF_UNIX'`（`core_running()`，2026-11-18 重現），Windows 上所有經 mux.py 的派工都不能用。另外 `spawn` 用 `env -u …` 當 argv 前綴（Windows 沒有 `env`），`app_layout.py` import `fcntl`（Windows 沒有）。
- fix：`scripts/mux.py`、`scripts/app_layout.py` 同步 toolkit 0.28.2 的 Windows 支援（副本）。

## [1.2.0] - 2026-11-17

起因：使用者 2026-11-17 轉用 Herdr.app，派工流程在 app 內無法開 worker。

- 同上：`references/advisor-discussion.md`、`consultant-desk.md`、`shared-preludes.md`、`scripts/advisor_last_reply.py` 從 lifecycle 4.2.0 的同名檔依對照表同步（只差 agent 名稱）；新增 `scripts/mux.py`、`scripts/app_layout.py`、`scripts/herdr_layout.py`（版面腳本，與 toolkit `agent-dispatch` 正本位元組相同；顧問 pane 排進主 session 旁；版面不依賴 toolkit，hc 下讀顧問 transcript 需 toolkit 的 SessionStart hook，沒有就改走 subagent 模式）。
- 同上（最終審查）：同步 lifecycle 4.2.0 的 `advisor-discussion.md` 修正（`session` 為 null 最多重試 3 次，缺 hook 改走 subagent 模式）與 `mux.py`、`app_layout.py` 副本更新。
- fix（實機驗收）：`app_layout.py` 副本同步（見 toolkit 0.25.0：spawn 後立刻放置會回 `no running terminal`，改為重試）。
- fix（實機驗收）：`mux.py` 副本同步（見 toolkit 0.25.0：hc send exit 9 改回 blocked）。

## [1.1.0] - 2026-11-16

起因：xiaoxiao 的 34 張票在 D1 補開時誤掛到 plugharbor 的看板 #1（違反票務雙軌設計「每個 repo 各建看板」），`reconcile.py` 只收本 repo 的票，兩邊對帳都是差異 0，沒人發現；之後用票號找看板項目時撞到同號的兩張票才暴露。

- `ticket-ops/scripts/reconcile.py`：看板上有別的 repo 的 Issue 時，在報告加一行 ⚠️ 列出各 repo 張數（不計入差異、不影響退出碼）；新增純函式 `other_repo_issues()` 與測試。

## [1.0.1] - 2026-11-16

起因：lifecycle 4.1.0 把設計文件改成新章節格式（設計見 `docs/superpowers/specs/2026-11-15-lifecycle-split-design.md`，第三批），本 plugin 的共用 references 副本跟著改讀新章節。

**改動**

- `references/` 共用副本（config、shared-preludes、shared-preludes-details、analysis-rigor、consultant-desk、legacy-parity）改讀新章節，舊章節以「（舊範本 §n）」括號別名保留。
- `references/pipeline.md`、`skills/ticket-reply/SKILL.md`：implement 步驟改稱實作前檢查；CR 流程與 TD 留置的章節對照改指新章節。

## [1.0.0] - 2026-11-15

起因：lifecycle 一個 plugin 管太多事（規格、票務、勘察、手冊、發版），要用票務的人得裝整包。設計見 `docs/superpowers/specs/2026-11-15-lifecycle-split-design.md`，第二批「拆 plugin」，tickets 是第一個拆出來的。

- 自 lifecycle 3.0.0 搬入：skills `ticket-ops`、`ticket-create`、`ticket-reply`、`ticket-report`、`triage`；agents `report-writer`、`silent-failure-hunter`；references `pipeline.md`、`report-calendar.md`。叫用名由 `lifecycle:<名稱>` 改為 `tickets:<名稱>`。
- 能單獨安裝，所以帶一份共用 references／scripts 副本（`harness-terms`、`config`、`shared-preludes*`、`consultant-desk` 等核心包，加 `feature-checklist.md`、`feature_checklist.py`）；canonical 在 lifecycle，漂移由 validate 的共用副本檢查擋。
- `scout` 的副本改名 `tickets-scout`（`<plugin>-<原名>` 規則），避免與 lifecycle 的 `lifecycle:scout` 同名混淆；`triage` 帶自己的 second-opinion 副本；`references/pipeline.md` 內的 `scout` 改為 `tickets-scout`。
- 新增 `scripts/test_skill_contracts.py`（自 lifecycle 搬來票務相關的接點契約，另驗 `reconcile.py` 找得到清單解析器）。
