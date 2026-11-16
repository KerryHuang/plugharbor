# demo-video 優化設計

| 項目 | 內容 |
|---|---|
| 日期 | 2026-11-16 |
| 版本 | 1.1.0 |
| 狀態 | 設計已與使用者討論定案 |
| 規格檢查 | ✅ 2026-11-16（版本 1.1.0） |
| 範圍 | `plugins/delivery/skills/demo-video`（SKILL.md、references、scripts、examples） |

## 1. 背景

demo-video 第一次實戰是在 dynamic-fields-design（Formwright），做了兩支影片：任務管理（93 秒）、純任務版設計需求（91 秒）。成品過了機器驗證，但製作過程的摩擦集中在三處：

| 摩擦 | 實際發生 |
|---|---|
| 起站與重置 | 起站、重置腳本都是臨時手寫。`ASPNETCORE_URLS` 沒生效，app 實際聽 5180；後來 5180 被另一個 session 的開發 server 佔走，健康檢查打到對方，被誤判為「就緒」。每次重跑前都要手動重置資料庫，不然上一輪建的資料會留在畫面上。 |
| 選擇器試錯 | 每支影片另外寫了 2～3 個 probe 腳本看 DOM。每次選擇器錯都要重置資料庫、整支重跑：每輪約 2 分鐘，其中重新配音約 20 秒、等語音約 60 秒。兩支影片合計失敗 4 輪。 |
| 操作超時（OVER） | 旁白審完才發現操作比旁白長，這時改旁白要重新送審，只能硬壓操作。換人（登出再點帳號，每次約 3 秒）是主因；上傳要自己寫 filechooser，浮層下拉要自己寫 `.q-menu`。 |

另外有幾個次要問題：

- 工作目錄 `.tmp/` 在這個 repo 沒有被 git 忽略。
- 專案原本有 `video/pilot` 的慣例，SKILL 的預設跟它衝突。
- 本機程式碼版本不對，臨時開了 worktree，結果成品放在 worktree 裡，有跟著被刪掉的風險。
- 回報時影片長度和製作時間沒分開寫，使用者誤會成影片要 40～50 分鐘。
- 配音授權的狀態只靠 agent 記得提醒。

## 2. 目標與非目標

**目標**

- 起站、重置、埠驗證由引擎負責。專案只要寫一次配方。
- 選擇器錯誤在 30 秒內回饋，不用配音、不用錄影。
- 操作是否超時，在審稿階段就看得到。
- 腳本和素材進版控，成品不會隨暫存目錄消失。

**非目標**

- `--from segN`（從第 N 段接著錄）：前面的段落會改資料，要從中間開始，得先把前段重播一次，錄影也得接起來，複雜度高。有了快速的 dry-run，整支重播已經夠便宜。
- 引擎自動開 worktree 或切換分支：這會動到使用者的工作區，交給 SKILL 流程詢問使用者。
- 引擎綁定特定 UI 框架或後端技術：框架和後端的細節都放在專案的配方裡。

## 3. 設計

### 3.1 目錄配置（使用者已拍板：`video/` 進版控）

```
video/
├── env.mjs                 ← 錄影環境配方（進版控，專案共用）
├── <影片名稱>/
│   ├── video.mjs           ← 腳本（進版控）
│   ├── files/              ← 要上傳的素材（進版控）
│   └── out/                ← 成品與中間檔（不進版控）
```

- 原本預設 `.tmp/demo-video/<名稱>/`，改為 `video/<名稱>/`。專案已有其他慣例時沿用既有的，SKILL 第 0 步要先看。
- `ensure-tools` 檢查 `video/**/out/`、`video/.build/`、`video/.data/`、`node_modules/` 有沒有被 git 忽略。沒有就印出要補的 `.gitignore` 行。只提示，不自動改。
- Node 依賴裝在 `video/`（共用一份），不再每支影片各裝一份。

### 3.2 錄影環境配方 `video/env.mjs`

```js
export default {
  // 建出可執行的站台；產物已存在就跳過（--rebuild 強制）
  build: async ({ root, sh }) => {},
  // 清空資料並重新產生 Demo 資料；每次 build、dry-run 前都會呼叫
  reset: async ({ dataDir, sh, env }) => {},
  start: {
    cmd: 'dotnet App.dll', cwd: '.build/app',
    portEnv: 'PORT',                      // 引擎找空埠，用這個環境變數傳給 app
    env: { Demo__LoginEnabled: 'true' },
    readyPath: '/api/health/ready',
  },
  login: async (page, userId) => {},      // 選填：a.as() 換人用
  ui: { menu: '.q-menu', dialog: '.q-dialog' }, // 選填：預設用 ARIA role（listbox、dialog）
  tts: { provider: 'edge', licensed: false },   // 見 3.7
}
```

