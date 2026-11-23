# herdr／Herdr.app 長任務：指令細節

SKILL.md 第 6 節的補充。派工一律走 `scripts/mux.py`，同一組動作對 herdr TUI 與 Herdr.app（hc）都成立；下面的 `mux.py` 指 `python3 "${CLAUDE_SKILL_DIR}/scripts/mux.py"`。

## mux.py 動作速查

| 動作 | 回傳 |
|---|---|
| `env` | `{"backend":"hc\|herdr\|none","self":…,"window":bool}`；`window` 只在 hc 有意義（Herdr.app 視窗開著）；判斷不出來時 `window:false` 並多一個 `window_error`；本機沒視窗但 `hc machine ls` 已連線的機器有顯示主 session 的視窗時 `window:true` 加 `window_on:<機器>` |
| `spawn --name N --kind <claude\|codex\|agy\|pi> --cwd D [--env K=V]… -- <CLI 參數>` | `{"id":…,"visible":bool[,"pane":…]}` |
| `send <id> (--text T \| --file F) [--wait] [--timeout 秒]` | `{"status":S,"raw":…}` |
| `wait <id> [--timeout 秒]` | `{"status":S,"raw":…}` |
| `read <id> [--lines N]` | 畫面純文字（非 JSON） |
| `alive <id>` | `{"alive":bool}` |
| `session <id>` | `{"session":"<id>"\|null[,"hint":…]}`，給 `advisor_last_reply.py`、`worker_ctx.py` 用 |
| `close <id>` | `{"closed":true}` |
| `attach-hint <id>` | `{"hint":"<請使用者貼的接手指令>"}` |

- `S`：`done|idle|working|blocked|error|timeout|gone`；`done` 與 `idle` 都是「這一輪結束」（hc 的 `done` 會停著不回 `idle`）。兩邊的原始回傳放 `raw`。
- 錯誤：stdout 印 `{"error":kind,"hint":…}`。exit 2 用法錯誤、3 `core_not_running`、4 `no_backend`、1 其他（`cli_not_found`、`window_error`、`spawn_failed`、`backend_error`…）。
- `session` 在 hc 下由 toolkit 的 SessionStart hook 記錄，只有 claude worker 有值，codex／agy／pi 回 `null`；沒裝 toolkit 時一律 `null` 並帶 `hint`（不是時序問題，重取沒用）。
- hc 的 `send`：worker 剛起（turn 0）會先 `hc wait`（至多 60 秒）再加 `--if idle`，status 不是 idle 就不送，回 `{"status":"blocked","hint":…}`；`wait`／`send --wait` 的 `ended:false` 映成 `timeout`（`reason` 在輸出上層，`message` 表示被訊息打斷而非逾時），已結束且沒有狀態映成 `gone`。
- `spawn` 在 hc 下以 `hc run --bg` 起 CLI（已加 `--no-notify`、清掉繼承的污染環境變數、CLI 先解成絕對路徑、codex 自動帶 `--no-daemon`），視窗開著時放進主 session 旁；`send` 時不讓 hc 把訊息包成 `<hc from …>`。

## TUI 專屬：安裝與升級

以下只適用 herdr TUI（`mux.py env` 的 `backend` 是 `herdr`）。Herdr.app 見下一節。

- macOS：`brew install herdr`、`brew services start herdr`。Windows：`powershell -ExecutionPolicy Bypass -c "irm https://herdr.dev/install.ps1 | iex"`，從使用者自己的終端機跑 `herdr server &`。
- `herdr integration install claude`；只有在 herdr pane 裡啟動的 Claude 才被追蹤，主 session 不會出現在 `herdr agent list`。
- `herdr status` 確認 server 在跑。
- 第 7 個 worker 起：`spawn` 先用 `herdr pane layout` 數主 tab 的 worker，已滿 6 個就自己 `herdr tab create --cwd … --label <名稱> --no-focus` 開新 tab、在其 `root_pane` 起 CLI，不切主 session、不跑 `herdr_layout.py`。
- 替別的專案開不回報的長駐獨立 session（不占 6 個 worker 名額）：`herdr tab create --cwd "<cwd>" --label <短名>`，取 `result.root_pane.pane_id`，再 `herdr agent start <名稱> --kind <claude|codex|agy|pi> --pane <pane_id> -- <模型參數>`；不用 `workspace create`（使用者看不到），不用 `pane run` 起 CLI（guard 會擋）。
- 收工重排：`mux.py close` 之後跑 `python3 "${CLAUDE_SKILL_DIR}/scripts/herdr_layout.py" --main "$HERDR_PANE_ID"`（`spawn` 開 worker 時已自動重排，關閉時沒有）。

升級 herdr 後所有指令回 `protocol_mismatch`（`mux.py` 的 `status` 為 `error`、`raw` 含該字樣）：`brew upgrade herdr` 只換 binary，跑中的舊 server 留在記憶體。新 CLI 的私有協定比舊 server 新時，所有 socket API 指令直接回 `protocol_mismatch`，不降級相容；已 attach 的 UI 照常，看不出異狀。Homebrew／mise／Nix 安裝不支援 `herdr update --handoff`，唯一修法是重啟 server，而重啟會終止所有 pane 程序。

