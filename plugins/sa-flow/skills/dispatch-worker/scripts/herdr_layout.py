#!/usr/bin/env python3
"""依 worker 數重排 herdr tab：主 session 永遠最大（3 個時四格等大）。

用法：herdr_layout.py --main <pane_id> [--worker <pane_id> ...]
  不給 --worker：同 tab 其餘 pane 全當 worker，依目前版面順序擺放。
  超過 6 個報錯（第 7 個起請開新 tab）。
  主 session 外框標「★ <名稱>」：--label 指定名稱；不給則沿用已有的 ★ 標籤，沒有就取 tab 名稱。
做法：先把所有 worker 搬到暫存 tab（主 session 變滿版），再依版型逐一搬回。
pane move 會保留 pane 內的程序與 herdr agent 身分（2026-10-05 實測）。
"""
import argparse, json, subprocess, sys

# Windows 預設 cp950：印中文會亂碼、印 emoji 直接炸 UnicodeEncodeError。
# 與 parse_foxpro.py 同一做法，腳本自己處理，不靠呼叫端設 PYTHONUTF8。
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

MAX_WORKERS = 6


def herdr(*args):
    out = subprocess.run(["herdr", *args], capture_output=True, text=True)
    try:
        data = json.loads(out.stdout)
    except json.JSONDecodeError:
        sys.exit(f"herdr {' '.join(args)} 非 JSON 輸出：{out.stdout or out.stderr}")
    if "error" in data:
        sys.exit(f"herdr {' '.join(args)} 失敗：{data['error']}")
    return data["result"]


def tab_of(pane):
    return herdr("pane", "get", pane)["pane"]["tab_id"]


def place(pane, tab, target, direction, ratio):
    r = herdr("pane", "move", pane, "--tab", tab, "--split", direction,
              "--target-pane", target, "--ratio", str(ratio), "--no-focus")
    if not r["move_result"]["changed"]:
        sys.exit(f"pane move {pane} → {target} 未生效")


# 每一步：(要擺的 worker 序號, 切誰, 方向, 被切者保留比例)；"M" 代表主 session
PLANS = {
    1: [(0, "M", "right", 0.5)],
    2: [(0, "M", "right", 0.5), (1, 0, "down", 0.5)],
    3: [(0, "M", "right", 0.5), (1, "M", "down", 0.5), (2, 0, "down", 0.5)],
    4: [(0, "M", "right", 1 / 3), (1, 0, "right", 0.5),
        (2, 0, "down", 0.5), (3, 1, "down", 0.5)],
    5: [(0, "M", "right", 0.25), (3, 0, "down", 0.5),
        (1, 0, "right", 1 / 3), (2, 1, "right", 0.5), (4, 3, "right", 0.5)],
    6: [(0, "M", "right", 0.25), (3, 0, "down", 0.5),
        (1, 0, "right", 1 / 3), (2, 1, "right", 0.5),
        (4, 3, "right", 1 / 3), (5, 4, "right", 0.5)],
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--main", required=True)
    ap.add_argument("--worker", action="append", default=[])
    ap.add_argument("--label")
    a = ap.parse_args()
    tab = tab_of(a.main)
    current = herdr("pane", "get", a.main)["pane"].get("label") or ""
    if a.label or not current.startswith("★"):
        name = a.label or next(t.get("label") or "" for t in herdr("tab", "list")["tabs"] if t["tab_id"] == tab)
        herdr("pane", "rename", a.main, f"★ {name}".strip())
    workers = a.worker or [p["pane_id"] for p in herdr("pane", "layout", "--pane", a.main)["layout"]["panes"]
                           if p["pane_id"] != a.main]
    if len(workers) > MAX_WORKERS:
        sys.exit(f"worker {len(workers)} 個，超過 {MAX_WORKERS}；第 7 個起請開新 tab")
    if not workers:
        return
    # 1. 全部搬到暫存 tab，主 session 回到滿版
    hold = herdr("pane", "move", workers[0], "--new-tab", "--label", "layout-hold",
                 "--no-focus")["move_result"]["pane"]["tab_id"]
    for w in workers[1:]:
        place(w, hold, workers[0], "right", 0.5)
    # 2. 依版型搬回（暫存 tab 搬空後 herdr 自動關閉）
    for idx, target, direction, ratio in PLANS[len(workers)]:
        tgt = a.main if target == "M" else workers[target]
        place(workers[idx], tab, tgt, direction, ratio)
    lay = herdr("pane", "layout", "--pane", a.main)["layout"]
    print(f"focused\t{lay['focused_pane_id']}")
    for p in lay["panes"]:
        r = p["rect"]
        print(f"{p['pane_id']}\t{r['width']}x{r['height']}\t@({r['x']},{r['y']})")


if __name__ == "__main__":
    main()
