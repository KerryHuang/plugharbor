# demo-video 優化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal：** demo-video 引擎接手起站、重置、埠驗證，新增 dry-run、配音快取、操作員新方法、每段畫面檢查，以及授權標記。

**Architecture：** 專案在 `video/env.mjs` 寫錄影環境配方，引擎從 `video/<名稱>/video.mjs` 往上一層找。`lib/env.mjs` 管起站生命週期：找埠、鎖、spawn、就緒判斷（驗 PID）、收尾。`build` 與 `dry-run` 共用同一個段落執行迴圈，差別只在配音與錄影。其餘新邏輯都拆成小模組：`lib/estimate.mjs`、`lib/tts-cache.mjs`、`lib/inspect.mjs`。

**Tech Stack：** Node 18+ ESM、`node:test`、playwright-core（既有）、ffmpeg／ffprobe（既有）、bash（ensure-tools）。

**Spec：** `docs/superpowers/specs/2026-11-16-demo-video-optimization-design.md`（版本 1.1.0）；`spec.dir`＝`docs/superpowers/specs`

**工作目錄：** worktree `../plugharbor-demo-video-opt`（plugharbor 同層），分支 `feature/demo-video-optimization`。下文路徑若沒特別說明，都相對於 `plugins/delivery/skills/demo-video/`，以下簡稱 `DV/`。

## Global Constraints

- 不新增 npm 依賴，只能用 Node 內建模組和既有的 playwright-core。
- 只關引擎自己起的程序，用 PID 個別 kill，不用 pkill，也不 kill 別人的程序。
- 輸出訊息逐字照規格，測試用這些字串斷言：
  - 「就緒：pid <PID>，埠 <N>」
  - 「server 未就緒」
  - 「reset 完成」
  - 「seg<i> 語音估計 <x>s 操作 <y>s」，超過的段落行尾加「 ⚠️」
  - 「FAIL seg<i>」
  - 「可互動元素：」
  - 「expect 未符合：<文字>」
  - 「配方沒有 login，不能用 a.as」
  - 「對外發布前要確認配音授權」
  - 「已有一個 demo-video 在跑（pid <PID>）」
- 語音估計固定為 `字數 ÷ 5 + 1` 秒。字數只算 Unicode 字母與數字（`\p{L}|\p{N}`），保留一位小數。
- MP4 metadata 的 comment：`配音：<provider 顯示名> <voice>，商用授權<已確認|未確認>`。provider 為 `edge` 時，顯示名是 `Edge TTS`。
- 路徑一律用 `node:path`。不能寫死 `/`，不能假設 POSIX shell，`ensure-tools.sh` 除外。
- 版號：delivery `1.0.0` → `1.1.0`（minor，新功能），`CHANGELOG.md` 同步新增條目。
- 既有的 `--base` 行為不能改：給了 `--base` 就完全不碰配方。

## Review Focus

1. **`start.cmd` 的路徑含空白**（例如 `C:/Program Files/...`）：用空白切字串會切錯。`start.cmd` 要同時接受字串與字串陣列，陣列不切。→ Task 2 加測試 `cmd 陣列含空白路徑可啟動`。
2. **配方的 `build`／`reset` 拋例外**：要以「配方 <欄位> 失敗：<訊息>」退出，而且不能已經起了 server 又沒收。→ Task 2 加測試 `reset 拋錯時不留下 server`。
3. **配音快取檔是 0 byte**（上次寫到一半就中斷）：要當成沒命中，重新配音。→ Task 1 加測試 `空檔視為未命中`。
4. **`listenerPid` 在 Windows 沒有 lsof**：改用 `netstat -ano` 解析，測試只在 POSIX 跑。→ Task 2 寫成分支，測試用 `{ skip: process.platform === 'win32' }`。
5. **dry-run 中途失敗，仍要收 server、釋放鎖**：下一次跑才不會被鎖擋住。→ Task 3 加測試 `dry-run 失敗後可立即再跑`。

