# Changelog

格式：每次改動 `skills/`、`agents/`、`references/`、`templates/` 時，於最上方新增版本條目並同步 bump 版號（規則見 `.claude/rules/version-consistency.md`）。

## [0.1.0] - 2026-11-02

- feat: 新 plugin。`live-drive` skill（investigate／e2e／explore 三模式，主 session 不開瀏覽器，全派 agent）、`browser-surveyor` agent（survey／capture／investigate／measure，含純 icon 按鈕的找法）。
- feat: `scripts/browser-doctor.py`（檢查 chrome-devtools MCP 註冊與版本，清殘留 profile，退出碼 0 為就緒）與 `test_browser_doctor.py`、`find-chrome.sh`。
- docs: `references/` 附 `browser-setup.md`（MCP 標準註冊）、`browser-tooling.md`（隔離模型與工具速查）、`harness-terms.md`（Claude Code 與 Pi 用語對照）。
- 後續版本會加入截圖標註、脫敏與 PDF 轉檔。
