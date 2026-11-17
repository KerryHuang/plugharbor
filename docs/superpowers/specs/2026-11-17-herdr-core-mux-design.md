# 派工層同時支援 Herdr.app（herdr-core）與 herdr TUI

日期：2026-11-17　狀態：已核准（使用者 2026-11-17）

## 起因與目的

使用者要從 herdr TUI（Homebrew `herdr` 0.9.x）轉到 Herdr.app（原生視窗，底層 herdr-core，CLI 為 `hc`）。
plugharbor 的派工層（開 worker、雙顧問、self-rotate、相關 hook／guard）全綁在 `herdr` CLI 與 `HERDR_ENV`，
在 app 開的終端裡會失效。目標：兩種環境都能派工，行為一致；TUI 使用者（含公開 repo 其他人）不受影響。

起因（CHANGELOG 用）：使用者 2026-11-17 轉用 Herdr.app，派工流程在 app 內無法開 worker。

## 目標

- 在 app 終端內：agent-dispatch 長任務 worker、雙顧問討論、handoff／unattended 的 self-rotate、
  herdr-env-context／compact-context／notification hook 都正常運作。
- 在 TUI 內：行為與現在相同，既有測試全過。
- skill 文件只寫一套動作，後端差異集中在一支轉接腳本。

## 非目標

- 不移除 TUI 支援（使用者裁決：兩邊都支援）。
- 不做遠端 machine（`hc --on`）派工。
- 不改派工判準（何時開 worker、模型等級表）。
- 不用 hc templates 取代現有 prompt 組裝。

## 反目標（做出來也算失敗）

- skill 文件出現兩套並列指令，讓 agent 讀 skill 的 token 明顯變多。
- 在 TUI 裡啟動的 core 繼承了 `HERDR_ENV=1`，導致 app 終端被誤判成 TUI 而呼叫 `herdr`（見「偵測」）。
- 主 session 被擠小或被關掉（現行版面原則：主 session 保持最大）。

## 已確認的事實（2026-11-17 實測）

- `hc` 0.1.19、`herdr-app` 0.1.15 已裝在 `~/.local/bin`；`hc` 呼叫時會自動啟動 core。
- hc 終端拿的是 **core 啟動當時的環境**，不是呼叫者的：`MUXPROBE=caller hc run 'echo $MUXPROBE'` 印空字串。
  本次 core 是從 TUI 內的 Claude Code Bash 自動啟動的，所以每個 hc 終端都帶 `HERDR_ENV=1`、`HERDR_PANE_ID`、
  `CLAUDECODE=1`、`CLAUDE_CODE_CHILD_SESSION=1`（後者會讓 worker 的 transcript 不落檔）。`hc server restart` 保留舊環境，只有 stop 再 start 才換新。
- **任何 `hc` 指令（含 `hc server status`）在 core 沒跑時都會自動啟動 core**，用的是呼叫者當下的環境。
  2026-11-17 實測：`hc server stop` 後緊接 `hc server status` 就以 Claude Code 環境重啟了 core。
  因此 `mux.py`、hook、測試在 core 沒跑時**不得呼叫 hc**：先不經 hc 檢查 core 是否在跑（例：`pgrep -f herdr-core` 或 socket 可連線，方法由 builder 定，有不自動啟動的旗標就用旗標），
  沒跑就回 `{"error":"core_not_running","hint":"從 Dock 開 Herdr.app"}`。測試照 `hc --skill` 指示用獨立 `HC_SESSION` 與暫存 XDG 路徑。
- 每個 hc 終端另有 `HC_TERMINAL_ID`、`HC_TERMINAL_SOCKET`、`HC_SCOPE`。
- `hc exec` 不設 `HC_TERMINAL_ID`；`hc run` 會。
- `hc send` 對純程式（`cat`）送的文字原樣到達，沒有 `<hc from>` 包裝（含從 hc 終端內送出）。對 agent 終端是否包裝**未驗證**。
- `hc get --json` 有 `status`（idle/working/blocked/error/done 類）、`turn`、`state`、`labels`、`first_message`、`name`，
  **沒有** agent 的 session id（舊 CLI `agent_session.value`）。
- `herdr-app` 視窗沒開時，`herdr-app do …` 失敗（`no Herdr window`）；hc 終端照跑。
- app 視窗指令（`herdr-app commands`，名稱取自 binary，參數未驗）：`pane.split`、`pane.swap`、`pane.close`、`pane.zoom`、
  `terminal.open --place right|down --target`、`tab.new`、`layout.set`／`layout.resize`、`agent.focus`。
  hc 終端加 label `herdr.space=<id>`（可再加 `herdr.tab=<id>`）才會進視窗，沒 label 的留在背景。

