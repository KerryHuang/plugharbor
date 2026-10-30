# herdr 長任務：指令細節

SKILL.md 第 4 節的補充。通用操作以官方 `herdr --skill` 為準。

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

worker 每一輪都整份重送 context，沒人盯就會一路長大。量法：

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

## 升級 herdr 後全部指令回 `protocol_mismatch`

`brew upgrade herdr` 只換 binary，跑中的舊 server 還在記憶體，協定不合時所有 socket 指令都回 `protocol_mismatch`，但 worker 其實還活著。修法只有重啟 server，會中斷所有 pane，所以由使用者在 worker 都 idle 時、從 herdr 外的終端機操作。

---

主動回報、`--wait` 搭配、cwd 檢查、判讀表與中途交接，改寫自另一個內部 plugin 的 `dispatch-worker` skill（2026-10-29 版）；那邊的版面重排、sidebar metadata、顧問 agent 屬該 plugin 專屬，未移植。