- `dataDir` 由引擎給，在 `video/.data/`。`env` 是引擎組好的環境變數，包含 `start.env` 與埠。
- 埠：引擎自己找空埠，不用固定埠，從根本避開跟其他 session 撞埠。
- 就緒條件有兩個，都要成立：聽這個埠的 PID 等於引擎自己起的程序，而且 `readyPath` 回 2xx。只看健康檢查，可能打到別人的 server。
- 收尾：成功或失敗都只關引擎自己起的程序。server log 寫到 `out/server.log`。
- 在新專案第一次使用：agent 依專案現有線索起草配方（README、Dockerfile、既有的 run 腳本），跑 `env-check` 驗證，給使用者看過再 commit。

### 3.3 引擎指令

| 指令 | 做什麼 |
|---|---|
| `build <video.mjs>` | 確認已建置 → 找埠 → reset → start → 就緒 → 配音（有快取）→ 錄影 → 字幕 → 合成 → 驗證 → stop |
| `dry-run <video.mjs>` | 確認已建置 → 找埠 → reset → start → 跑全部段落（不配音、不錄影、不等語音）→ 每段的操作秒數表 → stop |
| `env-check` | build → reset → start → 就緒 → stop，用來驗證配方 |
| `verify <out>` | 不變 |

- `--base <url>` 保留：有給時不起站，直接錄指定網址，相容沒有配方的專案。
- 腳本的 `setup(page, actor, url)` 保留。之後 `url` 由引擎用實際的埠組出來，腳本不再寫死 `base`。
- dry-run 失敗時，除了現有的截圖、網址、畫面文字之外，還要印出畫面上可互動的元素清單：按鈕、連結、欄位標籤、浮層選項，取代手寫 probe 腳本。

### 3.4 配音快取

- 以「文字＋聲音＋provider」的雜湊當 key，mp3 存在 `video/.tts-cache/`（不進版控）。
- 旁白沒改就不重新配音：重跑更快，文字也少送幾次到外部服務。

### 3.5 操作員新增方法

| 方法 | 行為 |
|---|---|
| `a.upload(按鈕, 檔案)` | 先等 filechooser，再點按鈕，最後 setFiles；相對路徑以影片目錄為準 |
| `a.select(欄位, 選項)` | 點欄位，在浮層容器（`ui.menu`，或預設的 `listbox`）的最後一個裡點選項 |
| `a.as(userId, 路徑?)` | 在背景呼叫配方的 `login`，換身分後直接到 `路徑`（省略就重新載入目前頁面）；沒寫 `login` 時直接報錯 |

- `a.as` 的畫面效果是直接跳頁，右上角換人名，不演示登入流程。要演示登入，照樣可以用 `a.click` 點帳號。

### 3.6 審稿附操作秒數，每段檢查畫面

- 流程改為：寫稿 → **dry-run** → 審稿 → build → 驗證 → 試聽。
- 審稿表每段列四欄：旁白、語音估計、操作秒數、狀態。
  - 語音估計 = 字數 ÷ 5 + 1 秒，不送 TTS。實測約每秒 5 字，加檔尾靜音約 1 秒。這樣維持「審稿前不配音」。
  - 操作比語音估計長的段落標 ⚠️，由使用者在審稿時決定要加長旁白、拆段，或接受。
- 每段可以寫 `expect`（文字或 locator）。引擎在操作做完時檢查，沒過就跟操作失敗一樣處理：停下來、留截圖。
- contact sheet 改抓「每段操作完成的那一刻」，不再抓語音中點；中點常抓到換頁中的畫面。`timeline.json` 要多記每段操作完成的時間。
- agent 仍要開 contact sheet 看，字幕有沒有遮擋、畫面好不好看，只能用眼睛判斷。

### 3.7 回報與授權

- SKILL 第 8 步的回報格式，以及動工前的預估，都要分開寫「成片長度」和「製作時間」，並寫出使用者要介入幾次（審稿、試聽）。
- 配音來源與授權狀態寫進 MP4 metadata，例如 `comment=配音：Edge TTS zh-TW-HsiaoChenNeural，商用授權未確認`。檔案流出去之後，資訊還跟著。
- 授權是專案層的決定，記在配方的 `tts.licensed`，每個專案只問一次。`licensed: false` 時，引擎在回報結尾固定印「對外發布前要確認配音授權」。

### 3.8 邊界情況

