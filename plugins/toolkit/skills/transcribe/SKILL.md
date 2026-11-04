---
name: transcribe
description: 在本機背景錄音（麥克風，或線上會議時連同系統播放的對方聲音）並可邊錄邊逐段轉錄，或把錄音檔轉成帶時間戳的逐字稿 Markdown：Mac（Apple Silicon）用 mlx-whisper，Windows／其他平台用 faster-whisper，中文輸出經 OpenCC 轉台灣繁體。不上雲端、不分講者。線上會議中還可加入會議 AI 顧問「小小」：有人說「嘿，小小，……」時用語音回答（Mac）。Use when 使用者說「轉逐字稿」「語音轉文字」「錄音轉文字」「開始錄音」「錄線上會議」「transcribe」「開小小」「會議顧問」，或給一個音檔／影片檔要文字內容。
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

## 線上會議（對方聲音＋邊錄邊轉）

目前只支援 Mac（macOS 14.2 以上、Python 3.11 以上、`pip install catap`）。Windows 尚未驗證，腳本會直接拒絕，請改用麥克風模式。

1. **開錄前先問使用者是否已告知所有與會者（含線上的對方）要錄音**，沒確認就不開錄。建議戴耳機：不戴的話喇叭聲會再被麥克風收一次，逐字稿可能出現重複句（已知限制）。
2. 環境：`doctor --record --source system`。它會印出系統錄音授權的步驟（查不到權限，只能提醒），轉述給使用者。
3. 開錄：`record start --out "<目錄>" --source both`（只錄對方用 `system`）。開錄時沒有靜音警告，因為還沒人講話是正常的。
4. 邊錄邊轉：`live start --out "<目錄>" [--prompt-file "<術語檔>"] [--language zh]`。每段錄完才轉，逐字稿追加到 `<目錄>/transcript.md`，每段結束寫一行 `<!-- seg-NNN done -->`，全部轉完寫 `<!-- live finished -->`。
5. 開錄後 1 到 2 分鐘跑 `record status --out "<目錄>"`：
   - 「對方聲音：尚未收到」：請使用者確認已授權、會議聲音從系統預設輸出播放。
   - 「逐字稿：已轉 N／M 段（落後）」：機器跟不上，轉告使用者。散會後 `live` 會在背景把剩下的轉完。
   - 「逐段轉錄已中止」：看 `<目錄>/live.log` 轉述原因，修好後再跑 `live start` 接續（不會重複追加）。某段寫 `<!-- seg-NNN failed -->` 表示那段轉錄失敗，事後可對 `recording.wav` 重轉。
6. 散會：`record stop --out "<目錄>"`，等 `transcript.md` 出現 `live finished`。`recording.wav` 照常產出。
7. 已知限制：會中切換輸出裝置（插拔耳機、AirPods 連線）後，可能收不到對方聲音。`status` 會顯示最近一次收到的時間，看到時間停住就提醒使用者。

## 會議 AI 顧問「小小」

在線上會議錄音（`--source both`）上加一個只在被點名時開口的顧問：有人說「嘿，小小，……」，它把最近 5 分鐘逐字稿和問題交給 `claude -p`，再用 `say` 把兩三句口語回答送進虛擬麥克風。腳本是 `${CLAUDE_PLUGIN_ROOT}/skills/transcribe/scripts/advisor.py`（以下簡寫 `advisor.py`，用跑 `record` 的同一個 python3 執行），只支援 Mac。

1. **一次性設定**（`advisor.py doctor` 缺什麼會印步驟）：
   - 安裝 BlackHole 2ch（`brew install --cask blackhole-2ch`，裝完 `sudo killall coreaudiod` 重啟音訊服務，不必重開機）。
   - 在「音訊MIDI設定」建立聚合裝置「小小麥克風」：先勾實體麥克風、再勾 BlackHole 2ch，時脈來源選實體麥克風。
   - 會議軟體的**麥克風**改選「小小麥克風」，喇叭維持原本的輸出。
   - 系統設定下載中文聲音「Meijia」。
2. **開會前**：`advisor.py doctor`。exit 1 時轉述 `NG` 項目；任何一項沒過就不啟動小小，會議照常只錄音。
3. **場合檔**：決定小小能用哪些工具、用哪個模型、人設。範例 `advisor-mode.example.json`；白名單只能放唯讀工具（含 `Write`、`Edit`、不限指令的 `Bash` 會被拒絕）。可加 `"cwd"` 指定它查資料的目錄、`"mcp_config"` 指定 MCP 設定檔；沒給就不載入任何 MCP。專案與本機設定裡預先允許的工具不會生效，小小只拿得到場合檔列出的工具。**開始前先問使用者是內部會議還是客戶會議**，再選對應的場合檔。
4. **啟動**：先照上一節開錄（`record start --source both`，可同時跑 `live start`），再
   `advisor.py start --out "<目錄>" --mode-file "<場合檔>" [--prompt-file "<術語檔>"] [--context-min 5]`。
   - exit 2：目錄沒在錄、錄音只有麥克風、場合檔不合格、術語檔含「小小」（會讓 Whisper 吐出整串「小小小」），或已有一個小小在跑。exit 3：沒啟動成功，附 `advisor.log` 尾段。
5. **會中**：`advisor.py status --out "<目錄>"` 看已回答、待補幾題。4 秒還沒答它會先說「我查一下。」；30 秒逾時說「這題我會後補在會議記錄。」並記為待補。思考或播放中又被叫一次會略過，記在 `advisor.md`。
6. **紀錄**：每次發言寫進 `<目錄>/advisor.md`（`### HH:MM:SS`、`- 問：`、`- 小小：`；待補多一行 `<!-- advisor pending -->`），與 `transcript.md` 分開，整理會議記錄時依時間合併。小小自己的聲音會被系統錄音錄進去，所以播放前後 1.5 秒內轉出的句子不比對喚醒詞、不放進上下文；`transcript.md` 裡那段合成語音的辨識結果在整理時以 `advisor.md` 原文為準。
7. 錄音停止後小小會自己結束；要提早下線用 `advisor.py stop --out "<目錄>"`。
8. 已知限制：只驗過合成語音（結果見 CHANGELOG），真人聲音經會議軟體的辨識率未驗證；喚醒要說「嘿，小小」，單說「小小」不算。

## Exit code

| code | 意思 |
|---|---|
| 0 | 成功 |
| 2 | 參數問題（找不到音檔、輸出已存在） |
| 3 | 環境缺件（ffmpeg、OpenCC） |
| 4 | 未偵測到語音（不產生檔案） |

## 不做

講者辨識、分我方／對方、雲端轉錄、Windows 系統音訊（尚未驗證）。
