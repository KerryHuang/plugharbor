# Changelog

格式：每次改動 `skills/`、`agents/`、`references/`、`templates/` 時，於最上方新增版本條目並同步 bump 版號（規則見 `.claude/rules/version-consistency.md`）。

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
