# herdr 長任務：指令細節

SKILL.md 第 4 節的補充。通用操作以官方 `herdr --skill` 為準。

## 安裝與升級

- macOS：`brew install herdr`、`brew services start herdr`。Windows：`powershell -ExecutionPolicy Bypass -c "irm https://herdr.dev/install.ps1 | iex"`，從使用者自己的終端機跑 `herdr server &`。
- `herdr integration install claude`；只有在 herdr pane 裡啟動的 Claude 才被追蹤，主 session 不會出現在 `herdr agent list`。
- `herdr status` 確認 server 在跑。

升級 herdr 後所有指令回 `protocol_mismatch`：`brew upgrade herdr` 只換 binary，跑中的舊 server 留在記憶體。新 CLI 的私有協定比舊 server 新時，所有 socket API 指令直接回 `protocol_mismatch`，不降級相容；已 attach 的 UI 照常，看不出異狀。Homebrew／mise／Nix 安裝不支援 `herdr update --handoff`，唯一修法是重啟 server，而重啟會終止所有 pane 程序。

- 升級前確認所有 pane 的 agent 都 idle、結果檔已落、worker 沒留半改的檔；升完當下就重啟 server（`herdr server stop` 後重開 `herdr`），不要晚點再重啟。
- 重啟由使用者在 herdr 外的終端機操作：從 pane 內跑 `herdr server stop` 會連自己一起砍。重啟後 layout 還原，Claude pane 靠 session id 自動 `--resume`，working 中的 agent 會被中斷。
- 輪詢拿不到 agent 狀態時，先看原始輸出是不是 `protocol_mismatch`，不要當成 worker 消失去重派。
- 升級前後用 `herdr status server`／`herdr status client` 比 `private_protocol` 與 `private_protocol_compatible`。

## cwd 信任檢查（對象是 claude）

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

## 等人答完：輪詢

判準是結果檔出現，或那一題從畫面消失，不看狀態燈。有 `Monitor` 就用它跑（上限 30 分鐘，到期重掛）：

```bash
H=<結果檔絕對路徑>; Q='<當前題目的 header 或題號>'
while true; do
  [ -f "$H" ] && { echo RESULT; exit 0; }
  herdr pane read <pane_id> | tail -24 | grep -q "$Q" || { echo CHANGED; exit 0; }
  herdr agent list | grep -q '"name":"<名稱>"' || { echo WORKER_GONE; exit 0; }
  sleep 10
done
```

## 中途交接（claude worker context 過大）

worker 每一輪都整份重送 context，沒人盯就會一路長大。量法（印出 token 數）：

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/worker_ctx.py" <agent_session.value>
```

超過 250,000 且 worker 是 idle、結果檔還沒到，依序送三段 prompt（一律寫成檔再 `"$(cat 檔)"`，各自 `--wait --timeout 540000`）：

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

2. 確認交接檔存在，送字面 `/clear`。session id 會換新、名稱不變，要再量就重抓 `agent_session.value`。
3. 接續：

   ```text
   讀 <工作區>/_handoff-<名稱>.md，從「下一步」接著做。結果寫進 <原結果檔路徑>，寫完照原 prompt 的方式回報：<原回報方式>。不要刪交接檔。
   ```

交接檔由你收工時一起清，worker 不刪。
