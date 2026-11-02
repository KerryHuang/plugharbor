# Changelog

格式：每次改動 `skills/`、`agents/`、`references/`、`templates/` 時，於最上方新增版本條目並同步 bump 版號（規則見 `.claude/rules/version-consistency.md`）。


## [0.7.2] - 2026-11-02

GitHub 沙盒實測日報／週報、Linear 個人 workspace 實測後修正：

- fix(ticket-ops)：GitHub `query` 一次只放一個時間欄位（同一 search 內是 AND，`created:… closed:…` 會漏掉窗外建立、窗內關閉的票）；`--json` 加 `body` 以解析 `parent`／`blocked-by`
- fix(ticket-ops)：Linear 時間篩選只收下限、上限由叫用端濾；`get_issue` 不回子票，改用 `list_issues(parentId)`；改描述一律用 `save_issue` 的 `patch`（讀回的描述含 `<linear-image>` 等內部標記，整份重送易壞）
- docs(config)：新建 Linear team 預設沒有 In Review，要先補
- fix(ticket-weekly-report)：「上週完成」與「上週新增」拆成兩個查詢；`verify_counts.py` 給了 dataset.json 也驗 HTML 內嵌資料，兩者不同即失敗；票務明細開頭帶「query 完整性」
- fix(ticket-daily-report)：新增 `delivered_prev_day` 清單供「交付停止」燈號與附錄使用（原本拿含今天的窗內交付判斷）；「最高優先」明定為 `urgent`；附錄資料警告照抄「query 完整性」

## [0.7.1] - 2026-11-02

- fix: `plugins/delivery-flow/agents/qa-runner-ui.md` 唯讀環境（`允許寫入: false`）禁止 `press_key` 按 Enter 或任何會送出的鍵，只准 Tab、Escape 與清空用的刪除鍵；步驟要求按 Enter 時停在按之前。`plugins/delivery-flow/skills/qa-verify/references/step-dsl.md` 的 `press` 節同步註明。
- fix: `plugins/delivery-flow/agents/qa-fixture.md` 沒有 DB 工具時不再把 `允許寫入` 一律判 false：可寫性只看設定 `qa.environments[].writable`，`writable: true` 時前置資料照常走畫面建立；沒有 DB 工具只讓 `含個資` 判 true、省略 `查證`，資料斷言回報「未查證（無 DB 工具）」。`plugins/delivery-flow/references/config.md`、`plugins/delivery-flow/skills/qa-verify/SKILL.md`、`plugins/delivery-flow/skills/qa-verify/references/environments.md` 同步。
- fix: `plugins/delivery-flow/skills/ticket-ops/references/github.md` 的 `query` 不再寫死 `--limit 200` 而靜默截斷：改 `--limit 1000`，筆數達上限視為可能截斷，要切時間窗分段合併或改 `gh api --paginate`，仍拿不全就回報「query 完整性：可能截斷」並把數字標為下限。`plugins/delivery-flow/skills/ticket-ops/references/linear.md`、`plugins/delivery-flow/skills/ticket-ops/references/contract.md` 與兩份報表的 `query-strategy.md`（`plugins/delivery-flow/skills/ticket-daily-report/references/query-strategy.md`、`plugins/delivery-flow/skills/ticket-weekly-report/references/query-strategy.md`）同步，報表頂端要有截斷警語。
- fix: `query` 回傳的階段在 `plugins/delivery-flow/skills/ticket-ops/references/linear.md` 與 `plugins/delivery-flow/skills/ticket-ops/references/github.md` 寫明依 `ticket.states` 反查，不在對照表的原生狀態回 `unmapped:<name>`，叫用端列為未分類。
- fix: `plugins/delivery-flow/scripts/config.py` 空字串視為缺鍵、非 UTF-8 設定檔改為退出碼 2 的格式錯誤（不再噴 Traceback），docstring 補上格式錯誤也是退出碼 2；補測試。
- fix: `plugins/delivery-flow/skills/qa-verify/scripts/validate.py` 的 `解析[].查詢` 與 db-check 的 `查詢` 也套用唯讀檢查；補測試。
- fix: `plugins/delivery-flow/references/harness-terms.md` 補 `${CLAUDE_SKILL_DIR}`、`Skill`、`WebFetch`／`WebSearch` 對照（與 `plugins/browser-docs/references/harness-terms.md` 一致），新增 `plugins/delivery-flow/scripts/test_harness_terms_sync.py` 比對兩份。
- fix: `plugins/delivery-flow/references/shared-preludes.md` 補「叫用 `browser-docs:*` 失敗時告知安裝」一行。
- fix: `plugins/delivery-flow/agents/qa-planner.md`、`plugins/delivery-flow/agents/qa-fixture.md`、`plugins/delivery-flow/agents/qa-runner-ui.md`、`plugins/delivery-flow/skills/operation-manual/SKILL.md` 不再用散文指向其他 plugin 的檔案：工具參數速查與 `--isolated` 註冊寫法直接寫進內文。
- fix: `plugins/delivery-flow/skills/prototype-html/references/neutral-style.css` 加 `color-scheme: light dark`，表單控制項邊框改用 `--control-border`（對 surface 約 4:1，符合 WCAG 1.4.11 的 3:1）；`plugins/delivery-flow/skills/prototype-html/SKILL.md` 的既有原型搜尋改用 `find`（bash 預設沒開 globstar），步驟 8 只對「會改變畫面結構」的待確認逐題問。
- fix: `plugins/delivery-flow/skills/operation-manual/references/manual-style-guide.md` 圖說的方括號一律用全形，避免 markdown 圖片語法提早結束。
- fix: `plugins/delivery-flow/package.json` 移除 `version`（版本只在 `plugins/delivery-flow/.claude-plugin/plugin.json` 同步，原本 0.2.1 已漂移），並新增 `plugins/delivery-flow/scripts/test_manifest.py` 防止再次漂移。

