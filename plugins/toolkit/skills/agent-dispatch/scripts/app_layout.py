#!/usr/bin/env python3
"""Herdr.app（hc 後端）的 worker 版面：worker 切在主 session 旁，主 pane 永遠最大。

用法：
  app_layout.py place --main <主 pane> --terminal <hc 位址> [--name <worker 名稱>]
    → {"pane":str,"visible":true[,"tab":str]}；失敗 {"error":"layout_failed","hint":…} exit 1。
  app_layout.py relayout --main <主 pane>
    → {"main":str,"workers":N}。app 的格子在 hc kill 後自動消失，不需重排；只回報現況。

版型（Ruling F，spike 筆記第 6 項：app 沒有指定比例的指令，只能對半切）：
  第 1 個 worker 從主 pane 往右切；之後只切「最新的 worker pane」（輪流 down／right）；
  主 pane 之後不再被切，所以始終 ≥ 任一 worker。第 7 個起 `tab.new --name <worker>`，不重排。
  worker 數 = 主 pane 所在 tab 內主 pane 以外的終端數。
  MAX_WORKERS 與 herdr_layout.py 相同（TUI 版為 6）；該檔 import 會執行 stream 設定，故複製常數。

放置做法是 spike 的 D：呼叫端先 `hc run --bg` 得到 hc 位址，這裡 `pane.focus` 到被切的 pane，
再 `terminal.keep --terminal <tN> --place right|down`（位置相對「目前 focus 的 pane」）。
放完把 focus 還給主 pane（新 pane 會搶 focus，會打斷使用者在主 session 的輸入）。
"""
import argparse, json, subprocess, sys

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

MAX_WORKERS = 6  # 同 herdr_layout.py


class LayoutError(Exception):
    pass


def app(*args):
    try:
        r = subprocess.run(["herdr-app", *args], capture_output=True, text=True, encoding="utf-8")
    except FileNotFoundError:
        raise LayoutError("找不到 herdr-app")
    if r.returncode != 0:
        raise LayoutError(f"herdr-app {' '.join(args)} 失敗（exit {r.returncode}）：{(r.stderr or r.stdout).strip()[:200]}")
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        raise LayoutError(f"herdr-app {' '.join(args)} 非 JSON 輸出：{r.stdout.strip()[:200]}")


def find_key(data, key):
    stack = [data]
    while stack:
        cur = stack.pop(0)
        if isinstance(cur, dict):
            if key in cur:
                return cur[key]
            stack.extend(cur.values())
        elif isinstance(cur, list):
            stack.extend(cur)
    return None


def terminals_of_tab(ls, main_pane):
    """回傳主 pane 所在 tab 的終端清單（依 ls 順序）；找不到主 pane 回 None。"""
    stack = [ls]
    while stack:
        cur = stack.pop(0)
        if isinstance(cur, dict):
            terms = cur.get("terminals")
            if isinstance(terms, list) and any(isinstance(t, dict) and t.get("pane") == main_pane for t in terms):
                return terms
            stack.extend(cur.values())
        elif isinstance(cur, list):
            stack.extend(cur)
    return None


def place(main, terminal, name):
    terms = terminals_of_tab(app("ls"), main)
    if terms is None:
        raise LayoutError(f"ls 找不到主 pane {main}")
    workers = [t for t in terms if t.get("pane") != main and t.get("terminal") != terminal]
    n = len(workers)
    if n >= MAX_WORKERS:
        tab = app("do", "tab.new", "--name", name or terminal)
        pane = find_key(tab, "pane")
        if pane:
            app("do", "pane.focus", "--pane", pane)
            app("do", "terminal.keep", "--terminal", terminal, "--place", "right")
        return {"pane": pane, "visible": True, "tab": find_key(tab, "tab")}
    if n == 0:
        target, direction = main, "right"
    else:
        target, direction = workers[-1].get("pane"), ("down" if n % 2 else "right")
    app("do", "pane.focus", "--pane", target)
    kept = app("do", "terminal.keep", "--terminal", terminal, "--place", direction)
    pane = find_key(kept, "pane")
    app("do", "pane.focus", "--pane", main)
    return {"pane": pane, "visible": True}


def relayout(main):
    terms = terminals_of_tab(app("ls"), main)
    if terms is None:
        raise LayoutError(f"ls 找不到主 pane {main}")
    return {"main": main, "workers": len([t for t in terms if t.get("pane") != main])}


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("place")
    p.add_argument("--main", required=True)
    p.add_argument("--terminal", required=True)
    p.add_argument("--name")
    sub.add_parser("relayout").add_argument("--main", required=True)
    a = ap.parse_args()
    try:
        result = place(a.main, a.terminal, a.name) if a.cmd == "place" else relayout(a.main)
    except LayoutError as e:
        print(json.dumps({"error": "layout_failed", "hint": str(e)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
