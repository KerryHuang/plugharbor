# browser-docs

瀏覽器實機操作與文件轉檔。提供 Chrome 實機驅動、畫面勘察、截圖標註，以及 PDF 轉 Word／Excel 與擬真度驗證。

## 安裝

```bash
claude plugin marketplace add https://github.com/KerryHuang/plugharbor.git
claude plugin install browser-docs@plugharbor
```

## 環境需求

| 項目 | 用途 | 備註 |
|------|------|------|
| chrome-devtools MCP | 所有瀏覽器操作 | 一律以 `--isolated` 註冊，標準寫法見 `references/browser-setup.md` |
| Chrome | MCP 啟動的瀏覽器 | `scripts/find-chrome.sh` 協助找路徑 |
| Pillow | 截圖標註（`annotate-screenshot`）、`pdf-converter` 擬真度比對 | `pip install pillow` |
| Word 或 LibreOffice | `pdf-converter` 的回轉驗證（docx 轉回 PDF 比對） | 擇一；Windows 優先用 Word，其他情況用 `soffice --headless`。都沒有時 verify 退出碼 3 |
| pymupdf、python-docx、openpyxl | `pdf-converter` 萃取與生成 | 缺套件的備妥方式見該 skill |

註冊後重啟 session，再跑：

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/browser-doctor.py
```

輸出 `OK`（退出碼 0）才算就緒；否則它會印出標準註冊寫法。

## skills 與 agents

| 名稱 | 類型 | 說明 |
|------|------|------|
| `live-drive` | skill | 透過 chrome-devtools MCP 操作執行中的系統：重現問題（investigate）、跑 e2e、探索現況（explore）。正式環境一律唯讀。 |
| `annotate-screenshot` | skill | 在截圖上畫框、編號、圖例、遮罩，或合成調整後示意圖；輸出 `-annotated.png` 並保留 clean 原圖。截圖前的假資料替換見 `references/anonymize-before-capture.md`。可由其他 skill、agent 叫用。 |
| `pdf-converter` | skill | PDF 轉 Word／Excel 且版面內容一致：機器萃取、回轉三軸驗證迴圈、佔位符範本模式。回轉用 Word 或 LibreOffice。 |
| `browser-surveyor` | agent | 走到指定畫面，記錄欄位、預設值、驗證訊息、console、network，截圖落證據檔。只觀察不解讀；由 `live-drive` 派發。 |
| `doc-fidelity-reviewer` | agent | 讀 `pdf-converter` 的 verify-report.json 與 diff PNG，翻成修正指示或判可接受放行。唯讀；由 `pdf-converter` 於 soft_fail 時派發。 |

## 登入設定

`live-drive` 讀 workspace 的 `.claude/live-drive.local.md`（或 `CLAUDE.local.md`）取得 `live-drive-url`、`live-drive-username`、`live-drive-password`（一行一鍵，`鍵: 值`）。此檔勿提交，憑證不會寫進任何產出。

## 其他 CLI

skill 以 Claude Code 用語撰寫；Pi 等其他 harness 先讀 `references/harness-terms.md`。Codex／Pi 只保證 skill 載入得到，跨 CLI 的叫用語法未實測。