| 情況 | 行為 |
|---|---|
| 沒有 `video/env.mjs` 也沒給 `--base` | 失敗退出，訊息說明要先起草配方或給 `--base` |
| 配方缺必填欄位（build、reset、start） | 與腳本驗證一樣，列出缺哪些欄位後退出 |
| 使用者中斷（Ctrl-C、SIGTERM） | 照樣關掉引擎起的 server 再退出 |
| 同一專案同時跑兩個 build 或 dry-run | 共用資料目錄會互相干擾：第二個直接拒絕，訊息說明已有一個在跑（含 PID） |
| 找到空埠後、app 起來前，埠被別人搶走 | 就緒驗證會因 PID 不符而失敗，訊息說明重跑即可；不自動重試 |
| 旁白空字串 | 既有腳本驗證已經擋下，不變 |
| 權限 | 不適用：本機工具，沒有使用者權限的概念 |

## 4. SKILL.md 與參考文件的改動

| 位置 | 改動 |
|---|---|
| 第 0 步 | 目錄改成 `video/`；先看專案有沒有既有慣例；檢查 gitignore；沒有 `env.mjs` 就起草，跑 env-check，給使用者看過再 commit；**起站前確認本機程式碼是不是要錄的版本，不是就用 AskUserQuestion 問**（開 worktree 或切分支，由使用者決定） |
| 第 1 步 | 不再用 live-drive 看 DOM，改成「寫稿 → dry-run 迴圈修選擇器」 |
| 第 2 步 | 審稿附秒數表（3.6） |
| 第 7～8 步 | contact sheet 抓的時間點；`expect`；回報分開寫長度和時間；授權提醒 |
| `script-format.md` | 新增 `a.upload`、`a.select`、`a.as`、`expect`；`base` 改為選填 |
| `troubleshooting.md` | 第 9、10 條（埠、PID）改註明「引擎已強制處理」，原文保留當背景；新增「`@` 提及清單太長，目標在可視範圍外：多打一個字縮小清單」 |
| `examples/leave-request` | `run.sh` 改寫成 `env.mjs`；e2e 測試跟著改 |

## 5. 驗收

### 5.1 驗收案例（即規格 §2.3）

以 `scripts/` 底下的 node 測試執行（channel 為 cli，qa-verify 不跑）；「leave-request」指 `examples/leave-request`。

#### AC-1 預設埠被佔用時改用空埠 [cli]

##### 前置條件
- 127.0.0.1:5180 有一個不是引擎起的程序在聽，且 `/api/health/ready` 回 200
- 配方 `start.portEnv` 為 `PORT`

##### 步驟
1. 執行 `env-check`

##### 預期
- 輸出「就緒：pid <引擎起的 PID>，埠 <N>」，N 不是 5180
- 結束後引擎起的 PID 已不存在
- 佔用 5180 的程序仍在執行

#### AC-2 server 起不來時失敗退出、不留殘留程序 [cli]

##### 前置條件
- 配方 `start.cmd` 指向不存在的執行檔

##### 步驟
1. 執行 `build leave-request/video.mjs`

##### 預期
- exit code 為 1
- 輸出含「server 未就緒」與 `out/server.log` 的路徑
- 沒有引擎起的程序殘留
- `out/` 沒有 mp4

#### AC-3 每次 build 前都重置資料 [cli]

##### 步驟
1. 連續執行兩次 `build leave-request/video.mjs`

##### 預期
- 兩次輸出都各有一行「reset 完成」
- 第二次的影片畫面與第一次相同（leave-request 第 2 段完成時清單列數兩次都是 1）

#### AC-4 dry-run 不配音、不錄影 [cli]

##### 步驟
1. 執行 `dry-run leave-request/video.mjs`

##### 預期
- TTS 呼叫次數為 0
- `out/` 沒有 mp4、沒有 frames 目錄
- 每段輸出一行「seg<i> 語音估計 <x>s 操作 <y>s」，超過的段落行尾有「⚠️」
- 全程少於 30 秒

#### AC-5 語音估計公式 [cli]

##### 步驟
1. 對旁白「這是一段剛好二十個字的測試旁白內容喔喔喔」（20 字）跑 dry-run，該段操作耗時 6.2 秒

##### 預期
- 該段語音估計顯示 5.0s（20 ÷ 5 + 1）
- 行尾有「⚠️」

#### AC-6 dry-run 失敗時印出可互動元素 [cli]

##### 前置條件
- 某段 `run` 點擊不存在的按鈕「不存在的按鈕」

##### 步驟
1. 執行 `dry-run`

##### 預期
- exit code 為 1
- 輸出「FAIL seg<i>」與 `out/fail.png` 路徑
- 輸出「可互動元素：」，其後列出畫面上實際存在的按鈕名稱（leave-request 為「送出」）

#### AC-7 expect 不符時視同失敗 [cli]

##### 前置條件
- 某段寫 `expect: '不會出現的文字'`

##### 步驟
1. 執行 `dry-run`

