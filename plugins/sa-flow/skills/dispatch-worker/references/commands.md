# 指令補充

通用指令以 `herdr --skill` 為準；這裡只放 SKILL.md 沒寫全的。

## 安裝與起 server（一次性）

- macOS：`brew install herdr`、`brew services start herdr`。Windows：`powershell -ExecutionPolicy Bypass -c "irm https://herdr.dev/install.ps1 | iex"`，從使用者自己的終端機跑 `herdr server &`。
- 兩台都要 `herdr integration install claude`；只有在 herdr pane 裡啟動的 Claude 才被追蹤，主 session 不會出現在 `herdr agent list`。
- `herdr status` 確認 server 在跑。

## 升級 herdr（`protocol_mismatch`）

`brew upgrade herdr` 只換 binary，跑中的舊 server 留在記憶體。新 CLI 的私有協定比舊 server 新時，**所有 socket API 指令直接回 `protocol_mismatch`**，不降級相容；已 attach 的 UI 照常，看不出異狀。Homebrew／mise／Nix 安裝不支援 `herdr update --handoff`，唯一修法是重啟 server，而重啟會終止所有 pane 程序。

- 升級前確認所有 pane 的 agent 都 idle、`_pm-run.json` 已落檔、worker 沒留半改的檔；**升完當下就重啟 server**（`herdr server stop` 後重開 `herdr`），不要「先升、晚點再重啟」——中間這段 dispatch-worker 的輪詢、prompt 與 hook 回報全部失效。
- 重啟由使用者在終端機操作：從 pane 內跑 `herdr server stop` 會連自己一起砍。重啟後 layout 還原，Claude pane 靠 session id 自動 `--resume`，working 中的 agent 會被中斷。
- **輪詢拿不到 agent 狀態時，先看原始輸出是不是 `protocol_mismatch`**，不要當成 worker 消失去重派（曾在一次 herdr 升級後，協調端的 `agent list`／`pane read`／`agent prompt` 全失效，worker 其實還活著）。
- 升級前後用 `herdr status server`／`herdr status client` 比 `private_protocol` 與 `private_protocol_compatible`。

## cwd 檢查（Step 0）

```bash
python3 - "<cwd 絕對路徑>" <<'PY'
import json, os, sys
p = os.path.realpath(sys.argv[1])
projects = json.load(open(os.path.expanduser("~/.claude.json"))).get("projects", {})
ok = any(os.path.realpath(k) == p for k in projects)
print("ok" if ok else "missing")
sys.exit(0 if ok else 1)
PY
```

`missing` → 不派工，請使用者先在該目錄開一次 Claude Code 並通過對話框。

## 等人答完：輪詢（Step 5）

判準是結果檔出現或該題從畫面消失，不看狀態燈。Claude Code 有 `Monitor` 時用它跑（上限 30 分鐘，到期重掛）。

```bash
H=<結果檔絕對路徑>; Q='<當前題目的 header 或題號>'
while true; do
  [ -f "$H" ] && { echo HANDOFF; exit 0; }
  herdr agent read <名稱> | tail -24 | grep -q "$Q" || { echo CHANGED; exit 0; }
  herdr agent list | grep -q '"name":"<名稱>"' || { echo WORKER_GONE; exit 0; }
  sleep 10
done
```

等「下一題或完工」則在第二條前加 `herdr agent read <名稱> | tail -12 | grep -q "Enter to select" && { echo ASKING; exit 0; }`。

## 中途交接（Step 5）

量 context（session id 從 `herdr agent list` 該 worker 的 `agent_session.value` 取；`/clear` 後會換新，要重抓）：

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/spec-chain/scripts/ctx.py <sessionId 前綴>
```

三段 prompt 一律寫成檔再 `"$(cat <檔>)"` 送（Step 1 規則），各自 `--wait --timeout 540000`：

① 寫交接檔：

```text
context 已過大，要清空後接續。先把接手所需寫進 <工作區>/_handoff-<名稱>.md，寫完就停，不做其他事。
固定五節，只寫結論與指路，不貼檔案全文、工具輸出、討論過程：
## 目標與驗收標準
## 已完成（含檔案路徑／commit）
## 已拍板的決定（不要重問）
## 試過但排除的方向（與原因）
## 下一步（第一個動作具體到檔案或指令）
未 commit 的改動列出檔案清單。不要刪任何檔。
```

② 確認 `_handoff-<名稱>.md` 存在後送字面 `/clear`（實測：herdr 送的 `/clear` 會被當指令執行，context 回到開場約 74K）。

③ 接續：

```text
讀 <工作區>/_handoff-<名稱>.md，從「下一步」接著做。結果寫進 <原結果檔路徑>，寫完照原 prompt 的方式回報：<原回報方式>。不要刪交接檔。
```
