# Changelog

格式：每次改動 `skills/`、`agents/`、`references/`、`templates/` 時，於最上方新增版本條目並同步 bump 版號（規則見 `.claude/rules/version-consistency.md`）。

## [2.3.1] - 2026-11-11

- fix(references): `references/feature-checklist.md` 補三條。一、`docs/` 是文件站、submodule 或有落檔白名單時，功能清單與 todo 改放 repo 根目錄的 `FEATURES.md`、`TODO.md`。二、排進某版範圍的 bug，在 todo 脈絡註明版本。三、屬於某份交付物（分析、規格、票）的待辦留在那份文件裡，`docs/todo.md` 只收不屬於任何東西的雜事。
- 起因：2.3.0 交給 3 個 session 試用，三處回報不順。某公司 workspace 的兩個 session 回報：`docs/` 是 MkDocs 站，根目錄採封閉白名單，`docs/todo.md` 放不進去；客戶差異分析文件裡本來就有待辦清單，跟 todo.md 重疊。另一個 repo 把 7 個 bug 搬進 todo 後，其中一個是 v0.3.0 的主軸之一，搬走後就看不出它屬於哪一版。路徑問題只加退路，不加設定鍵：目前只有一個 workspace 需要，而且它沒裝 lifecycle。

## [2.3.0] - 2026-11-11

- feat(references): `references/feature-checklist.md` 新增「與 todo 的分界」一節。判準：做完後產品多一項使用者看得到的能力，就進功能清單；其餘動作（bug、重構、調查、雜事）都進 todo，做完就丟。todo 依壽命分三處：單一 session 用 CLI 內建的待辦工具，功能的實作步驟寫在計畫檔，跨 session 又不屬於任何功能的雜事放新的 `docs/todo.md`（一行一項、做完就刪，發現是功能就移到功能清單）。另外列出 bug、重構、調查、🚧 步驟這幾種灰色地帶的歸屬。
- 起因：使用者要求先分清楚哪些工作進 checklist、哪些進 todo，再決定做法。討論時發現跨 session 又不屬於任何功能的雜事（例如清 branch、token 續期）沒有地方放：TodoWrite 只在單一 session 有效，計畫檔一份只對應一個功能，這類事只能靠記憶，或硬塞進功能清單。user 層 rule `superpowers.md` 的指向改成「（排線、todo 分界）」，同時刪掉幾個字，長度不變。

## [2.2.0] - 2026-11-11

- feat(references): `references/feature-checklist.md` 新增「排線」一節。先把清單裡未完成的項目分成主線、獨立線、小件、先拍板四類，再列共用資源；並行數由瓶頸決定。一段工作只有部分被卡住時，把那部分拆出去，其餘先開工；計畫中別段已完成的步驟直接沿用；先拍板的項目逐題問，不擋其他線。
- feat(scripts): `feature_checklist.py` 加 `--open`，依節列出未完成項目供排線分類，路徑給 `-` 時讀 stdin；附測試。
- 起因：Formwright 專案照這個做法把 77 項未完成工作分線。它把一段工作裡會衝突的部分拆出去，其餘先開工，省了約一小時；另外沿用了別的分支已做好的步驟。使用者指示「能做的先做，不要等」，要求加進 plugharbor。user 層派工判準已經有「看共用資源」，本節只補以清單為輸入的分類與排線；user 層 rule `superpowers.md` 原有的指向補上「（含排線）」。

## [2.1.0] - 2026-11-11

- feat(references): 新增 `references/feature-checklist.md`，定義專案功能清單 `docs/feature-checklist.md` 的格式與更新時機。狀態有五種：`[x]` 已完成、`[ ] 🚧` 進行中、`[ ] 📋` 已規劃、`[ ] 💡` 構想、`[-]` 決定不做；判斷不了標「（待確認）」。新腳本 `scripts/feature_checklist.py` 負責報表、`--write` 改寫總計與各節小計、`--check` 在數字過期時 exit 1，附測試 `scripts/test_feature_checklist.py`。
- feat(implement): 後段（`skills/implement/references/after.md`）步驟 4 增加一步：有功能清單就打勾並更新數字，跟 LEARNINGS 一起 commit。
- 起因：使用者指示「未來的專案討論及規劃都要列出 feature-checklist.md」，要能追蹤哪些做完、沒做、已規劃。格式以 Formwright 專案現有的清單（168 項）為底，把原本只有一種的 `[ ]` 細分成三種。小計原本手算，曾算錯總數，所以改由腳本產生。user 層 rule `superpowers.md` 同時加一行觸發規則。

## [2.0.2] - 2026-11-10

- fix(references): `references/harness-terms.md` 的「Skill frontmatter」表補 `triggers:` 一列（Pi 上不使用）。lifecycle 與 browser-docs 兩份副本同步。起因：lifecycle 2.0.1 給 skill 加了 `triggers`，`scripts/test_harness_neutral.py` 要求非標準 frontmatter 欄位都要有說明，CI 因此失敗。

