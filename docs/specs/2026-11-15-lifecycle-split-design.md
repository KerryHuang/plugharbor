# lifecycle 簡化與拆分：設計

狀態：討論定案，待使用者審（2026-11-15）。決定逐條標「使用者裁決」或「撰寫時自行決定」。

## 起因

- 一個單人專案從 2026-11-03 到 11-15 跑了 24 個 session，使用者覺得「很順手」。盤點 transcript：實際撐起流程的是 superpowers（設計 → 計畫 → subagent 實作 → 審查）、workspace:unattended（帳本、裁決分類、閘門、上線）、toolkit:agent-dispatch（跨家族審查）與專案自己的上線／驗證 skill；**lifecycle 只用到 `feature_checklist.py`（165 次），skill 一個都沒叫**。
- 本機約兩週的 transcript 裡，lifecycle 22 個 skill 只有 7 個被叫過（ticket-ops、spec、spec-check、implement 各 7 次，ticket-create 3、release 2、explore 2），多數在測試用的臨時專案；其餘 15 個 0 次。更早的紀錄與別台電腦看不到。
- lifecycle 的主力是四份文件的規格鏈（FRD／SAD／BFS／FFS）與角色分票，是為 PM／SA／QA／Dev 分工設計的；本機沒有任何專案設 `scale: full`。
- 該專案品質的關鍵有三件 lifecycle 沒有：計畫寫完先審（初審抓到 10 項必修、修訂後再 3 項）、跨家族審查、變異驗證。

## 目標

1. **superpowers 當工程核心**：設計、計畫、實作、審查、收尾分支交給它；lifecycle 不再自建一套。
2. **團隊有裝、沒裝 superpowers，產物同格式**：沒裝的成員走 lifecycle 的退路，產出的設計文件與計畫位置、章節、task 格式一樣，只是能力較少（不派 subagent、自審）。
3. **lifecycle 只管做之前與做之後**：功能清單排線、同步票、驗收、發版。
4. **可以只裝需要的部分**：票務、需求與會議、交付文件各自成 plugin。

非目標：改 superpowers 本身（外部 plugin）；改 workspace:unattended 的工作單元流程；周邊 skill 的內容改寫（只搬家）。

反目標（做了也算失敗）：使用者現在順手的流程（直接走 superpowers）多出必經步驟；團隊成員要改個人 user 層設定才能正常用。

## 架構

| 層 | 負責 | 內容 |
|---|---|---|
| 工程核心 | superpowers | brainstorming、writing-plans、執行、審查、finishing |
| 編排 | workspace、toolkit | 自動駕駛帳本、閘門、上線、跨家族審查、派工 |
| 開發主線 | lifecycle | spec（設計文件）、spec-check（實作前檢查）、implement（薄入口＋退路）、qa-verify、release、功能清單腳本 |
| 票務 | tickets（新） | ticket-ops、ticket-create、ticket-reply、ticket-report、triage、對帳 |
| 需求與會議 | discovery（新） | meeting-minutes、interview-prep、survey-existing-system、prototype-html |
| 交付文件 | delivery（新） | operation-manual、demo-video |

兩個都裝時（使用者裁決）：**流程聽 superpowers，設定與接點聽 lifecycle**。裁決寫在專案層 `AGENTS.md` 的標準段落（見「接點」），不靠個人 user 層。沒預料到的衝突用 AskUserQuestion 問人。

## 決定

### lifecycle（開發主線）

- **規格鏈移除**（使用者裁決）：拿掉 FRD／SAD／BFS／FFS 與 `--change` 的 CR 變體、`scale` 設定。spec 只產一份設計文件，章節對齊 superpowers 設計文件，並**固定有「驗收」一節**，寫成 qa-verify 讀得懂的案例格式（使用者裁決，取代 FFS 第 8 章轉案例）。
- **誰寫 spec／plan**（使用者裁決）：裝了 superpowers 就交給 brainstorming／writing-plans，lifecycle 只補「驗收一節」與「設計文件開頭連票」；沒裝才照同格式自己寫。
- **explore 移除**（使用者裁決）：spec 的退路吸收「把決策樹每個分支都解完」的問法，但一次一題、用 AskUserQuestion、推薦選項放第一。grill-me（外部、一輪多題、不產檔）不進 lifecycle。
- **spec-check 縮成「實作前檢查」**（使用者裁決）：只留 superpowers 沒有的——對照真實 DB 與程式碼驗設計文件，以及驗收一節是否可測；對抗式找缺口交給 brainstorming 的建造者檢查，沒裝才用簡版。
- **implement 留作薄入口＋同格式退路**（使用者裁決）：有 superpowers 就轉交；沒裝走升級後的退路（寫同格式計畫 → 計畫審查 → 逐項 TDD → 自審 → 收尾）。讀 LEARNINGS 的前段移除（撰寫時自行決定，隨 LEARNINGS 移除）。
- **after.md 只留兩段**（使用者裁決）：逐條對照設計文件驗收一節；回填（功能清單打勾＋同步票）。整合測試交閘門；LEARNINGS 移除。
- **計畫審查**（使用者裁決）：寫進專案層 `AGENTS.md` 段落，implement 退路也有一步；跨家族優先，沒有就同家新 context，必修修完才開工。
- **隨規格鏈移除的 skill**：spec-chain（撰寫時自行決定）、explore、consolidate-docs、write-doc、dev-feedback（使用者接受分類）。
- **agent**：依留下的 skill 機械精簡，沒有 skill 引用的移除（使用者同意不另問）。