##### 預期
- 輸出「FAIL seg<i>」與「expect 未符合：不會出現的文字」
- `out/fail.png` 存在

#### AC-8 配音快取命中不再呼叫 TTS [cli]

##### 步驟
1. 執行 `build`
2. 不改旁白，再執行一次 `build`
3. 改第 1 段旁白一個字，再執行一次 `build`

##### 預期
- 步驟 2 的 TTS 呼叫次數為 0
- 步驟 3 的 TTS 呼叫次數為 1

#### AC-9 a.upload 上傳檔案 [cli]

##### 步驟
1. 腳本一段執行 `a.upload(上傳按鈕, 'files/sample.png')`

##### 預期
- 頁面上顯示檔名「sample.png」

#### AC-10 a.select 選浮層選項 [cli]

##### 步驟
1. 腳本一段執行 `a.select('假別', '特休')`，選項渲染在 body 底下的浮層

##### 預期
- 欄位值為「特休」

#### AC-11 a.as 換身分 [cli]

##### 前置條件
- 配方有 `login`

##### 步驟
1. 腳本一段執行 `a.as('user02', '/')`

##### 預期
- 頁面顯示 user02 的名稱
- 該段沒有點擊登入頁的動作（畫面上沒有出現登入頁）

#### AC-12 配方沒有 login 時 a.as 報錯 [cli]

##### 步驟
1. 配方不寫 `login`，腳本呼叫 `a.as('user02')`

##### 預期
- 輸出「配方沒有 login，不能用 a.as」
- exit code 為 1

#### AC-13 授權寫進影片 metadata 與回報 [cli]

##### 前置條件
- 配方 `tts: { provider: 'edge', licensed: false }`

##### 步驟
1. 執行 `build`
2. 用 ffprobe 讀 mp4 的 comment

##### 預期
- comment 含「Edge TTS」與「商用授權未確認」
- build 輸出最後一行是「對外發布前要確認配音授權」
- 把 `licensed` 改成 true 再 build，輸出不含這一行

#### AC-14 contact sheet 抓操作完成的時間點 [cli]

##### 步驟
1. 執行 `build`

##### 預期
- `timeline.json` 每段都有 `doneT`，且 t ≤ doneT ≤ t + 操作秒數
- contact sheet 格數等於段數加 2

#### AC-15 輸出目錄沒有被 git 忽略時提示 [cli]

##### 前置條件
- 專案 `.gitignore` 沒有忽略 `video/**/out/`

##### 步驟
1. 執行 `ensure-tools.sh`

##### 預期
- 輸出要補的 `.gitignore` 行，含 `video/**/out/`
- 不修改 `.gitignore`

#### AC-16 給 --base 時不起站 [cli]

##### 步驟
1. 自己起好 leave-request 站，執行 `build video.mjs --base <該網址>`

##### 預期
- 輸出沒有「reset 完成」與「就緒：」
- 影片正常產出，機器檢查通過

### 5.2 實機回歸

用新版在 dynamic-fields-design 重做 design-by-tasks。對照組是這次的紀錄：失敗 4 輪、6 段 OVER。新版目標：OVER 在審稿表就被看到；修選擇器時不用整支錄影。由使用者試聽判定。

## 6. 決策紀錄

| 決策 | 誰定 | 理由 | 否決的選項與原因 |
|---|---|---|---|
| 配方放在專案、進版控 | 使用者 | 跨影片共用，起站知識留在專案裡 | 放 `.claude/`：配方是專案的錄影工具，不是 agent 設定；跟著 video.mjs：每支影片重複一份 |
| 預設目錄 `video/` | 使用者 | 腳本不會遺失，也符合既有的 `video/pilot` 慣例 | 維持 `.tmp/` 可設定：預設仍是丟棄式，這次差點遺失 |
| 不做 `--from segN` | 使用者同意 | 前段會改資料，要接續得先重播前段，錄影也要接起來 | 做 `--from`：複雜度高，快速 dry-run 已經夠便宜 |
| 引擎自選空埠，並驗證 PID | 技術決定 | 這次的實際事故 | 固定埠加健康檢查：這次正是被這招誤判成就緒 |
| 語音用字數估（每秒 5 字＋1 秒） | 技術決定 | 不送 TTS 也能審稿；係數由這次兩支影片實測 | 審稿前先配音：違反「審稿前不配音」，旁白在使用者看過前就送出去了 |
| 授權寫進 MP4 metadata | 使用者同意 | 檔案流出去，資訊還跟著 | 旁邊放說明檔：寄檔時容易漏掉 |
| 換人用 API 在背景切換（a.as） | 技術決定 | 每次省約 3 秒，是 OVER 的主因 | 只保留點帳號登入：OVER 壓不下來；兩種都保留，由作者選 |