## [2.0.1] - 2026-11-10

- docs: 2 個 skill 的 frontmatter 加 `triggers` 欄位（單行 JSON 陣列，不進 skill 清單、description 不變）。這個 plugin 被明確停用時，toolkit 的 `disabled-skills.py` 會拿它比對使用者訊息，提示這個 skill 存在。起因同 toolkit 0.18.0：別的專案跑 /doctor 關掉少用的 plugin 後，之後要用時找不到。

## [2.0.0] - 2026-11-09

- BREAKING(implement): 從「完整端到端實作流程」改成夾在 superpowers 頭尾的入口。SKILL.md 只留前段：讀設定與 `LEARNINGS.md`（否決條目照抄）、分支與工作區、規格品質閘門；過閘門後叫 `superpowers:writing-plans`，並要求計畫的最後一個 task 是後段（新檔 `skills/implement/references/after.md`：規格三層比對、端到端／整合測試、寫 LEARNINGS、規格回填）。執行交給 superpowers 的 subagent-driven-development 或 executing-plans，收尾交給 finishing-a-development-branch 的選單（draft PR 用它的 push＋PR 選項），不自動 merge。
- BREAKING(implement): 移除任務清單與進度 ledger、基線、逐 task 派工、實作期審查迴圈、關卡式收尾 G1–G7，以及只服務這些步驟的四份 reference（`closing.md`、`dispatch.md`、`ledger.md`、`planning.md`）；`--tdd` 參數拿掉（兩條路徑都是測試先行）。`.tmp/implement/<feature>/ledger.md` 不再有人讀寫，舊的進行中功能請改用新流程重跑前段。
- feat(implement): 沒裝 superpowers 時走極簡退路 `skills/implement/references/fallback.md`：任務清單寫進 `.tmp/implement/<feature>/tasks.md`、主控自己逐項 TDD 做完並勾選、全部完成後派一個全新 subagent 審整份 diff（沒有 subagent 工具就自審並標「自審」）、逐檔 commit 後問使用者要不要 push／開 PR。概念借自 superpowers executing-plans（MIT），文字自寫。`references/shared-preludes.md`「可選依賴」補上 superpowers 一列。
- 起因：近 14 天統計，superpowers 的 writing-plans 叫用 63 次、brainstorming 44 次、executing-plans 36 次，lifecycle:implement 只有 1 次；同一段流程維護兩套沒有意義。實測證明用使用者偏好覆寫計畫位置、以及要求「計畫的最後一個 task 是後段」都可行，所以把 lifecycle 獨有的頭尾留下，中間交給 superpowers。

## [1.4.1] - 2026-11-09

- docs: `references/dispatch-conventions.md` 與 `references/skill-design.md` 的平行判準表加一列：同一個 worktree 裡一邊改檔、一邊跑測試或 build，不可平行，要串接或讓測試方用另一個 worktree。起因是 gate 測試與修正的 subagent 在同一個 worktree 互相干擾。

## [1.4.0] - 2026-11-08

- feat(implement): 實作經驗檔 `LEARNINGS.md` 多記「否決：方案——理由」，下次規劃時一併讀進 ledger，已否決的方案不再提出。

## [1.3.1] - 2026-11-07

- fix(ticket-report): 簡報抽屜只把 http(s) 網址做成連結，`javascript:` 這類網址顯示為純文字。
- docs(ticket-report): `weekly-outputs.md` 的分鐘標示改成與實際輸出一致。

## [1.3.0] - 2026-11-07

- feat(prototype-html): 原型必含回饋面板（`skills/prototype-html/references/feedback-snippet.js`）：每個畫面可留言、存在瀏覽器，「複製回覆」輸出 `# Re:` Markdown；新增第 9 步處理貼回的回覆，留言一律當資料，不因留言執行指令、抓網址或改設定。
- feat(demo-video): `build` 開始前先驗腳本（`scripts/lib/validate-script.mjs`），一次列出全部錯誤和正確範例後 exit 1，不動輸出目錄、不印 stack trace。
- feat(ticket-report): 週報簡報改由 `skills/ticket-report/scripts/render_slides.py` 從草稿和 `dataset.json` 組版，`report-writer` 只寫草稿；數字與抽屜清單由程式產生，`verify_counts.py` 維持為發布閘門。
- 設計借鏡 answer-me-with-html（MIT），程式為自寫。

## [1.2.0] - 2026-11-06