### tickets（票務）

- ticket-create 拿掉 PM／SA／QA／Dev 四張角色子票（使用者裁決）：預設一張票；大功能依設計文件或功能清單的段拆子票（與「清單節＝父票、項目＝子票」一致）。
- 對帳 `reconcile.py` 目前 import lifecycle 的 `feature_checklist.py`：tickets 帶自己的解析副本，加同步測試。

### discovery、delivery

只搬家、不改行為。plugin-healthcheck 搬到本 repo 的 `.claude/skills/`（它健檢的是 plugin 本身）。

### 共用

- **設定檔**（使用者裁決）：四個 plugin 共用 `.plugharbor/lifecycle.yml`，各讀自己的區塊；既有專案不搬。
- **跨 plugin 依賴一律可選＋退路**（repo 規則）：例如 lifecycle 收尾沒裝 tickets 就只勾清單；triage 要寫規格但沒裝 lifecycle 就只給建議。
- **共用素材各複製一份＋同步測試**：
  - 腳本：`config.py`、清單解析（`feature_checklist.py` 的解析部分）。
  - agent：`report-writer`（spec-check、ticket-report、triage、meeting-minutes）、`scout`（spec、spec-check、triage、survey-existing-system）、`silent-failure-hunter`（triage、survey-existing-system）、`domain-advisor`（spec、survey-existing-system）。同名 agent 會撞 `validate.py` 的 `check_name_collisions`（pi、Codex 扁平命名）→ **副本改名**（使用者裁決），例如 `ticket-report-writer`、`discovery-scout`；檢查器不動，同步測試比對改名後的內文。
  - references：`harness-terms.md`（22 個 skill 都用）、`shared-preludes.md`、`dispatch-conventions.md`、`config.md`、`pipeline.md`（triage）、`feature-checklist.md`（ticket-ops）。
  - 既有的 `scripts/test_harness_terms_sync.py` 比對 lifecycle 與 browser-docs 的 5 個副本，annotate／anonymize 相關檔隨 operation-manual 搬到 delivery，測試要跟著改。
- **agent 去留要算跨 plugin 引用**：`architect`、`developer` 在 lifecycle 內沒有 skill 引用，但 backend（data-access、layered-architecture、unit-testing）、frontend-architecture、workspace 的 `debugging/references/tdd-cycle.md` 可選引用它們 → 保留。
- **轉交改指**：triage、ticket-create 指向 explore 的地方改指 spec。
- **舊設定 `scale`**：`config.py` 拿掉 `scale` 預設；遇到舊鍵印一行提示後忽略，不擋流程（撰寫時自行決定）。

## 接點

- **進場**：票號或清單項目的 `#n` 寫進設計文件開頭；brainstorming 讀那張票當輸入。
- **出場**：收尾照 lifecycle 的 `after.md` 兩段做。
- **專案層 `AGENTS.md` 標準段落**（使用者裁決）：lifecycle 提供一段文字，`setup/install-project.sh --shared` 裝 lifecycle 時寫入（已有就更新，用標記圍住以便更新）；專案有 `CLAUDE.md` 而沒引用 `AGENTS.md` 時補一行 `@AGENTS.md`（使用者裁決）。預設的 local 安裝不碰受版控的檔，個人用靠 user 層規則。內容：設計文件放 `<spec.dir>`、計畫位置、計畫審查、「開始實作」以 implement 為入口、收尾後接清單＋同步票、Git Flow 的專案交 release，以及**精簡的驗收案例格式**（幾行，讓 brainstorming 寫設計文件時直接帶上驗收一節；使用者裁決，不另加必經步驟）。直接說「brainstorm」的入口也經過它。
- **團隊安裝 superpowers**（使用者裁決）：團隊 repo 在 `.claude/settings.json` 宣告 superpowers（官方 marketplace），成員信任資料夾後提示安裝。

## 與現況衝突、必須一起改