---

### Task 1：語音估計與配音快取（純函式）

**Files：**
- Create: `DV/scripts/lib/estimate.mjs`, `DV/scripts/lib/tts-cache.mjs`
- Test: `DV/scripts/estimate.test.mjs`, `DV/scripts/tts-cache.test.mjs`

**Interfaces：**
- Produces:
  - `estimateVoiceSec(text: string): number`：回傳一位小數。
  - `withTtsCache(tts: (text, outFile, opts) => Promise<void>, { dir: string, provider: string }): (text, outFile, opts) => Promise<{ hit: boolean }>`：key 是 `sha256(provider + '\0' + opts.voice + '\0' + text)`，快取檔是 `<dir>/<key>.mp3`。命中時直接 copy 到 outFile；沒命中就呼叫 tts，產出後存進快取。

- [ ] **Step 1：寫失敗測試**
  - `estimate.test.mjs`：
    - `estimateVoiceSec('這是一段剛好二十個字的測試旁白內容喔喔喔') === 5`（AC-5）
    - `estimateVoiceSec('一、二。') === 1.4`：標點不計，只算 2 字，2 ÷ 5 + 1 = 1.4。
    - `estimateVoiceSec('Edge TTS 3') === 2.6`：字母與數字共 8 個，8 ÷ 5 + 1 = 2.6。
  - `tts-cache.test.mjs`，用寫檔的 stub tts 並計數：
    - 第一次 `{hit:false}`、stub 呼叫 1 次。
    - 同文字第二次 `{hit:true}`、stub 仍是 1 次。
    - 改一個字變 2 次。
    - voice 不同也是未命中。
    - `空檔視為未命中`：把快取檔截成 0 byte 後再跑，stub 會再被呼叫。
- [ ] **Step 2：** `node --test DV/scripts/estimate.test.mjs DV/scripts/tts-cache.test.mjs`。預期 FAIL：模組不存在。
- [ ] **Step 3：** 實作兩個模組。快取先寫到 `.tmp-<pid>` 再 rename，避免寫到一半留下壞檔。
- [ ] **Step 4：** 同一指令，預期 PASS。
- [ ] **Step 5：** commit `feat(delivery): demo-video 語音估計與配音快取`

### Task 2：錄影環境配方與起站生命週期（`env-check`）

**Files：**
- Create: `DV/scripts/lib/env.mjs`
- Modify: `DV/scripts/demo-video.mjs`：加 `env-check` 指令、用法字串、SIGINT／SIGTERM 收尾。
- Test: `DV/scripts/env.test.mjs`

**Interfaces：**
- Produces（`lib/env.mjs`）：
  - `findEnv(scriptPath: string): string | null`：只看 `dirname(scriptPath)/../env.mjs`。
  - `loadEnv(envPath): Promise<Recipe>`：缺 `build`、`reset`、`start.cmd`、`start.portEnv`、`start.readyPath` 時拋錯，訊息格式比照 `formatScriptErrors`，每一行「✗ <欄位>：…」。
  - `Recipe` 的欄位照規格 §3.2，另外有兩個選填欄位：
    - `start.port?: number`：偏好埠，被占用就改用空埠（AC-1 的前提）。
    - `start.readyTimeoutMs?: number`：預設 60000。
  - `findFreePort(preferred?: number): Promise<number>`：preferred 能在 127.0.0.1 listen 就用它，否則 listen 0 取得系統配的埠。
  - `listenerPid(port: number): number | null`：POSIX 用 `lsof -tiTCP:<port> -sTCP:LISTEN`；win32 用 `netstat -ano`。
  - `acquireLock(dataDir): () => void`：鎖檔是 `<dataDir>/.lock`，內容寫 pid。檔案存在且那個 pid 還活著，就拋「已有一個 demo-video 在跑（pid <PID>）」；pid 已死的鎖直接接手。回傳值是釋放函式。
  - `startEnv(recipe, { videoRoot, outDir, log = console.log }): Promise<{ url: string, pid: number, stop: () => Promise<void> }>`，依序做：
    1. acquireLock
    2. `recipe.build({ root: videoRoot, sh })`
    3. `recipe.reset({ dataDir, sh, env })`，然後印「reset 完成」
    4. spawn：不經 shell；`cmd` 是字串就用空白切，是陣列就不切；cwd 相對於 videoRoot；stdout 和 stderr 寫到 `<outDir>/server.log`
    5. 每 250ms 檢查一次，直到 `listenerPid(port) === pid` 且 `GET readyPath` 回 2xx，然後印「就緒：pid <PID>，埠 <N>」
    6. 逾時或子程序先結束，就 kill 子程序並拋「server 未就緒（log：<server.log 路徑>）」
    - 其中 `dataDir = <videoRoot>/.data`，`env = { ...process.env, ...start.env, [portEnv]: String(port) }`。
    - `stop()`：kill 自己的 pid，等它結束（最多 5 秒，之後送 SIGKILL），再釋放鎖。
    - 任一步驟失敗，都要先收掉已起的程序和鎖再拋出；配方函式拋錯時，訊息改成「配方 <欄位> 失敗：<原訊息>」。
