# Changelog

格式：每次改動 `skills/`、`agents/`、`references/`、`templates/` 時，於最上方新增版本條目並同步 bump 版號（規則見 `.claude/rules/version-consistency.md`）。

## [0.1.1] - 2026-11-02

- fix: `scripts/config.py` 遇 YAML 語法錯誤或最上層非對應時，以一行格式錯誤訊息結束（退出碼 2），不再丟 traceback；缺檔指引改點名實際要求的鍵；值為空視同缺鍵。
- docs: `references/config.md` 說明退出碼 2 由呼叫的 skill 提問並寫檔。
- test: `scripts/test_config.py` 補語法錯誤、非對應、空檔、空值測試。

## [0.1.0] - 2026-11-02

- feat: 新 plugin 骨架：`plugin.json` 宣告 `dependencies: ["browser-docs"]`、`package.json`（pi）。
- feat: 共用 references：`shared-preludes.md`、`dispatch-conventions.md`、`harness-terms.md`（與 browser-docs 同份）、`report-calendar.md`、`config.md`。
- feat: 設定載入 `scripts/config.py`（讀 `.plugharbor/delivery-flow.yml`，缺鍵給建檔指引）與 `scripts/test_config.py`。
- feat: 新增 `report-writer` agent（吃資料集、範本、輸出路徑，不綁報表種類）。
