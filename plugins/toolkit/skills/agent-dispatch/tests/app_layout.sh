#!/usr/bin/env bash
# app_layout.py 行為測試：PATH 只含 stub 目錄與 /usr/bin:/bin，stub 的 herdr-app 模擬 app 的 pane 樹
# （每次 split 對半），絕不碰真的 herdr-app。
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SCRIPT="$HERE/../scripts/app_layout.py"
PY="$(command -v python3)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

cat > "$TMP/herdr-app" <<STUB
#!$PY
import json, os, sys
state_f = os.environ["STUB_STATE"]
args = sys.argv[1:]
with open(os.environ["STUB_LOG"], "a", encoding="utf-8") as f:
    f.write(" ".join(args) + "\n")
st = json.load(open(state_f, encoding="utf-8"))
def save():
    json.dump(st, open(state_f, "w", encoding="utf-8"))
def opt(name):
    return args[args.index(name) + 1]
if args[0] == "ls":
    print(json.dumps({"spaces": [{"tabs": [{"tab": "tb1", "terminals": [
        {"terminal": p["terminal"], "pane": p["pane"], "name": p.get("name")} for p in st["panes"]]}]}]}))
elif args[:2] == ["do", "pane.focus"]:
    st["focus"] = opt("--pane"); save(); print('{"ok":true}')
elif args[:2] == ["do", "terminal.keep"]:
    tgt = next((p for p in st["panes"] if p["pane"] == st["focus"]), None)
    if tgt is None:  # focus 在別的 tab（tab.new 的 pane）：不影響主 tab
        print(json.dumps({"pending": True, "terminal": opt("--terminal"), "pane": "pother", "tab": "tb2"})); sys.exit(0)
    r = tgt["rect"]
    if opt("--place") == "right":
        w = r["w"] // 2
        new = {"x": r["x"] + r["w"] - w, "y": r["y"], "w": w, "h": r["h"]}
        r["w"] -= w
    else:
        h = r["h"] // 2
        new = {"x": r["x"], "y": r["y"] + r["h"] - h, "w": r["w"], "h": h}
        r["h"] -= h
    pane = "p%d" % (len(st["panes"]) + 1)
    st["panes"].append({"pane": pane, "terminal": opt("--terminal"), "rect": new})
    st["focus"] = pane; save()
    print(json.dumps({"pending": True, "terminal": opt("--terminal"), "pane": pane, "tab": "tb1"}))
elif args[:2] == ["do", "tab.new"]:
    print(json.dumps({"space": "sp1", "tab": "tb2", "pane": "pnew", "terminal": "tnew"}))
else:
    print("unexpected: " + " ".join(args), file=sys.stderr); sys.exit(9)
STUB
chmod +x "$TMP/herdr-app"

fail=0
check() { # 說明 條件結果(0=成立)
  if [ "$2" -eq 0 ]; then echo "PASS $1"; else echo "FAIL $1"; fail=1; fi
}
reset() { # 初始：主 pane p1（t0）佔滿 100x40
  export STUB_STATE="$TMP/state" STUB_LOG="$TMP/log"
  echo '{"focus":"p1","panes":[{"pane":"p1","terminal":"t0","rect":{"x":0,"y":0,"w":100,"h":40}}]}' > "$STUB_STATE"
  : > "$STUB_LOG"
}
placew() { # 序號
  PATH="$TMP:/usr/bin:/bin" "$PY" "$SCRIPT" place --main p1 --terminal "t$1" --name "w$1"
}
area() { # pane 面積
  "$PY" -c "import json,sys; s=json.load(open('$STUB_STATE')); r=next(p for p in s['panes'] if p['pane']=='$1')['rect']; print(r['w']*r['h'])"
}

# 1 個 worker：切主 pane 右側，主 pane 沒被 close／move
reset
out="$(placew 1)"
echo "$out" | grep -q '"visible": true'; check "1 worker：回 visible true" $?
grep -q 'do terminal.keep --terminal t1 --place right' "$TMP/log"; check "1 worker：放在主 pane 右側" $?
! grep -Eq 'pane\.close|pane\.move|pane\.swap|tab\.move' "$TMP/log"; check "1 worker：主 pane 未被 close／move／swap" $?
[ "$(grep -c 'pane.focus --pane p1' "$TMP/log")" -ge 1 ]; check "1 worker：focus 還給主 pane" $?

# 6 個 worker：主 pane 只被切一次，主 pane 面積 >= 任一 worker，其餘切法的目標都不是主 pane
reset
for i in 1 2 3 4 5 6; do placew "$i" > /dev/null; done
splits_main=$(awk '/pane.focus --pane/{t=$NF} /terminal.keep/{if(t=="p1")c++} END{print c+0}' "$TMP/log")
[ "$splits_main" -eq 1 ]; check "6 workers：主 pane 只被切一次" $?
main_area=$(area p1)
ok=0
for p in p2 p3 p4 p5 p6 p7; do [ "$main_area" -ge "$(area $p)" ] || ok=1; done
check "6 workers：主 pane 面積 >= 任一 worker" $ok
! grep -q 'tab.new' "$TMP/log"; check "6 workers：不開新 tab" $?
grep -q 'terminal.keep --terminal t2 --place down' "$TMP/log" && grep -q 'terminal.keep --terminal t3 --place right' "$TMP/log"; check "6 workers：之後輪流 down／right" $?

# 7 個 worker：第 7 個呼叫 tab.new，既有版面不重排（不再 keep 到主 tab、不動主 pane）
reset
for i in 1 2 3 4 5 6; do placew "$i" > /dev/null; done
panes_of() { "$PY" -c "import json; print(json.dumps(json.load(open('$STUB_STATE'))['panes']))"; }
before="$(panes_of)"
: > "$TMP/log"
placew 7 > "$TMP/out.7"
grep -q 'do tab.new --name w7' "$TMP/log"; check "7 workers：呼叫 tab.new --name w7" $?
! grep -Eq 'pane\.close|pane\.move|pane\.swap' "$TMP/log"; check "7 workers：未重排（無 close／move／swap）" $?
[ "$(panes_of)" = "$before" ]; check "7 workers：主 tab 版面不變" $?
grep -q '"tab": "tb2"' "$TMP/out.7"; check "7 workers：回報新 tab" $?

# ls 找不到主 pane：回 layout_failed，exit 非 0
reset
set +e
PATH="$TMP:/usr/bin:/bin" "$PY" "$SCRIPT" place --main pX --terminal t1 > "$TMP/out.x" 2>&1; rc=$?
set -e
[ "$rc" -ne 0 ] && grep -q layout_failed "$TMP/out.x"; check "找不到主 pane：layout_failed" $?

# relayout：只回報現況，不動版面
reset
for i in 1 2 3; do placew "$i" > /dev/null; done
: > "$TMP/log"
PATH="$TMP:/usr/bin:/bin" "$PY" "$SCRIPT" relayout --main p1 | grep -q '"workers": 3'; check "relayout：回報 3 個 worker" $?
! grep -q 'do ' "$TMP/log"; check "relayout：不改動版面" $?

exit $fail