- Produces（`demo-video.mjs`）：
  - `envCheck(videoRootOrScript): Promise<void>`
  - 全域 `activeStops: Set<() => Promise<void>>`：SIGINT／SIGTERM 時逐一呼叫，然後 `process.exit(130)`。

- [ ] **Step 1：寫失敗測試**（`env.test.mjs`）。假 app 用 `node -e` 起一個 http server，讀 `process.env.PORT`、回 `/ready` 200。配方寫在 tmp 目錄：
  - `預設埠被佔用時改用空埠`（AC-1）：測試自己 listen 埠 P，並對 `/ready` 回 200；配方 `start.port = P`。預期：
    - 輸出符合 `/就緒：pid (\d+)，埠 (\d+)/`，且 N ≠ P。
    - `stop()` 之後，`process.kill(pid, 0)` 拋 ESRCH。
    - 測試自己的 server 仍能回應。
  - `server 起不來時失敗退出`（AC-2）：分兩種情況，cmd 是 `['不存在的執行檔']`，或 cmd 是不 listen 的 node 程序且 readyTimeoutMs 為 1500。預期：
    - rejects，訊息符合 `/server 未就緒/` 且含 `server.log`。
    - 子程序已不存在。
    - 鎖檔已刪除。
  - `PID 不符不算就緒`（§3.8 搶埠）：假 app 不 listen，測試自己在 `PORT` 上 listen 並回 200。預期 rejects，訊息符合 `/server 未就緒/`。
  - `同時兩個被拒`（§3.8）：第一次 `startEnv` 成功後，第二次 rejects，訊息符合 `/已有一個 demo-video 在跑（pid \d+）/`。鎖檔裡的 pid 已死時，可以接手。
  - `缺必填欄位列出全部`：配方只有 `start` 時，訊息同時含 `✗ build` 與 `✗ reset`。
  - `reset 拋錯時不留下 server`（Review 2）
  - `cmd 陣列含空白路徑可啟動`（Review 1）：把假 app 寫到含空白的目錄，cmd 為 `[process.execPath, '<含空白路徑>/app.js']`。
  - `SIGINT 會收掉 server`：spawn `node demo-video.mjs env-check`，用慢就緒的假 app。看到「reset 完成」後送 SIGINT，預期：
    - exit code 130。
    - 假 app 的 pid（假 app 寫入 pidfile）已不存在。
- [ ] **Step 2：** `node --test DV/scripts/env.test.mjs`，預期 FAIL。
- [ ] **Step 3：** 實作 `lib/env.mjs` 與 `env-check` 指令。`env-check` 依序呼叫 `startEnv`、`stop`，成功就印「env-check 通過」。
- [ ] **Step 4：** 同一指令，預期 PASS。另外跑既有測試 `node --test DV/scripts/validate.test.mjs DV/scripts/subtitles.test.mjs`，預期 PASS。
- [ ] **Step 5：** commit `feat(delivery): demo-video 錄影環境配方與 env-check`

