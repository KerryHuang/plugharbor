---
name: pdf-converter
description: "把 PDF 轉成 Word 或 Excel 且版面內容須完整一致：含回轉驗證迴圈與佔位符範本模式（供列印範本製作）。觸發：「PDF 轉 Word」「PDF 轉 Excel」「轉成範本」。"
argument-hint: "<PDF路徑> [--to word|excel] [--template] [--output <路徑>]"
model: sonnet
---

# PDF Converter — 高擬真 PDF 轉 Word / Excel

> 非 Claude Code（如 Pi）執行時，先讀 `../../references/harness-terms.md`（相對本檔；Claude Code 為 `${CLAUDE_PLUGIN_ROOT}/references/harness-terms.md`，照字面執行可略過），把 Claude 專屬工具與路徑換成對應項。

把 PDF 轉成 Word 或 Excel，目標是**版面與內容一模一樣**，並以機器量測的回轉驗證迴圈自證——不是「看起來像」，而是文字逐字元比對、版面座標量偏差、頁面渲染疊圖比對。

## 輸入參數

```
$ARGUMENTS → <PDF路徑> [--to word|excel] [--template] [--output <路徑>]
```

| 參數 | 必填 | 說明 |
|------|------|------|
| PDF 路徑 | 是 | 來源 PDF；空白則詢問後終止 |
| `--to` | 否 | 目標格式；省略時 Step 2 依內容推薦後詢問 |
| `--template` | 否 | 範本模式：轉出後把資料值逐欄確認改成 `{欄位}` 佔位符（列印範本製作用） |
| `--output` | 否 | 輸出路徑；省略時依「產出位置」規則決定（見下） |

## 產出位置（--output 省略時）


1. **PDF 屬於某功能**（SDLC 流程中呼叫、或能對應到 `{docs-root}/{模組}/{功能}/` 既有功能目錄）→ 輸出至**該功能 docs 目錄**（與 FRD／SAD 同目錄）；來源 PDF 不在 docs 內時一併複製進去。對應不確定就 `AskUserQuestion` 確認目錄——**只在既有目錄中選，不得自建 `{docs-root}` 第一階目錄**（`{docs-root}` 由專案 CLAUDE.md 設定，未設定為 `docs/`）。
2. **獨立呼叫且無對應功能** → 與來源 PDF 同目錄同名。

中間產物（layout.json、diff PNG、verify-report）一律在 `.tmp/pdf-converter/{檔名}/`，不進 docs。

## 核心原則

1. **萃取與驗證腳本化、生成由 AI 撰寫**——`scripts/` 兩支腳本是確定性量測工具；生成程式碼由 AI 依 layout.json 現場撰寫（任意版型都能處理），生成結果一律回到腳本驗證，形成閉環。
2. **不猜測**：字型對映、欄位語意不確定時，先查 layout.json 證據，再 `AskUserQuestion`（一次一題、附建議）。
3. **驗證未過不交付**：門檻定義見 `references/verify-thresholds.md`；硬門檻不過必須重做，軟門檻超標交 `doc-fidelity-reviewer` 判定。

## 執行環境

- `<PY>` = 本機 python 直譯器。**不要寫死 `python`**：macOS 只有 `python3`，Windows Git Bash 多半只有
  `python`。用 `command -v python || command -v python3` 取存在的那個。
- 依賴套件：`pymupdf`（`import fitz`）、`python-docx`（`import docx`）、`openpyxl`、`pillow`（`import PIL`）。
  **開跑前先驗**，缺哪個就先備妥，不要跑到一半才炸：
  ```bash
  <PY> -c "import fitz, docx, openpyxl, PIL"    # 無輸出＝齊全，可直接開跑
  ```
  缺套件時**優先用 `uv` 開專用環境**，並把後續的 `<PY>` 改指該環境：
  ```bash
  uv venv ~/.venvs/pdf-converter
  uv pip install --python ~/.venvs/pdf-converter/bin/python pymupdf python-docx openpyxl pillow
  # 之後 <PY> = ~/.venvs/pdf-converter/bin/python
  ```
  ⚠ **不要往 macOS 的 `/usr/bin/python3` 裝**——那是 Apple 隨 Command Line Tools 附的
  Python 3.9（pip 21.x），是系統元件不該污染，版本也偏舊。`command -v python3` 在 mac 上
  預設就命中它，所以這一步不能省。無 `uv` 時退而求其次用 `<PY> -m pip install --user`。

## 執行流程（六步）

### Step 1：來源盤點

```bash
<PY> -B {skill_dir}/scripts/pdf_extract.py <PDF> --probe
```

檢查項：`encrypted`（加密 → 提示解密後終止）、`verdict`：

| verdict | 處理 |
|---------|------|
| `text_layer_ok` | 正常路徑，繼續 Step 2 |
| `scanned` / `partial_scanned` | **降級路徑**：告知使用者無文字層頁面清單，`AskUserQuestion` 確認是否接受「AI 視覺辨識重建（未經文字層驗證）」；接受 → 走 Step 3 降級分支，產出全程標注 ⚠️ 未經文字層驗證 |

