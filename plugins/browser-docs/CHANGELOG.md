# Changelog

格式：每次改動 `skills/`、`agents/`、`references/`、`templates/` 時，於最上方新增版本條目並同步 bump 版號（規則見 `.claude/rules/version-consistency.md`）。


## [0.3.3] - 2026-11-03

- docs: harness-terms 的 `${CLAUDE_PLUGIN_ROOT}` 補 Codex／agy 專案層 symlink 載入時的 plugin 根判定（realpath 往上兩層；複製模式讀 `.plugharbor-root`）。

## [0.3.2] - 2026-11-02

- fix: `plugins/browser-docs/skills/pdf-converter/scripts/verify_roundtrip.py` 新增 `ConversionFailed`，只在 LibreOffice 轉檔失敗或逾時時以退出碼 2 結束；原本 `except RuntimeError` 過寬，fitz 的損毀 PDF 錯誤會被誤報成「轉檔失敗」。`plugins/browser-docs/skills/pdf-converter/SKILL.md` 錯誤表補上退出碼 2 的處理，並補測試。
- fix: 座標換算改為「影像寬 ÷ `innerWidth`」，不再寫死 DPR 2 乘 2（viewport 或 DPR 不同時紅框會畫錯位置）：`plugins/browser-docs/skills/annotate-screenshot/SKILL.md`、`plugins/browser-docs/references/annotate-spec.md`、`plugins/browser-docs/references/browser-tooling.md`、`plugins/browser-docs/scripts/annotate.py`。
- fix: `plugins/browser-docs/references/harness-terms.md` 補 `${CLAUDE_SKILL_DIR}`、`Skill`、`WebFetch`／`WebSearch` 三列對照（與 `plugins/delivery-flow/references/harness-terms.md` 保持一致）。
- fix: `plugins/browser-docs/agents/browser-surveyor.md` 與 `plugins/browser-docs/skills/live-drive/references/safety.md` 的 `press_key` 清空輸入框例外改為只適用可寫環境（唯讀環境不 `fill`，也就不需要清空）。
- fix: `plugins/browser-docs/README.md` 與 `plugins/browser-docs/skills/live-drive/references/browser-bootstrapping.md` 寫出登入設定檔確切鍵名 `live-drive-url`、`live-drive-username`、`live-drive-password`。
- fix: `plugins/browser-docs/package.json` 移除 `version`（版本只在 `plugins/browser-docs/.claude-plugin/plugin.json` 同步），並新增 `plugins/browser-docs/scripts/test_manifest.py` 防止再次漂移。

## [0.3.1] - 2026-11-02

- fix: Word 已註冊但 pywin32 缺少或啟動失敗時，改用 LibreOffice；兩者都不可用時訊息含 pywin32 與安裝指引。
- fix: LibreOffice 轉檔逾時或失敗以一行訊息結束（退出碼 2），不再丟 traceback。
- docs: `pdf-converter` 產出位置措辭改為「由其他 skill 流程呼叫」。

## [0.3.0] - 2026-11-02

- feat: 新增 `pdf-converter` skill（PDF 轉 Word／Excel、回轉三軸驗證、範本模式）與 `doc-fidelity-reviewer` agent。
- feat: 回轉驗證加 LibreOffice 後備：新增 `skills/pdf-converter/scripts/converter_select.py`（`select_converter(env)`，Windows 有 Word 用 Word COM，否則 `soffice --headless --convert-to pdf`）；兩者皆無時 `skills/pdf-converter/scripts/verify_roundtrip.py` 印安裝指引、退出碼 3。
- feat: `skills/pdf-converter/scripts/verify_roundtrip.py` 的 `word` 子命令 新增 `--allow-degraded`，找不到轉換器時改為只驗文字軸（原本的自動降級改為明確選用）。
- test: 新增 `skills/pdf-converter/scripts/test_converter_select.py`（以模擬 env 驗證，CI 不需 Word／soffice）。

## [0.2.0] - 2026-11-02

- feat: 新增 `annotate-screenshot` skill：截圖加框、編號、圖例、遮罩，或以真實片段合成調整後示意圖；輸出 `-annotated.png` 並保留 clean 原圖，可由其他 skill 或 agent 以 Skill 工具叫用。
- feat: 新增 `scripts/annotate.py`（含 `mask` op）、`scripts/anonymize-page.js`（截圖前換假資料）與 `scripts/test_annotate.py`。
- docs: 新增 `references/annotate-spec.md`、`references/anonymize-before-capture.md`。

## [0.1.2] - 2026-11-02

- fix: 唯讀環境禁止清單補上 `press_key`（`browser-surveyor` 與 `live-drive` 的 `safety.md`），唯一例外是為 `fill` 清空輸入框，不得按 Enter 等會送出的鍵；`browser-tooling.md` 同步註明。

## [0.1.1] - 2026-11-02

- fix: `browser-surveyor` 的 tools 補上 `get_network_request`、`get_console_message`、`press_key`（investigate 模式與 `fill` 清空流程需要）；`live-drive` description 去掉 debug-port 說法；修正「四模式」「三條規則」等文字不符。

## [0.1.0] - 2026-11-02

- feat: 新 plugin。`live-drive` skill（investigate／e2e／explore 三模式，主 session 不開瀏覽器，全派 agent）、`browser-surveyor` agent（survey／capture／investigate／measure，含純 icon 按鈕的找法）。
- feat: `scripts/browser-doctor.py`（檢查 chrome-devtools MCP 註冊與版本，清殘留 profile，退出碼 0 為就緒）與 `test_browser_doctor.py`、`find-chrome.sh`。
- docs: `references/` 附 `browser-setup.md`（MCP 標準註冊）、`browser-tooling.md`（隔離模型與工具速查）、`harness-terms.md`（Claude Code 與 Pi 用語對照）。
- 後續版本會加入截圖標註、脫敏與 PDF 轉檔。