## [0.7.0] - 2026-11-02

- feat: 新增 skill `prototype-html`（`plugins/delivery-flow/skills/prototype-html/SKILL.md`）：把需求描述做成單檔、可點切換多畫面的 HTML 原型。需求有歧義時停下來用具體例子問；使用者給設計系統（URL 或檔案）就照它做，沒給就用無品牌的預設風格；資料照使用者樣本的組合，沒有樣本就用寫實組合加假識別值；不綁任何資料庫工具。
- feat: 新增 references `plugins/delivery-flow/skills/prototype-html/references/assembly-guide.md`（組裝與自我驗證）、`plugins/delivery-flow/skills/prototype-html/references/neutral-style.css`（系統字型、CSS 變數可覆寫、亮暗色、無外部資源）、`plugins/delivery-flow/skills/prototype-html/references/mock-data.md`（仿真資料規則）。
- feat: 新增 `plugins/delivery-flow/skills/prototype-html/references/field-layout-criteria.md`：表單欄位版面判準，保留 NN/g、Baymard、GOV.UK、WCAG 出處，去掉內部畫面代號、客戶數字與票號。

## [0.6.0] - 2026-11-02

- feat: 新增 skill `operation-manual`（`plugins/delivery-flow/skills/operation-manual/SKILL.md`）：實機探索、標註截圖、撰寫、審查、出 PDF／PPTX／Word 的操作手冊流程，並把探索中發現的規格落差依類型分流。環境讀 `qa.environments`（只用 `writable: true`），登入帳密放 `.plugharbor/qa.local.md`。
- feat: 新增 agent `plugins/delivery-flow/agents/manual-explorer.md`、`plugins/delivery-flow/agents/manual-writer.md`、`plugins/delivery-flow/agents/manual-reviewer.md`。`manual-explorer` 的 `tools` 加上 `Skill`，標註改叫用 `browser-docs:annotate-screenshot`，不再以路徑引用 browser-docs 的 annotate.py。
- feat: 新增 references `plugins/delivery-flow/skills/operation-manual/references/`：annotation-dispatch、build-deliverables、exploration-checklist、gaps-triage、red-flags、run-log 由既有流程改寫；manual-style-guide、skeleton-manual、skeleton-slides 以虛構產品重寫，保留圖文比、模式純度、caption 對帳等結構規則。
- feat: 新增產線腳本 `plugins/delivery-flow/scripts/`：`build-manual-pdf.py`、`build-manual-docx.sh`、`prep-docx-cover.py`、`make-docx-reference.py`、`build-deck.sh`、`check-deck-overflow.py`、`check-inventory-rects.py`、`text-image-ratio.py`、`ensure-tools.sh`、`manual-print.css`、`manual-reference.docx`（由 `make-docx-reference.py` 重新生成，作者與公司欄位為空）。
- feat: 封面品牌參數化：`build-manual-pdf.py`、`build-manual-docx.sh`、`prep-docx-cover.py` 接 `--brand`；未給則讀設定 `manual-brand`（`plugins/delivery-flow/scripts/manual_brand.py`），都沒有就不印任何品牌。`plugins/delivery-flow/references/config.md` 說明 `manual-brand` 為字串。
- fix: inventory 的 `rect` 改為 `[x0, y0, x1, y1]`（CSS px），與 `browser-docs` 標註 spec 的 `box` 同格式；`check-inventory-rects.py` 同步改驗 x1 > x0、y1 > y0 與圖面範圍。
- fix: `ensure-tools.sh` 新增 Pillow 檢查，並移除 `.python-path` 與 mkdocs 環境假設，一律用 `python3`；Chrome 偵測改為內嵌的存在檢查，找不到時指向 `browser-docs:live-drive`。
- test: 新增 `plugins/delivery-flow/scripts/test_manual_brand.py`（品牌來源優先序、PDF 封面、denylist 與 docx metadata 檢查，無 `.leak-denylist` 時只略過該項）與 `plugins/delivery-flow/scripts/test_check_inventory_rects.py`，直接執行 `python3 <檔>`。

