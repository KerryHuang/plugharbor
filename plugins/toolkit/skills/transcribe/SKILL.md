---
name: transcribe
description: 在本機背景錄音（麥克風），或把錄音檔轉成帶時間戳的逐字稿 Markdown：Mac（Apple Silicon）用 mlx-whisper，Windows／其他平台用 faster-whisper，中文輸出經 OpenCC 轉台灣繁體。不上雲端、不分講者。Use when 使用者說「轉逐字稿」「語音轉文字」「錄音轉文字」「開始錄音」「transcribe」，或給一個音檔／影片檔要文字內容。
argument-hint: "<音檔路徑>|record [--out <md>] [--prompt-file <術語檔>]"
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

## 錄音（麥克風）

1. **開錄前先問使用者是否已告知在場的人要錄音**。麥克風會收到現場所有人的聲音，沒確認就不開錄。
2. 環境：`doctor --record`（錄音需要 ffmpeg，Windows 也要）。Windows 要指定 `--device`，先用 `record devices` 列出名稱讓使用者選；Mac 不帶就用系統預設輸入。
3. 開錄：`transcribe.py record start --out "<目錄>" [--device <名稱>] [--segment-sec 300]`。指令會在背景啟動 ffmpeg 後立刻返回，每段寫一個 `seg-NNN.wav`。
   - 出現「幾乎是靜音」警告時，轉述給使用者確認裝置與麥克風權限，不要默默繼續。
   - exit 2＝這個目錄已在錄；exit 3＝沒啟動成功（附 ffmpeg log 尾段）。
4. 進行中可用 `record status --out "<目錄>"` 查已錄時間。錄音與 Claude session 脫鉤：session 中斷時錄音繼續，新 session 對同一目錄 `record stop` 即可。
5. 使用者說散會才停：`record stop --out "<目錄>"`，會合併成 `<目錄>/recording.wav`（exit 4＝沒有任何分段）。再用上面的 `transcribe` 轉 `recording.wav`。
6. **不要自行讀取或轉錄使用者沒要求的錄音內容**；測試錄音用完即刪。

## Exit code

| code | 意思 |
|---|---|
| 0 | 成功 |
| 2 | 參數問題（找不到音檔、輸出已存在） |
| 3 | 環境缺件（ffmpeg、OpenCC） |
| 4 | 未偵測到語音（不產生檔案） |

## 不做

講者辨識、雲端轉錄、線上會議的系統音訊擷取與會中即時轉錄（之後的版本才有）。