## 做法（Approaches）

考慮過三種：

1. **共用轉接腳本 `mux.py`（選用）**：派工需要的動作收斂成固定子指令，腳本內偵測後端並翻譯。文件一套、分支一處、測試集中。
2. 每處就地分支：約 45 檔文件各寫兩段。文件變兩倍長、改行為要改兩處。否決。
3. 文件只寫 hc、TUI 用 shim 模擬 hc：要在 TUI 重做 `wait --children`、回報標籤等語意，容易半套。否決。

使用者 2026-11-17 選 1。

## 設計

### 1. `mux.py`

位置：`plugins/toolkit/scripts/mux.py`（正本）；其他 plugin 需要時複製到各自 `scripts/mux.py`，登記進
`scripts/ci/shared-copies.json`，由既有比對機制保證一致。純 Python 3 標準庫，輸出 JSON（stdout），錯誤時 exit≠0 並輸出 `{"error":…,"hint":…}`。

**偵測（`mux.py env`）**，依序：

1. 只有一組變數（`HC_TERMINAL_ID` 或 `HERDR_ENV=1`＋`HERDR_PANE_ID`）→ 對應後端。
2. 兩組都在（core 或 herdr server 是在另一邊啟動的）→ 看誰的終端是**離自己最近的祖先程序**：
   `hc get $HC_TERMINAL_ID --json` 的 `pid` 與 herdr pane 的 shell pid（`herdr pane get`）比對自己的 process 祖先鏈，較近者勝；
   查不到就 `hc`。（我的決定；hook 內嵌判斷只做第 1 條＋「兩組都在 → 交給 `mux.py env`」，避免 hook 變慢）
3. 否則 → `none`。

輸出 `{"backend":"hc|herdr|none","self":"<自己的位址>","window":true|false}`；`window` 只在 hc 時有意義（`herdr-app status` 成功與否）。
可用環境變數 `MUX_BACKEND=hc|herdr|none` 強制指定（測試與除錯用）。

**動作**（名稱是我的決定，builder 可微調，但文件只能引用這組）：

| 動作 | 用途 | herdr 對應 | hc 對應 |
|---|---|---|---|
| `env` | 判斷在不在 herdr 內、自己是誰 | `HERDR_ENV`、`HERDR_PANE_ID` | `HC_TERMINAL_ID` |
| `spawn --name --kind --cwd [--below <w>] [--env K=V]… -- <CLI 參數>` | 開可見 worker 並啟動 CLI，回 `{"id":…}` | `pane split` ＋ `agent start` ＋ `pane rename` | `hc run --bg --name … --cwd … <cli> <參數>`（env 用 `env K=V` 前綴或等效），再依「版面」放進視窗 |
| `send <w> <文字檔或文字> [--wait --timeout 秒]` | 送 prompt；`--wait` 阻塞到該輪結束，回狀態 | `agent prompt [--wait --timeout ms]` | `hc send [--wait --timeout]` |
| `wait <w> [--timeout 秒]` | 等到不在工作 | `agent wait --until idle` | `hc wait <w>` |
| `read <w> [--lines N]` | 畫面文字 | `pane read`／`agent read` | `hc read [--lines]` |
| `alive <w>` | worker 還在不在 | `agent list` grep | `hc get` 的 `state` |
| `session <w>` | 取 agent 的 session id（transcript 用） | `agent get` 的 `agent_session.value` | 見「session id」 |
| `close <w>` | 收工 | `pane close` | `hc kill`＋`hc rm`（視窗格隨之消失；未驗證則補 `pane.close`） |
| `attach-hint <w>` | 卡住時給使用者的接手指令字串 | `herdr agent attach <p>` | `hc attach <t>`，或 app 內點該格 |

**環境與 hc 的自動訊息**（我的決定，spike 驗證）：

- core 不繼承呼叫者環境，`spawn` 的 `--env K=V` 一律用 `env -u CLAUDECODE -u CLAUDE_CODE_CHILD_SESSION -u CLAUDE_CODE_ENTRYPOINT -u HERDR_ENV -u HERDR_PANE_ID … K=V <cli>` 前綴帶入，同時清掉從 core 繼承的污染變數（清單與 `clis.mjs scrubEnv` 一致）。
- `hc run` 一律加 `--no-notify`，不讓 hc 把 worker 的輪次 note 打進主 session；等待只靠 `mux.py wait`／`send --wait`。
- `mux.py` 呼叫 `hc send` 時移除自己環境中的 `HC_TERMINAL_ID`，讓訊息不被包成 `<hc from … reach="hc send …">`（hc 以呼叫端身分決定是否包裝）。
  spike 若證實移除後仍會包裝，才退回請使用者設 `~/.config/herdr-core/config.toml` 的 `notes = false`，那時另開題問使用者。

