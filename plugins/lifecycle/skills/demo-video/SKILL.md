---
name: demo-video
description: "把旁白加操作步驟的腳本錄成有配音、字幕的操作示範影片（MP4＋SRT）。觸發：「做操作示範影片」「錄 demo 影片」「旁白影片」「教學影片」。"
argument-hint: "<影片名稱> <要示範的網址>"
---

# Demo Video — 操作示範影片

> 非 Claude Code（如 Pi）執行時，先讀 `../../references/harness-terms.md`（相對本檔；Claude Code 為 `${CLAUDE_PLUGIN_ROOT}/references/harness-terms.md`，照字面執行可略過），把 Claude 專屬工具與路徑換成對應項。

輸入一份「旁白＋操作步驟」腳本，產出配音、字幕、可直接播放的 MP4，以及 SRT。
要的是**文件型的操作手冊**用 `lifecycle:operation-manual`（截圖＋文字）；要**影片**才用本 skill。

引擎目錄 `ENGINE="${CLAUDE_PLUGIN_ROOT}/skills/demo-video/scripts"`（下稱 `$ENGINE`；路徑可能含空白，指令裡一律加引號）。腳本格式見
[script-format.md](references/script-format.md)，踩過的坑與除錯見 [troubleshooting.md](references/troubleshooting.md)，
驗證細節見 [verification.md](references/verification.md)，虛構範例在 `examples/leave-request/`。

## ⚠ 先看這三件事

1. **Edge TTS 不是正式授權的 API。** 預設語音走 `uvx edge-tts`（聲音 `zh-TW-HsiaoChenNeural`），商用條款未確認。
   **影片要對外發布（客戶、公開網站、行銷）前，先查清楚授權，或在影片腳本用 `tts` 換成付費語音。**
   另外旁白文字會送到外部服務，內容涉機密時一樣先換語音來源。
2. **AI 聽不到聲音。** agent 只能量音量與看畫面；語音品質、發音、斷句、字幕與聲音對不對得上，
   **一定要由使用者試聽**。驗證做完的回報狀態是「⏳ 等使用者試聽」，**不是完工**。
3. **產品資料隔離。** 錄影在使用者指定的網址進行：用**全新的本機資料庫**起一份，不要在線上站、測試站、客戶站操作
   （會留下假資料，影片還會露出真實資料）。只關**自己起的**程序，不碰別人開的 server 或瀏覽器。

## 製作順序（固定，不跳步）

```
1 寫稿 → 2 使用者審稿 → 3 配音 → 4 依語音長度錄操作 → 5 字幕 → 6 合成 → 7 驗證 → 8 使用者試聽
```

3～7 由引擎一次跑完（`build`），1、2、8 是人與 agent 的關卡。**不要審稿前就配音**：改一句稿就要整批重配、重錄。

### 0. 工作目錄與工具

工作目錄放在專案的 `.tmp/demo-video/<影片名稱>/`（不進版控）；Node 依賴只裝在這裡，不全域安裝：

```bash
bash "${CLAUDE_PLUGIN_ROOT}/skills/demo-video/scripts/ensure-tools.sh" --dir "<工作目錄>"
```

檢查 Chrome、node、ffmpeg、uvx，並在工作目錄安裝 `playwright-core`（用系統 Chrome，或 `CHROME_PATH` 指定的 Chromium 系執行檔；不下載瀏覽器）。
缺工具而無法自動裝時，把缺什麼告訴使用者，由使用者決定怎麼處理。

### 1. 寫稿

在工作目錄寫 `video.mjs`（格式見 [script-format.md](references/script-format.md)）：**每段一句旁白＋一組操作**。

- 旁白口語、一句講一件事（約 20～40 字）；一句話裡的標點會切成字幕，標點用全形。
- 操作要放慢：用 `a.type` 逐字輸入、`a.click` 先移游標再點；一段操作約 3～6 秒，長的拆段。
- **選擇器要精確**：用 `getByRole('button', { name: '新增', exact: true })` 這類；寬鬆 regex 會點到別的（例如「新增」點到「新增條件」），
  有些看起來像按鈕的其實是連結（`a`），role 不同。先用 `live-drive` 或瀏覽器看過真實 DOM 再寫。
- 版面：字幕壓在畫面**底部約 130px**，會蓋住那裡的 UI；示範的重點區域留在上方。

### 2. 使用者審稿

把旁白稿（每段一句，附對應操作一行摘要）給使用者審。用 AskUserQuestion 問：稿 OK／要改哪段。
**使用者確認前不配音、不錄影。**

### 3～7. 跑引擎

先準備好被錄的站（全新本機資料庫，見上面第 3 點與 troubleshooting 的「起 server」），再：

```bash
cd <工作目錄>
node "$ENGINE/demo-video.mjs" build video.mjs --out out [--base <網址>]
```

引擎依序做：配音 → 依**每段語音長度**錄操作（操作比語音長時印 `OVER`，該段要縮短操作或加長旁白）→
字幕（由旁白稿切句估時，不做語音辨識）→ 合成 → 驗證。成品：

| 檔案 | 內容 |
|---|---|
| `out/<name>.mp4` | 有配音、字幕燒進畫面（1920×1080） |
| `out/<name>.srt` | 同一份字幕，時間與影片一致 |
| `out/verify/contact.jpg` | 驗證用 contact sheet |
| `out/timeline.json` | 每段實際起訖時間（除錯用） |

某段操作失敗時引擎會截圖到 `out/fail.png`、印網址與畫面文字後結束：照畫面文字修選擇器再重跑。
只想重跑驗證：`node "$ENGINE/demo-video.mjs" verify out`。

### 7. 驗證（agent 必做，逐項回報）

引擎的 `build` 已機器檢查前兩項；**第三項要 agent 自己開圖看**。細節見 [verification.md](references/verification.md)。

| 項目 | 怎麼驗 | 沒做到 |
|---|---|---|
| 影像軌、音軌長度 | 引擎分別量兩條軌，不看容器長度；與預期不符就報錯 | 標「未驗證」 |
| 每段旁白有聲音 | 引擎對每段時間區間跑 `volumedetect`，靜音就報錯 | 標「未驗證」 |
| 畫面內容 | 用 Read 開 `out/verify/contact.jpg`，逐格對照旁白：畫面是不是該段在講的、字幕有沒有蓋到重點、有沒有錯誤畫面 | 標「未驗證」 |
| 語音品質／發音／字幕對齊 | **只有人能驗** | 一律標「未驗證，待使用者試聽」 |

### 8. 回報：等使用者試聽

回報成品路徑、各驗證項目的結果（四項分開寫），結尾狀態是 **⏳ 等使用者試聽**（誰：使用者；聽什麼：發音、語速、字幕時間點）。
使用者提出要改的地方 → 回到第 1 步改稿或選擇器，只重跑 `build`。**使用者說可以了才算完工。**

## 收尾

- 只關自己起的 server／瀏覽器程序（用記下的 PID，不用 `pkill`）；回報時列出工作目錄中可清的暫存（`out/frames`、`out/caps`、`out/voice`、`node_modules`），不自行刪除。
- 影片要對外發布 → 回到上面第 1 點：授權先確認。