## [0.5.0] - 2026-11-02

- feat: 新增 skill `qa-verify`（`plugins/delivery-flow/skills/qa-verify/SKILL.md`）：依驗收案例檔或票號做實機 E2E 驗收，派 `qa-planner`、`qa-fixture`、`qa-runner-ui` 三個 agent，機械判定 PASS／FAIL／前端未擋／BLOCKED／未執行／無法比對並產 `qa-report.md`；讀票（`get`）與回票（`comment`）一律經 `delivery-flow:ticket-ops`。
- feat: 新增中性驗收案例格式 `plugins/delivery-flow/skills/qa-verify/references/acceptance-format.md`（markdown 或 YAML，欄位 `id`、`title`、`preconditions[]`、`steps[]`、`expected[]`、`channel?`），`plugins/delivery-flow/skills/qa-verify/scripts/validate.py` 新增 `acceptance` 模式驗證；plan 的來源改為 `meta.規格.案例檔`，移除對特定規格文件章節的依賴。
- feat: 新增 agent `plugins/delivery-flow/agents/qa-planner.md`、`plugins/delivery-flow/agents/qa-fixture.md`、`plugins/delivery-flow/agents/qa-runner-ui.md`；環境可寫性改讀設定 `qa.environments`（`{name, url, writable}`），登入帳密放 `.plugharbor/qa.local.md`，不再查環境表或公司資料。
- feat: `ticket-ops` 契約新增第七個操作 `get`（單張票的標題、body、階段、labels、parent、children、url、updatedAt），`plugins/delivery-flow/skills/ticket-ops/references/linear.md`、`github.md` 補對映（GitHub 的 parent 讀 body 的 `parent: #n`，children 讀 task list）。
- fix: fixtures 的 `環境.依據` 改為必填、`環境.查證` 改為選填且限 SELECT／WITH 唯讀查詢（禁中途分號與寫入字）；markdown 案例檔解析改為非案例 `##` 行結束目前案例，缺標題、未知區段會報錯，支援全形冒號、通道轉小寫、圍欄與 BOM；YAML 語法錯誤印單行錯誤不拋 traceback。
- docs: `plugins/delivery-flow/references/config.md` 新增 `qa.environments` 鍵與範例。
- test: 新增 `plugins/delivery-flow/skills/qa-verify/scripts/test_validate.py`、`test_judge.py`、`test_report.py`（含 `test_neutral_format_minimal`），直接執行 `python3 <檔>`。

## [0.4.1] - 2026-11-02

- fix: `plugins/delivery-flow/skills/ticket-ops/references/contract.md` 的 `query` 補 `url`、`assignee?`、`createdAt?`、`completedAt?`（僅 `done`）、`priority?`（正規化為 urgent／high／medium／low／none）、`dueDate?`，篩選加建立與完成時間範圍；`estimate` 不納入。`linear.md`、`github.md` 補對映（GitHub 以 not planned 關閉不算 `completedAt`，`dueDate` 恆為空）。
- fix: `ticket-daily-report`、`ticket-weekly-report` 移除以 `updatedAt` 近似完成日的退路，ticket-ops 未回傳 `completedAt` 時 delivered、cleanup、lead 標「未提供」；停滯天數仍用 `updatedAt`。
- fix: `ticket-daily-report` 的 `--out-dir` 不存在時停下回報；`plugins/delivery-flow/skills/ticket-weekly-report/references/publishing.md` 移除過時的 HedgeDoc 段落。
- test: 新增 `plugins/delivery-flow/skills/ticket-weekly-report/scripts/test_verify_counts.py`（一致、數字不符、按鈕無資料集、資料集未引用四案）。

## [0.4.0] - 2026-11-02

- feat: 新增 skill `ticket-daily-report`（`plugins/delivery-flow/skills/ticket-daily-report/SKILL.md`）：每日票務進度報表，走看板找卡點、只列今天變壞的事；資料一律經 `delivery-flow:ticket-ops` 的 `query`，前景派發 `delivery-flow:report-writer` 產主報表與票務明細。priority、estimate、dueDate 為選配欄位，dataset 有才呈現；已移除 SA 票樹角色假設。
- feat: 新增 skill `ticket-weekly-report`（`plugins/delivery-flow/skills/ticket-weekly-report/SKILL.md`）：每週進度報表，產出會議簡報 HTML、週報、票務明細三份；簡報數字可點開抽屜（骨架 `plugins/delivery-flow/skills/ticket-weekly-report/references/drawer-template.html`），發布前以 `plugins/delivery-flow/skills/ticket-weekly-report/scripts/verify_counts.py` 複驗數字與清單一致。
- feat: 兩個 skill 以 `--out-dir` 取代原本的 Linear Document 發布，預設只留在 `.tmp/`，不寫入票務工具。

