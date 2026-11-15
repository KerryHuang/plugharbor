# 踩過的坑與除錯

這些都是實際做影片時踩到的，引擎已處理的標「引擎」，需要腳本作者注意的標「作者」。

## 影片與聲音

1. **靜止畫面讓影像軌提早結束**（引擎）。螢幕沒有變化就沒有新影格，影像軌會比音軌短。曾發生影像 52.8 秒、音軌 64 秒：
   播放器到 53 秒就沒聲音，但容器長度仍顯示 64 秒，用 `ffprobe format=duration` 完全看不出來。
   引擎用 `tpad=stop_mode=clone` 加 `trim` 把影像補到全片長，驗證時**分別**量影像軌與音軌長度，不符就報錯。
   不要自己改成只看容器長度。端到端測試（`scripts/e2e.test.mjs`）拿掉 `tpad` 會失敗。
2. **ffmpeg 可能沒有 libass／drawtext**（引擎）。Homebrew 版就沒有。字幕由瀏覽器渲染成透明 PNG，再用 `overlay=enable='between(t,a,b)'` 疊上，所以不需要這兩個 filter。字型找不到時改 `subtitleFont`。
3. **畫面沒有游標**（引擎）。無頭瀏覽器的畫面沒有滑鼠，引擎注入游標與點擊漣漪，換頁後位置保留。作者：操作要放慢，用 `a.type` 逐字輸入。
4. **畫面靜止時沒有第一格**（引擎）。開始錄影後先動一下游標才取得第一格，否則 `frames[0]` 不存在。
5. **語音檔尾端自帶約 1 秒靜音**（作者）。段落間隔已經夠，`gapMs` 維持 450 左右。
6. **時間軸以實際錄影為準**（引擎）。操作比語音長就印 `OVER`（作者要處理）；字幕切句按標點、時間按字數估算，只是估算。

## 選擇器與頁面

7. **選擇器要精確**（作者）。寬鬆 regex 曾點到錯的按鈕（「新增」點到「新增條件」）；有些按鈕其實是連結，`getByRole('button')` 找不到。
   用 `{ name: '新增', exact: true }`，必要時用 `locator('a')`、`getByRole('link')`。失敗時引擎會截圖 `out/fail.png`，印網址與畫面文字——**先看這兩樣再改**，不要憑感覺換選擇器重試。
8. **有些 UI 框架的下拉選單是浮層**，選項不在原本欄位底下：先點開，再到浮層容器裡找選項文字。

## 起 server

9. **應用程式的埠可能不受環境變數控制**。以 ASP.NET Core 為例，曾發生 `ASPNETCORE_URLS` 設了卻沒生效，影片錄到另一個程序的頁面。
   **起 server 後先看實際在聽的埠**（`lsof -iTCP -sTCP:LISTEN -P | grep <程序>`），確認 `--base` 指到自己起的那個，再錄影。
   預設埠被占用時停下來，不要直接錄。
10. 用**全新的本機資料庫**；起 server 的腳本記下 PID，收尾 `kill <PID>`，不用 `pkill`、不關別人的程序。範例：`examples/leave-request/run.sh`。

## 環境

- 找不到 playwright-core：引擎讀的是**目前目錄**的 `node_modules`，要在工作目錄下執行。
- 找不到 Chrome：安裝 Google Chrome，或把 `CHROME_PATH` 設成 Chrome／Chromium 執行檔（有設就一律用它，且 `ensure-tools.sh` 只認它）。沒設時引擎用系統安裝的 Chrome（`channel: 'chrome'`），單獨裝的 Chromium 不在 PATH 上被自動採用。不下載瀏覽器、不用 Playwright 的 recordVideo。
- `uvx edge-tts` 失敗：多半是沒有網路或服務暫時拒絕，重跑；持續失敗改用 `tts` 換語音來源。
