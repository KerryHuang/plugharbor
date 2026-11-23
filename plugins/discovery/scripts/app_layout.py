#!/usr/bin/env python3
"""Herdr.app（hc 後端）的 worker 版面：worker 切在主 session 旁，主 pane 永遠最大。

用法：
  app_layout.py place --main <主 pane> --terminal <hc 位址>
    → {"pane":str,"visible":true[,"tab":str]}；失敗 {"error":"layout_failed","hint":…} exit 1。
  app 的格子在 hc kill 後自動消失，不需重排，所以沒有 relayout。

版型（Ruling F，spike 筆記第 6 項：app 沒有指定比例的指令，只能對半切）：
  第 1 個 worker 從主 pane 往右切；之後只切「最新的 worker pane」（輪流 down／right）；
  主 pane 之後不再被切，所以始終 ≥ 任一 worker。第 7 個起 `terminal.keep --terminal <t>` 不帶 place
  （官方說明：不帶 place 即開新 tab，tab 內只有 worker），不重排。
  worker 數 = 主 pane 所在 tab 內主 pane 以外的終端數。
  MAX_WORKERS 與 herdr_layout.py 相同（TUI 版為 6）；該檔 import 會執行 stream 設定，故複製常數。

放置做法是 spike 的 D：呼叫端先 `hc run --bg` 得到 hc 位址，這裡 `pane.focus` 到被切的 pane，
再 `terminal.keep --terminal <tN> --place right|down`（位置相對「目前 focus 的 pane」）。
放完把 focus 還給主 pane（新 pane 會搶 focus，會打斷使用者在主 session 的輸入），盡力而為：還原失敗不影響回報。
ls→focus→keep→還原 focus 是臨界區，用 flock（Windows 用 msvcrt.locking）序列化（並行派工時 focus 是全域狀態，不鎖會切到錯的 pane）。
鎖檔：${XDG_STATE_HOME:-~/.local/state}/plugharbor/app-layout.lock。
"""
import argparse, json, os, subprocess, sys, time
from contextlib import contextmanager
from pathlib import Path

try:
    import fcntl
except ImportError:  # Windows
    fcntl = None
    import msvcrt

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

MAX_WORKERS = 6  # 同 herdr_layout.py
KEEP_RETRIES = 10  # 實機：spawn 後立刻 keep 會回 no running terminal


class LayoutError(Exception):
    pass


def app(*args):
    # HERDR_APP_ON=<機器>：視窗開在 hc 已連線的另一台（mux.py remote_main 找到的），經 hc exec 操作那邊的 herdr-app
    on = os.environ.get("HERDR_APP_ON")
    argv = ["hc", "exec", "--on", on, "--", "herdr-app", *args] if on else ["herdr-app", *args]
    try:
        r = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8")
    except FileNotFoundError:
        raise LayoutError("找不到 herdr-app")
    if r.returncode != 0:
        raise LayoutError(f"herdr-app {' '.join(args)} 失敗（exit {r.returncode}）：{(r.stderr or r.stdout).strip()[:200]}")
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        raise LayoutError(f"herdr-app {' '.join(args)} 非 JSON 輸出：{r.stdout.strip()[:200]}")


def keep(*args):
    """terminal.keep；hc run 剛回傳時 app 可能還沒看到該終端（no running terminal），短暫重試。"""
    for _ in range(KEEP_RETRIES - 1):
        try:
            return app("do", "terminal.keep", *args)
        except LayoutError as e:
            if "no running terminal" not in str(e):
                raise
            time.sleep(0.3)
    return app("do", "terminal.keep", *args)


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


@contextmanager
def locked():
    base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    path = Path(base) / "plugharbor" / "app-layout.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        if fcntl:
            fcntl.flock(f, fcntl.LOCK_EX)
        else:
            f.seek(0)  # msvcrt 鎖「目前位置起 1 byte」：各程序都從 0 鎖才互斥
            msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
        try:
            yield
        finally:
            if fcntl:
                fcntl.flock(f, fcntl.LOCK_UN)
            else:
                f.seek(0)
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)


def restore_focus(main):
    try:
        app("do", "pane.focus", "--pane", main)
    except LayoutError:
        pass  # 盡力而為：worker 已放好，不能因此回報失敗


def place(main, terminal):
    with locked():
        terms = terminals_of_tab(app("ls"), main)
        if terms is None:
            raise LayoutError(f"ls 找不到主 pane {main}")
        workers = [t for t in terms if t.get("pane") != main and t.get("terminal") != terminal]
        n = len(workers)
        try:
            if n >= MAX_WORKERS:
                # 不帶 --place：開新 tab，tab 內只有這個 worker
                kept = keep("--terminal", terminal)
            else:
                if n == 0:
                    target, direction = main, "right"
                else:
                    target, direction = workers[-1].get("pane"), ("down" if n % 2 else "right")
                app("do", "pane.focus", "--pane", target)
                kept = keep("--terminal", terminal, "--place", direction)
        finally:
            restore_focus(main)
    result = {"pane": find_key(kept, "pane"), "visible": True}
    if n >= MAX_WORKERS:
        result["tab"] = find_key(kept, "tab")
    return result


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("place")
    p.add_argument("--main", required=True)
    p.add_argument("--terminal", required=True)
    a = ap.parse_args()
    try:
        result = place(a.main, a.terminal)
    except LayoutError as e:
        print(json.dumps({"error": "layout_failed", "hint": str(e)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
