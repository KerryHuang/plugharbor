# Changelog

格式：每次改動 `skills/`、`agents/`、`references/`、`templates/` 時，於最上方新增版本條目並同步 bump 版號（規則見 `.claude/rules/version-consistency.md`）。

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