### Task 3：dry-run、expect 與失敗時的元素清單

**Files：**
- Create: `DV/scripts/lib/inspect.mjs`
- Modify:
  - `DV/scripts/demo-video.mjs`：抽出段落迴圈，加 `dry-run` 指令。
  - `DV/scripts/lib/validate-script.mjs`：有配方時 `base` 改選填；驗 `expect` 的型別。
- Test: `DV/scripts/dryrun.test.mjs`；`DV/scripts/validate.test.mjs` 加案例。

**Interfaces：**
- Consumes：Task 1 的 `estimateVoiceSec`；Task 2 的 `findEnv`、`loadEnv`、`startEnv`、`activeStops`。
- Produces：
  - `listInteractive(page): Promise<string[]>`（`lib/inspect.mjs`）：可見的 button、link、checkbox、tab、menuitem、option，以及有 label 的欄位。逐一取 accessible name，去重，最多 40 筆。
  - `runSegments(segments, actor, { page, outDir, waitFor: (i, usedMs) => Promise<void> }): Promise<{ ok: boolean, segs: Array<{ usedMs: number, doneMs: number }> }>`：
    - 每段做完 `run` 後，若有 `expect` 就檢查：字串用 `page.getByText(expect).first().waitFor({ timeout: 3000 })`；函式則呼叫 `expect(actor)` 取得 locator，再 waitFor。
    - `doneMs = Date.now()` 在操作與 expect 都完成時記錄。
    - 失敗時：截圖到 `out/fail.png`；印「FAIL seg<i> <url>」、錯誤摘要、畫面文字；再印「可互動元素：」，後面每行一筆。expect 不符時，錯誤摘要是「expect 未符合：<文字>」。
    - 回傳 `ok: false`。
    - `build` 傳入的 `waitFor` 補足語音長度；`dry-run` 傳不等待的 no-op。
  - `dryRun(scriptPath, { base?: string, out?: string }): Promise<{ ok: boolean }>`：
    - 不配音、不錄影，`out` 只放 fail.png 與 server.log。
    - 每段印「seg<i> 語音估計 <x>s 操作 <y>s」，`y > x` 時行尾加「 ⚠️」。
    - 不管成功或失敗，都在 finally 裡 stop。
  - `validateScript(cfg, { base, hasEnv })`：`!base && !cfg.base && !hasEnv` 才報錯。訊息改為「腳本沒有 base，沒給 --base，也找不到 video/env.mjs」。`expect` 只能是非空字串或函式。

- [ ] **Step 1：寫失敗測試**（`dryrun.test.mjs`）。沒有 Chrome 或 playwright-core 時，照 `e2e.test.mjs` 的 `skipReason` 跳過。配方用 node 靜態頁 app，頁面就是 e2e 的 PAGE。
  - `dry-run 不配音不錄影`（AC-4）：腳本的 `tts` 是計數 stub。預期：
    - stub 被呼叫 0 次。
    - `out/` 沒有 `*.mp4`，也沒有 `frames/`。
    - 每段都有符合 `/seg\d 語音估計 [\d.]+s 操作 [\d.]+s/` 的行。
    - 全程 < 30000ms。
  - `操作超過估計時標 ⚠️`（AC-5）：一段旁白是那 20 字，`run` 為 `a.pause(6200)`。預期該行含「語音估計 5.0s」並以「 ⚠️」結尾。
  - `失敗時印可互動元素`（AC-6）：一段點 `getByRole('button',{name:'不存在的按鈕'})`，timeoutMs 為 1500。預期：
    - exit 1。
    - 輸出符合 `/FAIL seg\d/`、含 `fail.png`、含「可互動元素：」，且下一行起有一行是「送出」。
  - `expect 不符視同失敗`（AC-7）：`expect: '不會出現的文字'`。預期：
    - 輸出含「FAIL seg」與「expect 未符合：不會出現的文字」。
    - `out/fail.png` 存在。
  - `dry-run 失敗後可立即再跑`（Review 5）：AC-6 跑完後馬上再跑一次 dry-run，預期不出現「已有一個 demo-video 在跑」。
  - `validate.test.mjs`：
    - `{segments:[…]}` 搭配 `hasEnv:true` 時，沒有錯誤。
    - `expect: 3` 時報 `segments[0].expect`。