## [0.3.1] - 2026-11-02

- fix: `ticket-ops` 移除 gist 附圖路線（`gh gist create` 不收二進位檔，佔位流程可能漏出壞連結），`github_attach_plan(repo, image_path)` 只保留存進 repo 的做法。
- fix: `attach` 契約改為必須回報圖實際位置與連結是否有效；GitHub 須 push 到預設分支（經使用者確認）才貼連結，否則回報「圖仍在本機 <path>，未附」。
- fix: 附圖連結的檔名做 URL 編碼；`plugins/delivery-flow/skills/ticket-ops/references/linear.md` 說明 `create` 的 `state` 與 `set_stage` 一樣用 ID。

## [0.3.0] - 2026-11-02

- feat: 新增 skill `ticket-ops`（票務工具層）：定義建票、改階段、留言、附圖、查詢、blocked-by 六個操作契約，依 `ticket.tool` 載入 Linear 或 GitHub Issues 做法；Jira 只有設定對照範例（未實測），叫用時需使用者確認才繼續。
- feat: 新增 `plugins/delivery-flow/skills/ticket-ops/scripts/ticket_backend.py`：`stage_to_native` 依 `ticket.states` 把抽象階段轉成 Linear state 名稱或 GitHub label／關閉動作，`github_attach_plan` 產出附圖存放位置與 markdown（GitHub 無官方圖片上傳 API）。
- fix: `issue-triage` 查既有票與交棒開票改明確叫用 `delivery-flow:ticket-ops`。
- docs: `plugins/delivery-flow/references/config.md` 的 GitHub 範例 label 改為 `stage:<名稱>` 慣例。

## [0.2.1] - 2026-11-02

- fix: `issue-triage` 新增讀取 `ticket.tool` 的前置步驟，缺檔或缺鍵（退出碼 2）時依 `references/harness-terms.md` 提問並寫入 `.plugharbor/delivery-flow.yml`；刪除與 report-writer constraints 重複的落檔規則。
- fix: `publish-target` 沒有內建預設值，`meeting-minutes` 與 `references/config.md` 的「預設」改為建議值；`meeting-minutes` 的 conventions 引用補完整路徑 `plugins/delivery-flow/skills/meeting-minutes/references/recording-conventions.md`。

## [0.2.0] - 2026-11-02

- feat: 新增 skill `meeting-minutes`：即時記錄與會後整理；落檔與發布位置讀 `publish-target`（`file:<目錄>` 存本機為預設，`hedgedoc:<url>` 需自架且尚未實測）；補回「內部備註（非會議內容）」規則，記錄人的推論與假設情境不混進會議條目；第二意見審閱改為通用的唯讀 subagent。
- feat: 新增 skill `interview-prep`：多場素材彙整成已知／未知盤點，或產出受訪者訪談大綱；每條標已確認／待確認／可能推測並附出處；Fireflies 逐字稿為選配。
- feat: 新增 skill `issue-triage`：回饋逐項對照現況 codebase 分成 Bug／Enhancement／Feature，標既有票與規格文件，產出可開票的問題清單。
- feat: 新增 `templates/meeting-minutes.md`、`templates/requirement-synthesis.md`、`templates/interview-outline.md`。

## [0.1.1] - 2026-11-02

- fix: `scripts/config.py` 遇 YAML 語法錯誤或最上層非對應時，以一行格式錯誤訊息結束（退出碼 2），不再丟 traceback；缺檔指引改點名實際要求的鍵；值為空視同缺鍵。
- docs: `references/config.md` 說明退出碼 2 由呼叫的 skill 提問並寫檔。
- test: `scripts/test_config.py` 補語法錯誤、非對應、空檔、空值測試。

## [0.1.0] - 2026-11-02

- feat: 新 plugin 骨架：`plugin.json` 宣告 `dependencies: ["browser-docs"]`、`package.json`（pi）。
- feat: 共用 references：`shared-preludes.md`、`dispatch-conventions.md`、`harness-terms.md`（與 browser-docs 同份）、`report-calendar.md`、`config.md`。
- feat: 設定載入 `scripts/config.py`（讀 `.plugharbor/delivery-flow.yml`，缺鍵給建檔指引）與 `scripts/test_config.py`。
- feat: 新增 `report-writer` agent（吃資料集、範本、輸出路徑，不綁報表種類）。