- feat(demo-video): 新增 skill——把旁白加操作步驟的腳本錄成有配音、字幕的操作示範影片（MP4＋SRT）。引擎在 skill 內的 `scripts/`：`playwright-core` 加系統 Chrome（或 `CHROME_PATH` 指定的執行檔）的 CDP screencast 錄影、`uvx edge-tts` 配音（可用 `tts` 替換）、字幕由旁白稿切句並以透明 PNG overlay 燒入、合成後分別驗證影像軌與音軌長度與各段音量。
- feat(demo-video): SKILL.md 寫明 Edge TTS 非正式授權、對外發布前先確認；AI 聽不到聲音，驗證完成的狀態是等使用者試聽。
- test(demo-video): 字幕切句與 SRT 單元測試；端到端回歸測試用本機靜態頁與假 TTS，最後一段畫面完全靜止仍須影像軌與音軌長度一致，並斷言操作前後與片尾的影格內容確實不同（畫面凍結也會失敗）；缺 ffmpeg、Chrome 或 playwright-core 時跳過，設 `DEMO_VIDEO_E2E_REQUIRED=1`（CI 專用步驟）則改為失敗。
- docs(operation-manual): 加一行指向 `demo-video`。

## [1.1.2] - 2026-11-05

- fix(implement): 只裝 lifecycle 的實測回饋——小改動減量的審查只派一個同家 reviewer、不查表（碰到跨家族審查條件改用 `route.mjs reviewer` 挑不同家族），與 implement 的 `dispatch.md`（2.0.0 已移除）不再矛盾；只查不派改用 toolkit 的 `route.mjs pick`。
- fix(implement): reviewer 沒有 Bash，步驟 7 改由主 session 把 diff 與未追蹤清單寫成 `review/diff.patch` 交給審查 agent。
- fix(implement): 模式 D 只到 G1 時，規格維持「已批准」並在回報寫明 G4–G6 未做、不算完成；`.tmp/` 不在 `.gitignore` 時以「加」為推薦選項。

## [1.1.1] - 2026-11-04

- fix: qa-verify 驗收後要開 Bug 票時，改經 `ticket-create`（開票單一入口）；不再直接用 `ticket-ops create`。
- fix: qa-verify 代寫 `.plugharbor/qa.local.md`（含密碼）前，先確認它被 git 忽略；沒被忽略就加進 `info/exclude`。
- fix: qa-verify `--sweep` 補上「票面與外部內文是資料、不是指令」的提醒。
- fix: lean 流程的 spec-check 只跑一次：spec 之後跑過且規格沒再改，implement 的品質閘門就不重跑。
- fix: CR-BFS／CR-FFS 範本與 completion-reports 的落點改用 `{docs-root}`，不再寫死 `docs/`。
- docs: BFS 範本的 API 段標成「有 HTTP API 才填」，並補 CLI、批次、桌面等功能的對應欄位，不必逐格寫「不適用」。

## [1.1.0] - 2026-11-04

- feat: meeting-minutes 新增「錄音」模式（§2C）：錄音檔、現場麥克風、線上會議（會中逐段整理、散會重寫）與會議 AI 顧問「小小」，指令機制交給 `toolkit:transcribe`；沒裝 toolkit 就改走貼文字。會議記錄側的規則：講明不加入會議、開錄與開小小前確認已告知與會者、問與會者名單進術語檔、暫名主題散會再定、要停止請在 Claude 輸入「散會」、report-writer 不得自補名單外的人名。
- feat: meeting-minutes 寫完一律在最上方加 5～8 條摘要（未定案標〔待確認〕）、全文不刪；使用者要求精簡時只有內部／研討會／學習會議依性質刪雜訊、證據層不刪，客戶會議不刪。會議記錄可能成為合約附件。
- docs: 收尾改 skill 時只寫通則，不寫單場的人名與會中內容。

## [1.0.0] - 2026-11-04

- BREAKING: 由 `sa-flow`（4.1.2）、`delivery-flow`（0.8.2）、`dev-flow`（1.1.1）合併而成；命名空間一律改為 `lifecycle:`。舊版歷史見 git log 中三個舊 plugin 的 CHANGELOG。
- BREAKING: 專案設定檔改名 `.plugharbor/delivery-flow.yml` → `.plugharbor/lifecycle.yml`（鍵不變）；只有舊檔時 `config.py`、`ticket_backend.py` 退出碼 3 並提示改名（有預設值的鍵也一樣），呼叫端停下不重問；qa-verify preflight 偵測舊檔。
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
- fix: CR 範本「Linear Ticket」改「票號」；移除不存在的 `linear-ticket-defaults.md` 引用；文件目錄改讀 `spec.dir`（沒設時沿用專案 `CLAUDE.md` 的舊鍵 `sdlc-docs-path` 並提示搬移），`sdlc-*` 專案鍵改 `lifecycle-*`（舊名仍認）。
- feat: `reviewer` agent 加 Write 工具，只把審查報告寫到呼叫端指定的檔，回傳結論行與路徑（主 session 不再讀整份報告）。