- [ ] **Step 2：** `node --test DV/scripts/dryrun.test.mjs DV/scripts/validate.test.mjs`，預期 FAIL。
- [ ] **Step 3：** 實作。`build` 改呼叫 `runSegments`，行為不變；`build` 失敗時同樣印元素清單。
- [ ] **Step 4：** 同一指令，預期 PASS。再跑 `node --test DV/scripts/e2e.test.mjs`（`--base` 路徑），預期 PASS。
- [ ] **Step 5：** commit `feat(delivery): demo-video dry-run、expect 與失敗元素清單`

### Task 4：build 接上配方、快取、doneT、授權標記

**Files：**
- Modify:
  - `DV/scripts/demo-video.mjs`：`build`、`verify`。
  - `DV/scripts/lib/media.mjs`：`compose` 多收 `metadata: Record<string,string>`，轉成 `-metadata k=v`。
- Test: `DV/scripts/e2e.test.mjs`：既有測試加斷言，另新增一個測試。

**Interfaces：**
- Consumes：Task 1 的 `withTtsCache`；Task 2 的 `startEnv`；Task 3 的 `runSegments`。
- Produces：
  - `build(scriptPath, { out?, base? })`：
    - 沒給 `--base` 時走配方。
    - `out` 預設 `dirname(scriptPath)/out`。
    - 配音包一層 `withTtsCache`，快取目錄是 `<videoRoot>/.tts-cache`。給 `--base` 時，用 `dirname(scriptPath)/.tts-cache`。
  - `timeline.json`：每段多記 `doneT`（秒，相對影片開頭），全域多記 `tts: { provider, voice, licensed }`。
  - `verify`：contact sheet 的時間點改為 `[0.3, ...segs.map(g => g.doneT), total - 0.5]`，提示文字改成「每格依序為：開頭、各段操作完成時、結尾」。`licensed !== true` 時，最後一行印「對外發布前要確認配音授權」。
  - 配方 `tts` 的預設值是 `{ provider: 'edge', licensed: false }`。腳本自己帶 `tts` 函式、且沒有配方時，provider 記為 `custom`。

- [ ] **Step 1：寫失敗測試**
  - 既有測試（`--base`，AC-16）：
    - 輸出不含「reset 完成」，也不含「就緒：」。
    - `timeline.json` 每段 `t <= doneT`。
    - contact sheet 存在。
  - 新測試 `配方模式：每次重置、快取、授權標記`：tmp 目錄放 `env.mjs`。reset 每次都把 `.data/count` 歸零，並 append 一行到 `.data/resets.log`；app 是 e2e PAGE 的靜態頁。腳本 `tts` 是會寫計數檔的 sine stub。依序：
    1. build：預期 exit 0、stub 呼叫 2 次、輸出含「reset 完成」。
    2. 不改旁白再 build：預期 stub 呼叫數不變（AC-8），`resets.log` 有 2 行（AC-3）。
    3. 改第 1 段一個字再 build：預期 stub 只多 1 次（AC-8）。
    4. ffprobe 讀 `format_tags=comment`：預期含「商用授權未確認」，且輸出最後一行是「對外發布前要確認配音授權」（AC-13）。
    5. 把配方改成 `licensed:true` 再 build：預期輸出不含那一行。
    6. contact sheet 的格數 = 段數 + 2（AC-14）：檢查 `verify/frames/` 的檔案數。