- 升級前確認所有 pane 的 agent 都 idle、結果檔已落、worker 沒留半改的檔；升完當下就重啟 server（`herdr server stop` 後重開 `herdr`），不要晚點再重啟。
- 重啟由使用者在 herdr 外的終端機操作：從 pane 內跑 `herdr server stop` 會連自己一起砍。重啟後 layout 還原，Claude pane 靠 session id 自動 `--resume`，working 中的 agent 會被中斷。
- 輪詢拿不到 agent 狀態時，先看原始輸出是不是 `protocol_mismatch`，不要當成 worker 消失去重派。
- 升級前後用 `herdr status server`／`herdr status client` 比 `private_protocol` 與 `private_protocol_compatible`。

## Herdr.app（hc）

- 四種 CLI（claude、codex、agy、pi）在 app 內都原生回報狀態，codex 需 `--no-daemon`（`spawn` 已自動加）。
- 更新：`hc update`（由使用者執行；app 視窗也會提示重啟）。
- **core 的重啟只能請使用者做**：禁止自行 stop／restart core（會中斷所有終端與 worker）。
- core 沒跑（`core_not_running`）：請使用者從 Dock 開 Herdr.app。不要為了確認 core 狀態直接跑 `hc`：hc 會以你的環境自動啟動 core；改用 `mux.py env`／任何 `mux.py` 動作，它先連 socket 判斷，沒跑就直接回錯。
- 視窗沒開：`spawn` 回 `visible:false`，worker 在背景照跑；請使用者開視窗後叫出。
- 版面：第 1 個 worker 在主 session 右側，之後依序往下、往右對切（app 沒有指定比例的指令），主 session 不被切；第 7 個起開新 tab。`close` 後格子自動消失。

## 防睡眠

長任務期間不要蓋上 Mac 螢幕，caffeinate 擋不住；細節見 `background-worker.md`「macOS 防睡眠」。

## cwd 信任檢查（對象是 claude）

Claude Code 的信任會沿用上層目錄：cwd 或任一上層標了 `hasTrustDialogAccepted: true` 就不會跳對話框。

```bash
python3 - "<cwd 絕對路徑>" <<'PY'
import json, os, sys
p = os.path.realpath(sys.argv[1])
projects = json.load(open(os.path.expanduser("~/.claude.json"))).get("projects", {})
trusted = {os.path.realpath(k) for k, v in projects.items() if v.get("hasTrustDialogAccepted")}
d = p
while True:
    if d in trusted:
        print("ok"); sys.exit(0)
    parent = os.path.dirname(d)
    if parent == d:
        break
    d = parent
print("missing")
sys.exit(1)
PY
```

## 等人答完：輪詢

判準是結果檔出現，或那一題從畫面消失，不看狀態燈。有 `Monitor` 就用它跑（上限 30 分鐘，到期重掛）：

```bash
H=<結果檔絕對路徑>; Q='<當前題目的 header 或題號>'
MUX='python3 <scripts/mux.py 絕對路徑>'  # 即上面的 mux.py
while true; do
  [ -f "$H" ] && { echo RESULT; exit 0; }
  $MUX read <id> | tail -24 | grep -q "$Q" || { echo CHANGED; exit 0; }
  $MUX alive <id> | grep -q '"alive": true' || { echo WORKER_GONE; exit 0; }
  sleep 10
done
```

## 中途交接（claude worker context 過大）

worker 每一輪都整份重送 context，沒人盯就會一路長大。`<session>` 取自 `mux.py session <id>` 的 `session` 值（只有 claude worker 有；`null` 就無法量）。量法（印出 token 數）：

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/worker_ctx.py" <session>
```

超過 250,000 且 worker 是 idle、結果檔還沒到，依序送三段 prompt（一律寫成檔，各自 `mux.py send <id> --file 檔 --wait --timeout 540`）：

1. 寫交接檔：

   ```text
   context 已過大，要清空後接續。先把接手所需寫進 <工作區>/_handoff-<名稱>.md，寫完就停，不做其他事。
   固定五節，只寫結論與指路，不貼檔案全文、工具輸出、討論過程：
   ## 目標與驗收方式
   ## 已完成（含檔案路徑／commit）
   ## 已拍板的決定（不要重問）
   ## 試過但排除的方向（與原因）
   ## 下一步（第一個動作具體到檔案或指令）
   未 commit 的改動列出檔案清單。不要刪任何檔。
   ```

2. 確認交接檔存在，用 `mux.py send <id> --text /clear` 送字面 `/clear`。session id 會換新、`<id>` 不變，要再量就重跑 `mux.py session <id>`。
3. 接續：

   ```text
   讀 <工作區>/_handoff-<名稱>.md，從「下一步」接著做。結果寫進 <原結果檔路徑>，寫完照原 prompt 的方式回報：<原回報方式>。不要刪交接檔。
   ```

交接檔由你收工時一起清，worker 不刪。
