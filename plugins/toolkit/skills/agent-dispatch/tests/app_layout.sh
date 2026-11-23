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
import json, os, sys, time
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
    time.sleep(0.2)  # 拉大並行時的競態視窗
    st = json.load(open(state_f, encoding="utf-8"))
    st["focus"] = opt("--pane"); save(); print('{"ok":true}')
elif args[:2] == ["do", "terminal.keep"]:
    nr = os.environ.get("STUB_NOT_RUNNING")  # 模擬 hc run 剛回傳、app 還沒看到該終端
    left = int(open(nr).read() or 0) if nr else 0
    if left > 0:
        open(nr, "w").write(str(left - 1))
        print(json.dumps({"error": 'no running terminal "%s"' % opt("--terminal")}, indent=2)); sys.exit(1)
    with open(os.environ["STUB_LOG"], "a", encoding="utf-8") as f:
        f.write("keep-target %s %s\n" % (opt("--terminal"), st["focus"]))
    if "--place" not in args:  # 不帶 place：開新 tab，tab 內只有 worker
        pane = "pw%s" % opt("--terminal")
        st["focus"] = pane; save()
        print(json.dumps({"pending": True, "terminal": opt("--terminal"), "pane": pane, "tab": "tb2"})); sys.exit(0)
    tgt = next(p for p in st["panes"] if p["pane"] == st["focus"])
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
else:
    print("unexpected: " + " ".join(args), file=sys.stderr); sys.exit(9)
STUB
chmod +x "$TMP/herdr-app"

fail=0
check() { # 說明 條件結果(0=成立)
  if [ "$2" -eq 0 ]; then echo "PASS $1"; else echo "FAIL $1"; fail=1; fi
}
reset() { # 初始：主 pane p1（t0）佔滿 100x40
  export STUB_STATE="$TMP/state" STUB_LOG="$TMP/log" XDG_STATE_HOME="$TMP/xdg"
  echo '{"focus":"p1","panes":[{"pane":"p1","terminal":"t0","rect":{"x":0,"y":0,"w":100,"h":40}}]}' > "$STUB_STATE"
  : > "$STUB_LOG"
}
placew() { # 序號
  PATH="$TMP:/usr/bin:/bin" "$PY" "$SCRIPT" place --main p1 --terminal "t$1"
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

# 7 個 worker：第 7 個 terminal.keep 不帶 place（新 tab）；不呼叫 tab.new、不重排、回 worker 自己的 pane、focus 還給主 pane
reset
for i in 1 2 3 4 5 6; do placew "$i" > /dev/null; done
panes_of() { "$PY" -c "import json; print(json.dumps(json.load(open('$STUB_STATE'))['panes']))"; }
before="$(panes_of)"
: > "$TMP/log"
placew 7 > "$TMP/out.7"
grep -q 'do terminal.keep --terminal t7$' "$TMP/log"; check "7 workers：terminal.keep 不帶 place" $?
! grep -q 'tab.new' "$TMP/log"; check "7 workers：不呼叫 tab.new" $?
! grep -Eq 'pane\.close|pane\.move|pane\.swap' "$TMP/log"; check "7 workers：未重排（無 close／move／swap）" $?
[ "$(panes_of)" = "$before" ]; check "7 workers：主 tab 版面不變" $?
grep -q '"pane": "pwt7"' "$TMP/out.7" && grep -q '"tab": "tb2"' "$TMP/out.7"; check "7 workers：回 worker 的 pane 與新 tab" $?
[ "$(tail -1 "$TMP/log")" = "do pane.focus --pane p1" ]; check "7 workers：focus 還給主 pane" $?

# 還原 focus 失敗：worker 已放好，仍回 visible true
reset
cat > "$TMP/herdr-app.wrap" <<WRAP
#!/bin/sh
if [ "\$1" = do ] && [ "\$2" = pane.focus ] && [ "\$4" = p1 ] && [ -f "$TMP/placed" ]; then exit 3; fi
[ "\$2" = terminal.keep ] && touch "$TMP/placed"
exec "$TMP/herdr-app.real" "\$@"
WRAP
mv "$TMP/herdr-app" "$TMP/herdr-app.real"; mv "$TMP/herdr-app.wrap" "$TMP/herdr-app"; chmod +x "$TMP/herdr-app"
out="$(placew 1)"; rc=$?
[ "$rc" -eq 0 ] && echo "$out" | grep -q '"visible": true'; check "還原 focus 失敗：仍回 visible true" $?
rm -f "$TMP/placed"; mv "$TMP/herdr-app.real" "$TMP/herdr-app"

# 並行：兩個 place 同時跑，flock 序列化 → 第 2 個看到第 1 個的 worker，目標不同，主 pane 只被切一次
reset
placew 1 > "$TMP/out.c1" & p1=$!
placew 2 > "$TMP/out.c2" & p2=$!
wait "$p1"; wait "$p2"
targets=$(grep '^keep-target' "$TMP/log" | awk '{print $3}')
[ "$(echo "$targets" | sort -u | wc -l | tr -d ' ')" -eq 2 ]; check "並行：兩次 keep 目標不同" $?
[ "$(echo "$targets" | grep -c '^p1$')" -eq 1 ]; check "並行：主 pane 只被切一次" $?
[ "$(area p1)" -ge "$(area p2)" ] && [ "$(area p1)" -ge "$(area p3)" ]; check "並行：主 pane 面積 >= 任一 worker" $?

# 剛 spawn 的終端 app 還沒看到（no running terminal）：重試後放好
reset
echo 2 > "$TMP/nr"
out="$(STUB_NOT_RUNNING="$TMP/nr" placew 1 || true)"
echo "$out" | grep -q '"visible": true' && r=0 || r=1; check "app 尚未看到終端：重試後 visible true" $r
[ "$(grep -c '^do terminal.keep' "$TMP/log")" -eq 3 ] && r=0 || r=1; check "app 尚未看到終端：keep 共呼叫 3 次" $r

# ls 找不到主 pane：回 layout_failed，exit 非 0
reset
set +e
PATH="$TMP:/usr/bin:/bin" "$PY" "$SCRIPT" place --main pX --terminal t1 > "$TMP/out.x" 2>&1; rc=$?
set -e
[ "$rc" -ne 0 ] && grep -q layout_failed "$TMP/out.x"; check "找不到主 pane：layout_failed" $?

# HERDR_APP_ON：視窗在另一台機器，每個 herdr-app 呼叫都經 hc exec --on <機器> -- herdr-app
reset
cat > "$TMP/hc" <<HC
#!/bin/sh
echo "hc \$*" >> "$TMP/hc.log"
[ "\$1 \$2 \$3 \$4 \$5" = "exec --on mac -- herdr-app" ] || exit 9
shift 5; exec "$TMP/herdr-app" "\$@"
HC
chmod +x "$TMP/hc"; : > "$TMP/hc.log"
out="$(HERDR_APP_ON=mac placew 1)"
echo "$out" | grep -q '"visible": true'; check "遠端視窗：回 visible true" $?
grep -q '^hc exec --on mac -- herdr-app do terminal.keep --terminal t1 --place right$' "$TMP/hc.log"; check "遠端視窗：keep 經 hc exec 送到該機器" $?
[ "$(grep -c '^hc exec --on mac -- herdr-app ' "$TMP/hc.log")" -eq "$(grep -vc '^keep-target' "$TMP/log")" ] && r=0 || r=1; check "遠端視窗：所有 herdr-app 呼叫都經 hc exec" $r
rm "$TMP/hc"

exit $fail