- [ ] **Step 2：** `node --test DV/scripts/e2e.test.mjs`，預期 FAIL。
- [ ] **Step 3：** 實作。
- [ ] **Step 4：** 同一指令，預期 PASS。另外跑全部 `node --test DV/scripts/*.test.mjs`，預期 PASS。
- [ ] **Step 5：** commit `feat(delivery): demo-video build 接配方、配音快取與授權標記`

### Task 5：操作員 `a.upload`、`a.select`、`a.as`

**Files：**
- Modify:
  - `DV/scripts/lib/actor.mjs`
  - `DV/scripts/demo-video.mjs`：`createActor` 傳入配方的 `ui`、`login`，以及影片目錄。
- Test: `DV/scripts/actor.test.mjs`（需要 Chrome，沒有就 skip）

**Interfaces：**
- Consumes：配方的 `ui?: { menu?: string }`、`login?: (page, userId) => Promise<void>`。
- Produces：`createActor(page, { moveMs, typeDelay, ui, login, fileRoot })`，新增三個方法：
  - `a.upload(button: Locator, file: string): Promise<void>`：先 `page.waitForEvent('filechooser')`，再 `a.click(button)`，最後 setFiles。file 是相對路徑時以 `fileRoot`（影片目錄）為準。
  - `a.select(label: string | Locator, option: string): Promise<void>`：label 是字串時用 `page.getByLabel(label)`。點開之後，浮層容器用 `ui.menu`，沒設時用 `[role=listbox]`，取 `.last()`，再用 `getByText(option, { exact: true })` 點選項。
  - `a.as(userId: string, path?: string): Promise<void>`：沒有 `login` 時拋 `Error('配方沒有 login，不能用 a.as')`。有的話先 `await login(page, userId)`，再 goto `path`（相對於目前 origin）；沒給 path 就 reload。

- [ ] **Step 1：寫失敗測試**。測試頁用 `page.setContent`，不需要 server：
  - `a.upload`（AC-9）：頁面有按鈕，按下時點隱藏的 file input，並把檔名顯示到 `#name`。預期 `#name` 的文字是「sample.png」。
  - `a.select`（AC-10）：欄位 `aria-label=假別`，點下去會在 body 末端 append 一個 `role=listbox`，裡面有「特休」「事假」。點選項時把值寫回欄位。預期欄位值為「特休」。另外驗 `ui:{menu:'.my-menu'}` 也能用。
  - `a.as`（AC-11）：login stub 設 cookie 為 user02；頁面依 cookie 顯示名稱，用 `page.route` 回應。預期顯示「user02」。
  - `a.as 沒有 login`（AC-12）：預期 rejects，訊息為「配方沒有 login，不能用 a.as」。
- [ ] **Step 2：** `node --test DV/scripts/actor.test.mjs`，預期 FAIL。
- [ ] **Step 3：** 實作。
- [ ] **Step 4：** 同一指令，預期 PASS。
- [ ] **Step 5：** commit `feat(delivery): demo-video 操作員 upload／select／as`

### Task 6：ensure-tools 改用 `video/` 並檢查 gitignore

**Files：**
- Modify: `DV/scripts/ensure-tools.sh`
- Test: `DV/scripts/ensure-tools.test.mjs`

**Interfaces：**
- 用法改成 `ensure-tools.sh --dir <video 目錄> [--check]`，`--dir` 的語意不變（node_modules 裝在這裡）。
- 新增第 6 項「gitignore」：`--dir` 在 git repo 裡時，對 `<dir>/x/out/a.mp4`、`<dir>/.data/x`、`<dir>/.tts-cache/x`、`<dir>/node_modules/x` 逐一跑 `git check-ignore -q`。有沒被忽略的，就印「gitignore ⚠ 請在 .gitignore 補上：」，後面每行一條，例如 `video/**/out/`，相對於 repo 根。只提示，不改檔，也不算 MISSING。

