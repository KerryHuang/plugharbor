#!/usr/bin/env python3
"""spec-chain PM 續跑檢查——把 `_pm-run.json` 的宣稱與現實對帳。

PM 被壓縮、中斷或重開之後，用這支重建「哪一棒到哪了、誰還活著、有沒有人在看」。

**不採信檔案內容**：pane 還在不在問 herdr，產出檔在不在問檔案系統。
檔案只提供「PM 當初以為的樣子」，兩者的差就是 PM 離開期間發生的事。

用法：
    pm_resume.py <_pm-run.json 路徑> [--root <workspace 根>]

`--root` 用來解析 stage.output 的相對路徑，預設為當前工作目錄。

**結束碼一律 0**，判定看輸出文字。（`--wait` 逾時回 exit 1 卻不是失敗這件事已經害過一次，
本 skill 不再用結束碼傳遞「需要處置」。）
"""
import json
import os
import subprocess
import sys

# Windows 預設 cp950：印中文會亂碼、印 emoji 直接炸 UnicodeEncodeError。
# 與 parse_foxpro.py 同一做法，腳本自己處理，不靠呼叫端設 PYTHONUTF8。
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

STATUS_KNOWN = {"dispatched", "stopped", "verified", "rejected"}


def live_panes():
    """回傳 {pane_id: agent}；herdr 不可用時回 (None, 原因)。"""
    try:
        p = subprocess.run(
            ["herdr", "agent", "list"], capture_output=True, text=True, timeout=20
        )
    except FileNotFoundError:
        return None, "找不到 herdr 指令"
    except (OSError, subprocess.SubprocessError) as e:
        return None, "herdr 無法執行：%s" % e
    if p.returncode != 0:
        msg = (p.stderr or p.stdout or "").strip().splitlines()
        return None, "herdr agent list 失敗（exit %d）：%s" % (
            p.returncode, msg[0] if msg else "無輸出")
    try:
        data = json.loads(p.stdout)
    except ValueError:
        return None, "herdr agent list 回傳非 JSON"
    agents = (data.get("result") or {}).get("agents") or []
    return {a["pane_id"]: a for a in agents if a.get("pane_id")}, None


def verdict(status, pane_alive, out_exists):
    """(標記, 判定, 下一步)。pane_alive 為 None 代表無法確認（herdr 不可用）。"""
    if status == "verified":
        if not out_exists:
            return "🔴", "已驗收但產出檔不見了", "查檔案是否被移動或誤刪，別直接重派"
        return "  ", "已驗收", "不必重做"
    if status == "rejected":
        return "⚠️", "回派修正中", "直接重驗檔案，不要等 worker 回報"
    if status not in STATUS_KNOWN:
        return "🔴", "status 值不認得：%r" % status, "修正 _pm-run.json"
    # dispatched / stopped
    # 產出檔是硬證據，先判它——pane 死活不影響「已經產出了該驗收」這個結論，
    # 所以 herdr 不可用也答得出來。
    if out_exists:
        return "⚠️", "已有產出（PM 離開期間完成）", "進驗收"
    if pane_alive is None:
        return "⚠️", "無產出，pane 狀態不明（herdr 不可用）", "先修好 herdr 再判"
    if pane_alive:
        return "  ", "pane 還在、尚無產出", "herdr agent read 看是在跑還是停在提問"
    return "🔴", "pane 不見且無產出", "worker 死了或被誤關——重派這一棒"


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    path = argv[0]
    root = os.getcwd()
    if "--root" in argv:
        i = argv.index("--root") + 1
        if i >= len(argv):
            print("🔴 --root 後面要接 workspace 根的絕對路徑。")
            return 0
        root = argv[i]

    if not os.path.exists(path):
        print("沒有 %s——這是本功能目錄的第一輪，或 PM 從沒寫過狀態。" % path)
        print("照 worker-protocol.md「執行狀態與續跑」節建一份，不要憑記憶重建進度。")
        return 0
    try:
        with open(path, encoding="utf-8") as f:
            state = json.load(f)
    except ValueError as e:
        print("🔴 %s 不是合法 JSON：%s" % (path, e))
        print("手動修好再跑；不要繞過它憑記憶重建進度。")
        return 0

    panes, why = live_panes()
    if why:
        print("⚠️ %s——pane 存活無法確認，以下判定不完整。\n" % why)

    stages = state.get("stages") or []
    if not stages:
        print("⚠️ %s 裡沒有 stages，等於沒有狀態。" % path)
        return 0

    print("功能目錄：%s" % state.get("feature_dir", "(未記)"))
    print("票號：%s｜skill 版本：%s｜更新於：%s"
          % (state.get("ticket", "-"), state.get("skill_commit", "-"),
             state.get("updated", "-")))
    print("")

    todo = 0
    any_alive = False
    for st in stages:
        pane = st.get("pane")
        alive = None if panes is None else (pane in panes)
        if alive:
            any_alive = True
        out = st.get("output")
        out_exists = bool(out) and os.path.exists(
            out if os.path.isabs(out) else os.path.join(root, out))
        mark, said, nxt = verdict(st.get("status"), alive, out_exists)
        if mark.strip():
            todo += 1
        print("%s %-18s %-16s pane=%-7s %s" % (
            mark, st.get("stage", "?"), st.get("worker", "-"), pane or "-", said))
        print("     → %s" % nxt)

    watch = state.get("watch")
    if watch is not None and not isinstance(watch, dict):
        print("\n⚠️ watch 欄位不是物件（%r），以未掛等待處理；格式見 worker-protocol.md" % (watch,))
        watch = None
    watch = watch or {}
    armed = watch.get("armed")
    print("")
    if any_alive and armed is not True:
        todo += 1
        print("🔴 有 worker 還活著，但 watch.armed 不是 true——**無人看守**。")
        print("     → 立刻重掛 herdr agent wait，並把 watch 欄位更新回 true")
    elif any_alive:
        print("   watch 已掛在 %s" % (watch.get("target") or "?"))
    else:
        print("   沒有活著的 worker，不需要掛等待。")

    print("\n需要處置：%d 項" % todo)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
