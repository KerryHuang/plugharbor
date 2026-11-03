---
name: transcribe
description: 在本機把錄音檔轉成帶時間戳的逐字稿 Markdown：Mac（Apple Silicon）用 mlx-whisper，Windows／其他平台用 faster-whisper，中文輸出經 OpenCC 轉台灣繁體。不上雲端、不分講者。Use when 使用者說「轉逐字稿」「語音轉文字」「錄音轉文字」「transcribe」，或給一個音檔／影片檔要文字內容。
argument-hint: "<音檔路徑> [--out <md>] [--prompt-file <術語檔>]"
---

# 語音轉逐字稿

一支腳本 `${CLAUDE_PLUGIN_ROOT}/skills/transcribe/scripts/transcribe.py` 做完全部，你只負責執行它和轉述結果。不要自己寫轉錄程式碼。

## 執行

1. **先檢查環境**：`python3 ${CLAUDE_PLUGIN_ROOT}/skills/transcribe/scripts/transcribe.py doctor`
   - exit 0：繼續。
   - exit 1：把輸出中標 `NG` 的項目和安裝指令轉述給使用者，**問過才裝**，不自行安裝。
2. **轉錄**：

   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/transcribe/scripts/transcribe.py transcribe "<音檔>" --out "<輸出.md>" [--prompt-file "<術語檔>"] [--model large-v3-turbo] [--language zh]
   ```

   - 輸出檔預設放在音檔旁、同名 `.md`；已存在時腳本會拒絕，要覆寫先問使用者再加 `--force`。
   - `--prompt-file`：純文字，一行或空白分隔的專有名詞（人名、產品名、行話），提高辨識率。
   - 長音檔可能跑數十分鐘，用背景執行並告知使用者預估時間。
3. **回報**：輸出路徑、段數；非 0 結束時原文轉述 stderr，不重試同一指令。

## Exit code

| code | 意思 |
|---|---|
| 0 | 成功 |
| 2 | 參數問題（找不到音檔、輸出已存在） |
| 3 | 環境缺件（ffmpeg、OpenCC） |
| 4 | 未偵測到語音（不產生檔案） |

## 不做

講者辨識、雲端轉錄、即時錄音（之後的版本才有）。