- [ ] **Step 1：寫失敗測試**（AC-15）：tmp 目錄 `git init`，`.gitignore` 只寫 `*.log`。執行 `bash ensure-tools.sh --dir <tmp>/video --check`。預期：
  - 輸出含 `video/**/out/`、`video/.data/`、`video/.tts-cache/`。
  - `.gitignore` 內容不變。
  - 補齊 `.gitignore` 後再跑，輸出不含「請在 .gitignore 補上」。
- [ ] **Step 2：** `node --test DV/scripts/ensure-tools.test.mjs`，預期 FAIL。
- [ ] **Step 3：** 實作。
- [ ] **Step 4：** 同一指令，預期 PASS。
- [ ] **Step 5：** commit `feat(delivery): demo-video ensure-tools 檢查 video/ 的 gitignore`

### Task 7：範例、文件與版號

**Files：**
- Create: `DV/examples/env.mjs`：用 Node 內建 http 提供 `examples/leave-request/index.html` 的靜態站；`reset` 沒有資料要清，只印訊息；`tts:{provider:'edge',licensed:false}`。
- Modify:
  - `DV/examples/leave-request/video.mjs`：拿掉 `base`，假別改用一般 `a.click` 加 `selectOption`（原生 select，不是浮層），註解更新執行方式。
  - `DV/SKILL.md`：照規格 §4 的表逐列改。
    - 第 0 步：`video/` 目錄、既有慣例、gitignore、起草配方並跑 env-check、確認程式碼版本並用 AskUserQuestion 問。
    - 第 1 步：dry-run 迴圈。
    - 第 2 步：秒數表格式，四欄是旁白、語音估計、操作、狀態。
    - 第 7～8 步：contact sheet 時間點、expect；回報分開寫「成片長度」「製作時間」和介入次數；授權提醒。
  - `DV/references/script-format.md`：新增 `a.upload`、`a.select`、`a.as`、`expect`；`base` 改為選填；新增 `env.mjs` 欄位表。
  - `DV/references/troubleshooting.md`：
    - 第 9、10 條改成「引擎已強制處理（自選空埠、驗 PID、只關自己的程序）」，原文保留當背景。
    - 新增一條：`@` 提及清單太長，目標在可視範圍外時，多打一個字縮小清單。
  - `plugins/delivery/.claude-plugin/plugin.json`：1.1.0。
  - `plugins/delivery/CHANGELOG.md`：新增 `[1.1.0] - 2026-11-16` 條目，起因、改動、設計連結。
  - `docs/feature.md`：demo-video 段四項改 `[x]`，完成數改成 4／共 4。
- Delete: `DV/examples/leave-request/run.sh`

- [ ] **Step 1：** 在 `DV/examples` 下跑 `node DV/scripts/demo-video.mjs env-check examples/leave-request/video.mjs`，預期輸出含「env-check 通過」。
- [ ] **Step 2：** 跑 `dry-run examples/leave-request/video.mjs`，預期 exit 0，4 段都有秒數行。
- [ ] **Step 3：** 跑 repo 的驗證：`node --test $(git ls-files 'plugins/**/*.test.mjs') 'setup/adapters/tests/*.test.mjs'`，再加上 `.github/workflows/validate.yml` 裡其他的 validate 步驟（版號一致、共用副本），逐條照抄執行。預期全部 PASS。
- [ ] **Step 4：** commit `docs(delivery): demo-video 範例改用配方、文件與版號 1.1.0`

### Task 8：後段（規格比對、整合測試、經驗、回填）

- [ ] 照 `plugins/lifecycle/skills/implement/references/after.md` 做。規格路徑與 `spec.dir` 見本計畫開頭。
- [ ] 規格 §5.2 的實機回歸（在 dynamic-fields-design 重做 design-by-tasks），在這裡只準備好指令與待辦，交給使用者決定何時跑、試聽。回報標「未驗證」。
