# 影片腳本格式（`video.mjs`）

ESM 模組，`export default` 一個物件。虛構範例見 `../examples/leave-request/video.mjs`。

```js
export default {
  name: 'leave-request',                    // 輸出檔名（out/<name>.mp4 / .srt）。預設 'video'
  base: 'http://127.0.0.1:5190/',           // 選填：被錄的站。有 video/env.mjs 就不用寫；--base 優先，且完全不碰配方
  voice: 'zh-TW-HsiaoChenNeural',           // 預設語音聲音
  viewport: { width: 1280, height: 720 },   // 必須是 16:9；輸出一律縮放成 1920×1080
  locale: 'zh-TW',
  gapMs: 450,                               // 每段語音結束後再留的間隔
  timeoutMs: 8000,                          // 每個動作等元素的上限
  subtitleFont: "'PingFang TC',...",        // 字幕字型；系統沒有預設字型時要換
  tts: async (text, outFile, { voice }) => {},   // 選用：換語音來源，必須寫出 outFile（.mp3）
  setup: async (page, actor, url) => {},    // 選用：開始錄影前的準備（登入、導到起始頁）。預設 page.goto(url)；url 是引擎起站的實際網址
  segments: [
    { text: '一句旁白。', run: async (a) => { /* 操作 */ }, expect: '已送出' },  // expect 選填
  ],
}
```

`build` 開始前會先檢查 `name`、`base`（有配方或 `--base` 時可省略）、`viewport`、`tts`、`setup`、`segments`（`lib/validate-script.mjs`），一次列出全部錯誤和正確範例後 exit 1，不動輸出目錄。改這裡的欄位時要同步該檔。

## 操作員 `a`

| 方法 | 做什麼 |
|---|---|
| `a.p` | Playwright `page`，用來定位元素與等條件 |
| `a.pause(ms)` | 純等待（讓畫面停著，配合旁白） |
| `a.move(loc)` / `a.hover(loc)` | 游標移到元素中心（約 0.5 秒），換頁後游標位置保留 |
| `a.click(loc)` | 移游標＋點擊漣漪＋點擊 |
| `a.type(loc, text)` | 點進欄位後逐字輸入（觀眾看得到打字） |
| `a.fill(loc, value)` | 點進欄位後一次填入（日期、很長的值） |
| `a.upload(按鈕, 檔案)` | 先等 filechooser，再點按鈕，最後 setFiles；相對路徑以影片目錄（`video.mjs` 所在處）為準 |
| `a.select(欄位, 選項)` | 點欄位（字串當標籤用 `getByLabel`），在最後一個浮層容器裡點選項文字。容器預設 `[role=listbox]`，可用配方 `ui.menu` 改。原生 `<select>` 不是浮層，用 `a.click` 加 `selectOption` |
| `a.as(userId, 路徑?)` | 呼叫配方的 `login(page, userId)` 換身分，再跳到 `路徑`（相對目前網址；省略就重新載入）。畫面是直接跳頁，不演示登入；要演示登入就用 `a.click`。配方沒寫 `login` 會報「配方沒有 login，不能用 a.as」 |

`loc` 是 Playwright locator，例如 `a.p.getByRole('button', { name: '儲存', exact: true })`。
錄影畫面沒有系統游標，所以一律用 `a.*` 操作，不要直接 `loc.click()`（觀眾會看到畫面自己動）。
下拉選單等 `a.*` 沒涵蓋的動作，先 `a.click(...)` 讓游標到位，再用 `a.p` 做。

## 每段的 `expect`

選填。`expect` 是文字（`page.getByText(文字).first()`）或函式 `(a) => locator`；操作做完時等它出現，沒出現就跟操作失敗一樣處理：停下來、留 `out/fail.png`，並印「expect 未符合：<文字>」。
用來擋住「操作沒報錯但畫面不對」，例如送出後沒出現成功訊息。

## 錄影環境配方（`video/env.mjs`）

放在影片目錄的上一層（`video/env.mjs`，影片在 `video/<名稱>/video.mjs`），進版控，專案共用。範例見 `../examples/env.mjs`。腳本沒寫 `base` 也沒給 `--base` 時，引擎用它起站；找不到配方就失敗退出。

| 欄位 | 必填 | 說明 |
|---|---|---|
| `build({ root, sh })` | 是 | 建出可執行的站台；產物已存在就自己跳過。靜態頁留空函式 |
| `reset({ dataDir, sh, env })` | 是 | 清空資料並重新產生 Demo 資料；每次 build、dry-run、env-check 都會呼叫，成功後引擎印「reset 完成」。`dataDir` 是 `video/.data/`；`env` 含 `start.env` 與埠 |
| `start.cmd` | 是 | 字串（以空白切開）或字串陣列（路徑含空白時用陣列）。POSIX 以新的 process group 起站，`npm run`、`dotnet run` 這類啟動器形式也能判斷就緒，收站時整個 group 一起收；**Windows 只比對 pid，cmd 必須直接執行 server 本體** |
| `start.portEnv` | 是 | 引擎找空埠，用這個環境變數傳給 app（例如 `PORT`） |
| `start.readyPath` | 是 | 就緒檢查路徑。條件有兩個：聽這個埠的程序屬於引擎自己起的，而且這個路徑回 2xx |
| `start.cwd` | 否 | 相對於 `video/`，預設 `.` |
| `start.env` | 否 | 額外環境變數 |
| `start.port` | 否 | 偏好埠；被占用時改用空埠 |
| `start.readyTimeoutMs` | 否 | 等就緒的上限，預設 60000；逾時印「server 未就緒」與 `out/server.log` 路徑 |
| `login(page, userId)` | 否 | 給 `a.as` 用 |
| `ui` | 否 | `{ menu, dialog }`：浮層選擇器，預設用 ARIA role（`listbox`、`dialog`） |
| `tts` | 否 | `{ provider: 'edge', licensed: false }`，授權狀態寫進 MP4 metadata（見下） |

- 收尾：成功、失敗、Ctrl-C 都只關引擎自己起的程序（以 PID 或其 process group）。同一個 `video/` 同時只能跑一個引擎，第二個會印「已有一個 demo-video 在跑（pid <PID>）」後退出。
- 配音授權：預設 provider 是 `edge`。腳本自帶 `tts` 函式時，provider 一律記 `custom`；只有配方明確寫 `tts: { provider: 'custom', licensed: true }` 才標成已確認。MP4 comment 為 `配音：<provider 顯示名> <voice>，商用授權<已確認|未確認>`，未確認時 build 結尾印「對外發布前要確認配音授權」。
- 配音快取在 `video/.tts-cache/`（key 為文字、聲音、provider 的雜湊），旁白沒改就不重新配音。

## 時間軸怎麼算

- 每段開始時記下**實際**時間；音訊用 `adelay` 放到該時間，字幕用同一個時間。不是預先排程。
- 一段的實際長度 = max(操作耗時, 語音長度 + `gapMs`)。操作超過語音就印 `OVER`：旁白講完了畫面還在動，要縮短操作或把旁白加長。
- 語音檔尾端自帶約 1 秒靜音，所以 `gapMs` 不要設太大，否則段落間空白太久。
- 字幕按標點（`，。！？；`）切句，過長的句子再均分；每句的時間按字數分配，標點加權 2 個字。
  這是估算，不是語音辨識，**對得準不準要人試聽**。

## 換語音來源

```js
tts: async (text, outFile, { voice }) => {
  // 呼叫自己的 TTS，把音檔寫到 outFile（副檔名 .mp3；其他格式請轉成 mp3）
}
```