- `setup/install-project.sh` 第 123 行起：**裝 lifecycle 就在專案停用 superpowers**（2026-11-04 df1651e「lifecycle 取代 Superpowers」）。與目標 1 相反，第一批改成不停用（改為寫入上面的宣告與段落屬第三批）。已查：使用中的專案目前沒有被停用的紀錄。
- `setup/tests/install-project.sh` 第 12 段測的就是停用 superpowers，第一批重寫。
- user 層規則 `superpowers.md`（在 setup 的 home 目錄下）兩行要改：「裝了 lifecycle 時…先叫 `lifecycle:implement` 前段（讀經驗、規格閘門）」與「有 lifecycle 照它的 references/feature-checklist.md」；常駐 context 不得變長。
- 引用 lifecycle skill 的其他檔：`plugins/workspace/skills/quality-check/SKILL.md`、`plugins/workspace/skills/project-setup/references/flow.md`、`plugins/workspace/skills/submodule-relay/SKILL.md`（引用 release，留在 lifecycle 不用改，要確認）、`plugins/research/.../test_harvest.py`。
- 文件：根 `README.md` 的 plugin 表、「skills 與 agents」表與第 78–80 行流程段（explore、`scale: full`）、`setup/README.md` 第 34 行、`docs/agent-parity.md` 第 86、91 行。
- `marketplace.json`、pi 的 `package.json`、`setup/` 的 plugin 清單（user 層／專案層分類）。
- CI：腳本測試迴圈是 glob `plugins/**/test_*.py`，新 plugin 自動納入；寫死路徑的是 `.github/workflows/validate.yml` 第 50 行的 demo-video e2e，要改成 delivery。
- plugin-healthcheck 搬到 `.claude/skills/` 後會離開 glob 與 validate 的掃描範圍，它引用的 `../../references/harness-terms.md` 會斷：搬時改引用並確認測試仍被跑到。

## 分批（使用者裁決）

每批各自發版、各自驗收：

1. **先刪**：規格鏈與連帶 skill、agent、範本、`scale`；`install-project.sh` 不再停用 superpowers；qa-verify 改讀設計文件驗收一節；ticket-create 拿掉角色子票。lifecycle major。
2. **再拆**：tickets、discovery、delivery 三個新 plugin（1.0.0），只搬不改行為；共用素材複製（agent 改名）＋同步測試；lifecycle 再 major。既有專案遷移（使用者裁決）：`install-project.sh` 看到 `.plugharbor/lifecycle.yml` 有 `ticket:` 區塊就順便裝 tickets；不用 `ph_rename_new`（它是 plugin 一對一改名、會卸載舊名，會把 lifecycle 一起卸掉）。
3. **最後接**：AGENTS.md 標準段落與寫入、計畫審查、同格式退路、spec 退路的問法、spec-check 縮減、implement 變薄、after.md 精簡、user 層 superpowers.md 改寫。lifecycle minor。

與「票務雙軌示範」並行（使用者裁決）：第二批搬家後改叫用名稱，示範順便驗搬家沒壞。

## 驗收

- 每批：`python3 scripts/ci/validate.py` 過；全部 plugin 腳本測試、setup 測試過；`claude -p --plugin-dir` e2e（push 前）。
- 第一批：spec 只產一份含「驗收」一節的設計文件；qa-verify 能從該節產案例；`install-project.sh` 不再寫停用 superpowers。
- 第二批：只裝 tickets（不裝 lifecycle）能建票、改階段、對帳；只裝 discovery 能做會議記錄；同步測試抓得到副本漂移。
- 第三批：兩個情境 e2e——(A) 裝 superpowers：說「開始實作」走 superpowers，收尾有清單打勾與同步票；(B) 沒裝：走退路，產出的設計文件與計畫章節和 (A) 一致，有計畫審查一步。

## 考慮過的做法

- **保留規格鏈**（我原本的建議）：交付文件給不同讀者（PO 簽核、SA、前後端、QA）。使用者裁決拿掉：沒有人在用、團隊要的是一致的規劃結構。
- **把 superpowers 整套抄進 lifecycle**：沒裝的人能力最接近；但 superpowers 持續改版，副本會漂移。改為只對齊格式。
- **不拆 plugin、等起因**（我原本的建議）：成本最低。使用者裁決這輪一起拆，讓只要票務或會議記錄的人不用整包裝。
- **出場接點放 user 層規則或 hook**：user 層只管得到自己的電腦；hook 只管出場、成本高。改放專案層 AGENTS.md。

## 撰寫時自行決定的事（待使用者確認）

1. spec-chain 隨規格鏈移除。
2. implement 讀 LEARNINGS 的前段隨 LEARNINGS 移除。
3. `install-project.sh` 不再停用 superpowers 放第一批（不等第三批），因為它直接違反目標 1。
4. 新 plugin 版號從 1.0.0 起；lifecycle 第一、二批各一次 major。
5. 計畫位置沿用 `.tmp/plans/<yyyymmdd-slug>/`，寫進 AGENTS.md 段落。
6. 第一批到第三批之間，superpowers 產的設計文件還沒有驗收一節：qa-verify 的退路是從設計文件內文擬案例、請人確認。
7. 在專案 `.claude/settings.json` 宣告 superpowers 只在 `install-project.sh --shared` 時做，預設的 local 模式不寫。

## 未驗證

- superpowers 能否只靠專案層 `.claude/settings.json` 宣告，在乾淨的機器上被提示安裝（官方文件說 `extraKnownMarketplaces` 要信任資料夾後才生效；官方 marketplace 預期更單純，未實測）。
- 周邊 skill 在別台電腦的使用量。

## 留給 builder

- 各批的檔案清單與搬遷順序、同步測試的寫法、AGENTS.md 段落的確切文字與標記格式、設計文件「驗收」一節的案例格式（以 qa-verify 現有 `acceptance-format.md` 為準）。