狀態值統一成 `done|idle|working|blocked|error|timeout|gone`；兩個後端的原始值在 `mux.py` 內映射，原始輸出放 `raw` 欄。

### 1b. 沒有狀態回報的 CLI（hc 後端）

hc 的 agent 狀態只來自程式自己送的 OSC 7501（`idle`／`working`／`done`／`blocked`／`error`），不從畫面猜。
使用者 2026-11-17 裁決：缺狀態的 CLI **替它補狀態回報**，讓四種 CLI（claude、codex、agy、pi）在 app 內都能當可見 worker。

- 第一步 spike：在 app 內逐一 `hc run --bg` 起四種 CLI，用 `hc get` 看 `status` 是否會變，列出哪些缺。codex 要帶 `--no-daemon`。
- 缺的那幾種，各用該 CLI 的原生擴充點補（例：Claude Code hook、pi extension、codex／agy 的 hook 或 notify 設定），在輪次開始／結束／等人時輸出 OSC 7501。
  OSC 7501 的確切格式由 builder 從 herdr-core 文件或原始碼（`hc schema`、herdr-core repo）查明。
- 整合檔放在各 CLI 對應的 setup 位置（比照 `setup/herdr/pi/`），由 `install.sh` 安裝、uninstall 移除，並有測試。
- 某 CLI 沒有可用的擴充點：該 CLI 在 app 內 `spawn` 報錯並提示改派其他 CLI，寫進文件；回頭向使用者報告，不默默降級。

### 2. 版面（hc 後端）

使用者裁決：worker 切在主 session 旁邊，同 TUI 現行（主 session 最大、最多 6 個、第 7 個起開新 tab）。

- 視窗開著：worker 放進主 session 所在 tab，依 `herdr_layout.py` 現行 `PLANS` 的版型排列。
  實作方式由 builder 經 spike 決定：用 `herdr-app do terminal.open --place … --target <主 pane>` 直接在指定位置開，
  或 `hc run` 加 `herdr.space`／`herdr.tab` label 後用 `pane.swap`／`layout.resize` 調整。
  hc 這支放在 `herdr_layout.py` 內新增 hc 分支，或另開 `app_layout.py`，由 `mux.py spawn` 呼叫。
- 版型做不到完全一樣（比例等）可接受，底線：主 session 不小於其他任一格、不被關、不被搬離原 tab。
- 視窗沒開：worker 照跑（背景，無 label），`spawn` 回傳 `"visible":false`，派工文件提示使用者開 app 後用 `agent.focus` 叫出。（我的決定）
- 第 7 個起：`herdr-app do tab.new --name <worker>`，不重排。

### 3. session id（hc 後端）

hc 不提供 agent session id。我的決定：toolkit 的 SessionStart hook（`herdr-env-context.py` 同檔或新 hook）在
`HC_TERMINAL_ID` 存在時，把 hook 輸入的 `session_id` 寫到 `${XDG_STATE_HOME:-~/.local/state}/plugharbor/hc-sessions/<HC_TERMINAL_ID>`；
`mux.py session <w>` 先用 `hc get` 取該 worker 的 address 再讀檔。`/clear` 會再觸發 SessionStart，檔案隨之更新，self-rotate 靠它偵測 `/clear` 完成。
codex／agy／pi worker 沒有這個 hook 時回 `null`，呼叫端照現行無 session id 的路徑處理。

### 4. self-rotate.sh

改用 `mux.py`：`env` 取自己、`wait` 等閒置、`send` 送 `/clear`／`/reload-plugins`／接續句、`session` 偵測 id 變化、`read` 驗畫面。
重試、逾時、log 格式不變。兩份副本（handoff、unattended）仍需位元組相同。
hc 下 `hc send` 送到自己終端時，**必須確認** slash command 不被包成 `<hc …>` 標籤；若會包裝，改用 `hc keys`／等效方式送原文，或在 `~/.config/herdr-core/config.toml` 的 `notes` 設定上找解法（builder 驗證後決定）。

### 5. 雙顧問與結果回傳

