# 影片腳本格式（`video.mjs`）

ESM 模組，`export default` 一個物件。虛構範例見 `../examples/leave-request/video.mjs`。

```js
export default {
  name: 'leave-request',                    // 輸出檔名（out/<name>.mp4 / .srt）。預設 'video'
  base: 'http://127.0.0.1:5190/',           // 被錄的站。可用 --base 覆寫
  voice: 'zh-TW-HsiaoChenNeural',           // 預設語音聲音
  viewport: { width: 1280, height: 720 },   // 必須是 16:9；輸出一律縮放成 1920×1080
  locale: 'zh-TW',
  gapMs: 450,                               // 每段語音結束後再留的間隔
  timeoutMs: 8000,                          // 每個動作等元素的上限
  subtitleFont: "'PingFang TC',...",        // 字幕字型；系統沒有預設字型時要換
  tts: async (text, outFile, { voice }) => {},   // 選用：換語音來源，必須寫出 outFile（.mp3）
  setup: async (page, actor, url) => {},    // 選用：開始錄影前的準備（登入、導到起始頁）。預設 page.goto(url)
  segments: [
    { text: '一句旁白。', run: async (a) => { /* 操作 */ } },
  ],
}
```

`build` 開始前會先檢查 `name`、`base`、`viewport`、`tts`、`setup`、`segments`（`lib/validate-script.mjs`），一次列出全部錯誤和正確範例後 exit 1，不動輸出目錄。改這裡的欄位時要同步該檔。

## 操作員 `a`

| 方法 | 做什麼 |
|---|---|
| `a.p` | Playwright `page`，用來定位元素與等條件 |
| `a.pause(ms)` | 純等待（讓畫面停著，配合旁白） |
| `a.move(loc)` / `a.hover(loc)` | 游標移到元素中心（約 0.5 秒），換頁後游標位置保留 |
| `a.click(loc)` | 移游標＋點擊漣漪＋點擊 |
| `a.type(loc, text)` | 點進欄位後逐字輸入（觀眾看得到打字） |
| `a.fill(loc, value)` | 點進欄位後一次填入（日期、很長的值） |

`loc` 是 Playwright locator，例如 `a.p.getByRole('button', { name: '儲存', exact: true })`。
錄影畫面沒有系統游標，所以一律用 `a.*` 操作，不要直接 `loc.click()`（觀眾會看到畫面自己動）。
下拉選單等 `a.*` 沒涵蓋的動作，先 `a.click(...)` 讓游標到位，再用 `a.p` 做。

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
