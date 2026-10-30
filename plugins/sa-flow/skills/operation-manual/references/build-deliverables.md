# S8 產交付檔：指令與格式限制

> 由 `operation-manual` SKILL.md 的 S8 節指向。**要不要產、產哪種一律問使用者**，
> 那個決策在 SKILL.md；本檔是問完之後的執行細節。

## 指令

```bash
# 標準 PDF
<mkdocs 的 python> ${CLAUDE_PLUGIN_ROOT}/scripts/build-manual-pdf.py <手冊.md> <輸出.pdf>
${CLAUDE_PLUGIN_ROOT}/scripts/build-deck.sh <簡報.md> <.tmp 下的輸出目錄>   # 同時出 PDF 與 PPTX

# Office 系列
${CLAUDE_PLUGIN_ROOT}/scripts/build-manual-docx.sh <手冊.md> <輸出.docx>
${CLAUDE_PLUGIN_ROOT}/scripts/build-deck.sh <簡報.md> <.tmp 下的輸出目錄>   # PPTX 與上面同一支
```

`<mkdocs 的 python>` 由 `ensure-tools.sh` 偵測後寫在 `scripts/.python-path`。

**產出一律落 `.tmp/`，不進版控。** 使用者只要 PDF 時，`build-deck.sh` 仍會一起產 PPTX，產完刪掉即可。

## 簡報溢出檢查

`build-deck.sh` 產完 PDF 會**自動跑** `check-deck-overflow.py`：內容侵入頁尾帶就列出頁碼。
列出的頁要開 PDF 確認，確認溢出就退回 S5，不交付。單獨跑：

```bash
<python> ${CLAUDE_PLUGIN_ROOT}/scripts/check-deck-overflow.py <簡報.pdf>   # 結束碼 0 無溢出｜1 有溢出｜2 無法檢查
```

需要 PyMuPDF 或 pdftoppm（poppler）其中之一；兩者都沒有會回報「無法檢查」，不要當成通過。

## 頁碼

PDF 與 Word 輸出**一律自動蓋頁碼**（置中「第 N 頁，共 M 頁」），不必也不要手動補。
PDF 由 `build-manual-pdf.py` 產出後用 PyMuPDF 逐頁蓋章；Word 由 `manual-reference.docx`
內建的頁尾 PAGE/NUMPAGES 欄位提供，開檔時自動算好。**簡報（Marp）本來就有頁碼，這條只補
非簡報版**——曾發現交付的 PDF 全數缺頁碼，才在此修好產線。

## 兩個要先告知使用者的限制

- **PowerPoint 每頁是一張圖片，文字不能編輯**（Marp 的限制）。
  適合播放與存檔；客戶要自己改內容就不能用這條路。
- **Word 的樣式已範本化**，視覺對齊 PDF：章標題藍字＋下邊框、節標題左色條、
  步驟標題淺藍底、說明區塊黃底左橘條、表格藍表頭白字、內文 PingFang TC。
  樣式由 `scripts/manual-reference.docx` 控制，該檔由 `make-docx-reference.py` 生成並隨 plugin 提供——
  要調樣式改那支腳本再重新生成，不要手改 docx。
  仍與 PDF 有差的是分頁控制（Word 沒有 `break-inside: avoid`，長表格與圖片
  可能被切到下一頁）與封面（docx 無自訂封面頁）。