- 開 pane、起 claude、`--agent <plugin>:<agent>`、送題阻塞等待：全改 `mux.py spawn`／`send --wait`。
- 回覆內容：維持現行 `advisor_last_reply.py` 讀 transcript（靠 `mux.py session`）。hc 的 `<hc from>` 回報機制這次不採用，
  避免兩個後端回覆路徑不同。（我的決定）

### 6. hook 與 guard

- `herdr-env-context.py`、`compact-context.py`、`notification.sh`、`bg.mjs detectEnv`：「在不在 herdr 內」改用偵測規則
  （`HC_TERMINAL_ID` 或 `HERDR_ENV=1`）。hook 不呼叫 `mux.py` 子行程（效能），各自內嵌同一條判斷；判斷式要和 `mux.py` 相同，加測試比對。
  注入的說明文字不變長。
- `notification.sh`：hc 下 app 有沒有自己的通知**未驗證**；先比照 TUI 不發桌面通知，有事故再改。（我的決定）
- guards：保留現有兩條；新增等價規則擋 `hc run … claude|codex|agy|pi` 不經 `mux.py`（否則漏帶 model／effort）——
  guard 是字串比對，`mux.py` 內部呼叫不經 Bash 工具不受影響。是否需要新增由 builder 視 `spawn` 是否為唯一入口決定。
- `clis.mjs scrubEnv`：再加濾 `HC_TERMINAL_ID`、`HC_TERMINAL_SOCKET`、`HC_SCOPE`（理由同 `HERDR_PANE_ID`：拋棄式 CLI 不能冒用主 session 身分）。

### 7. 文件

- agent-dispatch SKILL.md 第 5、6 節、`herdr-long-task.md`、advisor-discussion／consultant-desk／shared-preludes（四份複本）、
  handoff／unattended SKILL、autopilot、agent-orchestration：指令全換成 `mux.py` 動作，判斷「在 herdr 內」改成「`mux.py env` 的 backend 不是 none」。
- `herdr-long-task.md` 的安裝、升級、`protocol_mismatch`、`server stop` 段落：保留為 TUI 專屬小節，另加一小段 hc（`hc server status|restart`、`hc update`）。這是唯一允許兩套並列的地方。
- SKILL.md 維持 300 行內；description 不變長。
- **setup／user 層規則**（我的決定：納入範圍，否則 app 內的 agent 會判定「不在 herdr 內」而不派工）：
  - setup 的 home 目錄 `rules/dispatch.md`、`setup/adapters/runtime.md`：「herdr」改指 TUI 或 Herdr.app 皆可，判斷改成「`mux.py env` 不是 none」；字數不增加（拿現有措辭換）。
  - `herdr-env-context.py` 注入文字中的「（HERDR_ENV=1）」改成不綁變數名的說法，長度不變。
  - `install.sh` 的 `herdr integration install claude`：只在有 `herdr` 時執行（現況即如此則不動）；hc 側不需整合安裝。
  - `setup/herdr/hooks/herdr-parent-tag.py`（側欄父子掛載）、`setup/herdr/pi/herdr-tree.ts`：不移植；hc 以 `hc run` 的 parent 關係原生記錄父子，app 側欄是否顯示由 app 決定。

## 驗收

1. `python3 scripts/ci/validate.py` 通過；CI 會跑的測試（pytest、shell、`node --test`）本機全過。
2. `mux.py` 單元測試：兩個後端各用 PATH stub（沿用現有 stub 手法）驗每個動作的指令翻譯與狀態映射；偵測規則含「兩組變數同時存在 → hc」。
3. self-rotate 測試：現有 herdr stub 測試不改語意仍過；新增 hc stub 版。
4. 實機（使用者在 app 內）：claude、codex、agy、pi 各派一個長任務 worker 並確認狀態會變；跑一次雙顧問；觸發一次 self-rotate；各項分開回報。TUI 內同項回歸。
   實機項目由使用者操作或使用者在場時執行，未跑到的標「未驗證」。
5. 各 plugin CHANGELOG、版號依 AGENTS.md 同步；`docs/feature.md` 加一行。

## 留給 builder

- `mux.py` CLI 細節（旗標名、JSON 欄位）、`env K=V` 在 hc 的帶法、`kill`/`rm` 與視窗格關閉的互動。
- hc 版面的具體指令組合（需先開 app 視窗 spike）。
- 是否新增 hc guard。
- 測試檔放哪（沿用各 skill 既有 `tests/`）。
- commit 拆法與 plugin 版號級距（toolkit 有新腳本、行為擴充 → minor）。