### Step 2：目標格式判斷

`--to` 已指定則跳過。未指定時依 probe 結果推薦（表格佔版面主體 → Excel；一般文件版面 → Word），`AskUserQuestion` 確認，推薦置首。

### Step 3：完整萃取

```bash
<PY> -B {skill_dir}/scripts/pdf_extract.py <PDF> --out {工作目錄}/layout.json --images-dir {工作目錄}/imgs
```

工作目錄用 `.tmp/pdf-converter/{檔名}/`（gitignored，用完可刪）。layout.json 含每頁：文字 span（文字/座標/字型/字級/粗斜體/色彩）、表格結構（格線儲存格＋文字）、線條與矩形（邊框樣式還原用）、圖片（檔案＋座標）。

**降級分支（掃描頁）**：`--render-dir` 把頁面渲染成 PNG，AI 讀圖重建版面與文字；後續驗證只做視覺軸，文字軸標注「未經文字層驗證」。

### Step 4：生成

讀 `references/generation-guide.md` 後，AI 依 layout.json 撰寫生成腳本（放工作目錄）執行：

- **Word**（python-docx）：頁面尺寸與邊界照 layout 換算、字型逐一對映（CID 字型名 → 實際中文字型，不確定就問）、表格邊框依 drawings 線寬還原、座標定位靠表格框架與段落間距逼近。
- **Excel**（openpyxl）：表格結構 → 儲存格（含合併格）、欄寬依 bbox 換算、邊框/字型/對齊還原；表格外的散落文字放對應位置的儲存格並註記。

### Step 5：驗證迴圈（最多 3 輪）

```bash
# Word：回轉三軸比對（需本機 Office；偵測不到 Word COM → 降級只驗文字軸並明告）
<PY> -B {skill_dir}/scripts/verify_roundtrip.py word --original <PDF> --docx <輸出> --outdir {工作目錄}/verify
# Excel：逐儲存格值比對
<PY> -B {skill_dir}/scripts/verify_roundtrip.py excel --layout {工作目錄}/layout.json --xlsx <輸出> --outdir {工作目錄}/verify
```

| verdict | 處理 |
|---------|------|
| `pass` | 進 Step 6 |
| `hard_fail`（文字/儲存格值不一致） | 依 verify-report 的 missing/extra 清單修正生成腳本，重生成再驗 |
| `soft_fail`（座標 >2mm 或視覺 ≥3%） | 派 `doc-fidelity-reviewer`（附 verify-report.json 與 diff PNG 路徑）→ 依回傳的修正指示改生成腳本重跑；reviewer 判定為「可接受的渲染差異」則放行並記入收尾報告 |

3 輪仍未過 → 停止迭代，列出殘餘差異（附 diff PNG）交使用者裁決（`接受現狀交付` / `指出修正方向繼續`）。

**範本模式註**：`--template` 時 Step 5 加 `--text-mode report-only`（佔位符與原值不同屬預期，文字軸只回報不判定），版面與視覺軸照常把關。

### Step 5.5：範本模式（僅 --template）

Word 轉換通過驗證後：

1. 從 layout.json 區分「標籤文字」（欄名、固定文案）與「資料值」（會隨單據變動的內容）。
2. 逐欄 `AskUserQuestion` 確認佔位符名稱（一次一題，建議名稱置首；可參照既有範本的命名慣例——使用者有提供參照範本時以其為準）。
3. 資料值替換為 `{佔位符}`；明細表保留一列佔位符列，其餘資料列刪除。
4. 重跑 Step 5（report-only）確認替換未破壞版面。

### Step 6：收尾報告

- 輸出檔絕對路徑＋驗證統計（文字一致率／anchor 最大偏差 mm／視覺差異率／迭代輪數）。
- 降級路徑或 reviewer 放行的軟門檻超標項，逐項列出並標注。
- diff PNG 與 verify-report.json 留在工作目錄供查驗，提醒用完可刪。

## 錯誤處理

| 情境 | 處理 |
|------|------|
| PDF 路徑空白或不存在 | 提示後終止 |
| PDF 加密 | 提示解密後終止 |
| 全頁掃描且使用者拒絕降級 | 終止，說明不做 OCR 的原因（辨識錯字造成假精確） |
| Word COM 不可用（無 Office） | Word 模式降級：跳過回轉，只以 docx 內文比對文字軸，明告「版面與視覺驗證未執行」 |
| 3 輪驗證未過 | 停止迭代，附 diff 證據交使用者裁決 |

## References

- [generation-guide.md](references/generation-guide.md) — python-docx／openpyxl 版面重建技法（頁面設定、字型對映、邊框、合併格）
- [verify-thresholds.md](references/verify-thresholds.md) — 三軸門檻定義、差異分級與 reviewer 判定準則
