#!/usr/bin/env bash
# feedback-capture／feedback-reminder hook 的行為驗證（佇列腳本屬 skill，不在此測）。
# HOME（與 Windows 的 USERPROFILE）一律導到暫存目錄，絕不碰真的 ~/.claude/feedback-loop。
set -euo pipefail
PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
fail() { echo "FAIL: $1"; exit 1; }

PY=""
for c in python3 python; do
  if "$c" -c "" >/dev/null 2>&1; then PY="$c"; break; fi
done
[ -n "$PY" ] || fail "找不到可執行的 python"

CAPTURE="$PLUGIN_DIR/hooks/feedback-capture.py"
REMINDER="$PLUGIN_DIR/hooks/feedback-reminder.py"
H="$TMP/home"; Q="$H/.claude/feedback-loop/queue.jsonl"; mkdir -p "$H"
run() { HOME="$H" USERPROFILE="$H" "$PY" "$@"; }
lines() { [ -f "$Q" ] && wc -l < "$Q" | tr -d ' ' || echo 0; }
payload() { "$PY" -c 'import json,sys; print(json.dumps({"prompt": sys.argv[1], "session_id": "s1", "cwd": "/w"}, ensure_ascii=False))' "$1"; }

# --- feedback-capture ---
# 1) 命中寫入，stdout 為空
OUT="$(payload "不對，我說過要先跑測試" | run "$CAPTURE")"; RC=$?
[ "$RC" = 0 ] || fail "capture exit $RC"
[ -z "$OUT" ] || fail "capture stdout 不該有輸出：$OUT"
[ "$(lines)" = 1 ] || fail "命中後佇列應有 1 筆"
run - "$Q" <<'PYEOF' || fail "佇列內容不符"
import json, sys
r = json.loads(open(sys.argv[1], encoding="utf-8").read().splitlines()[0])
assert set(r) == {"id", "ts", "session_id", "cwd", "matched", "excerpt"}, r
assert r["session_id"] == "s1" and r["cwd"] == "/w", r
assert "不對" in r["matched"] and "我說過" in r["matched"], r
assert r["excerpt"].startswith("不對"), r
PYEOF

# 2) 英文命中
payload "That's not what I asked for" | run "$CAPTURE" >/dev/null
[ "$(lines)" = 2 ] || fail "英文糾正未命中"

# 3) 未命中不寫
payload "幫我整理這份報告的格式" | run "$CAPTURE" >/dev/null
[ "$(lines)" = 2 ] || fail "未命中卻寫入"

# 4) 長貼上（> 2000 字）跳過
LONG="不對$(printf 'x%.0s' $(seq 1 2100))"
payload "$LONG" | run "$CAPTURE" >/dev/null
[ "$(lines)" = 2 ] || fail "長貼上未跳過"

# 5) slash command 跳過
payload "/some-command 不對" | run "$CAPTURE" >/dev/null
[ "$(lines)" = 2 ] || fail "slash command 未跳過"

# 7) 壞掉的 stdin：exit 0、stdout 空
OUT="$(printf 'not json{' | run "$CAPTURE")" || fail "壞 stdin 應 exit 0"
[ -z "$OUT" ] || fail "壞 stdin 不該有 stdout"
OUT="$(printf '\xff\xfe\x00' | run "$CAPTURE")" || fail "非 UTF-8 stdin 應 exit 0"
[ -z "$OUT" ] || fail "非 UTF-8 stdin 不該有 stdout"

# 8) Windows 式 cp950 stdio 仍正確解中文
payload "又來了" | PYTHONIOENCODING=cp950 run "$CAPTURE" >/dev/null
[ "$(lines)" = 3 ] || fail "cp950 stdio 下未命中"

# 9) 佇列目錄無法建立（feedback 是檔案）也 exit 0
H2="$TMP/home2"; mkdir -p "$H2/.claude"; : > "$H2/.claude/feedback-loop"
OUT="$(payload "不對" | HOME="$H2" USERPROFILE="$H2" "$PY" "$CAPTURE" 2>/dev/null)" || fail "寫入失敗應 exit 0"
[ -z "$OUT" ] || fail "寫入失敗不該有 stdout"

# 10) 問句型／建議型糾正命中，需求描述裡的「應該要」不誤抓（獨立 HOME，不動上面的筆數）
H3="$TMP/home3"; Q3="$H3/.claude/feedback-loop/queue.jsonl"; mkdir -p "$H3"
for s in "怎麼停了？" "pane 完成主 session 都不知道，應該要 pane 回報才對" "PM 改 Done 不就不能追蹤子票了嗎？"; do
  payload "$s" | HOME="$H3" USERPROFILE="$H3" "$PY" "$CAPTURE" >/dev/null
done
payload "客戶應該要能自行設定流水號" | HOME="$H3" USERPROFILE="$H3" "$PY" "$CAPTURE" >/dev/null
payload 'Sub-agent "smoke" completed. 結果不對，改用 B' | HOME="$H3" USERPROFILE="$H3" "$PY" "$CAPTURE" >/dev/null
[ "$(wc -l < "$Q3" | tr -d ' ')" = 3 ] || fail "問句型糾正筆數不符"

# --- feedback-reminder ---
R="$TMP/rhome"; RF="$R/.claude/feedback-loop"
rrun() { HOME="$R" USERPROFILE="$R" "$PY" "$REMINDER"; }
mkq() {  # $1=筆數 $2=幾天前
  mkdir -p "$RF"; "$PY" - "$RF/queue.jsonl" "$1" "$2" <<'PYEOF'
import json, sys
from datetime import datetime, timedelta
ts = (datetime.now().astimezone() - timedelta(days=int(sys.argv[3]))).isoformat(timespec="seconds")
with open(sys.argv[1], "w", encoding="utf-8") as fh:
    for i in range(int(sys.argv[2])):
        fh.write(json.dumps({"id": f"t{i}", "ts": ts, "excerpt": "範例"}, ensure_ascii=False) + "\n")
PYEOF
}

# 10) 檔案不存在：無輸出
OUT="$(rrun)" || fail "reminder 應 exit 0"
[ -z "$OUT" ] || fail "無佇列不該輸出"

# 11) 未達門檻（3 筆、1 天前、從未回顧）：無輸出
mkq 3 1
[ -z "$(rrun)" ] || fail "未達門檻卻輸出"

# 12) 筆數達門檻：輸出合法 JSON，兩種訊息都有
mkq 10 1
OUT="$(rrun)"
echo "$OUT" | "$PY" -c '
import json, sys
d = json.load(sys.stdin)
assert "10 條" in d["systemMessage"], d
assert d["hookSpecificOutput"]["hookEventName"] == "SessionStart", d
ctx = d["hookSpecificOutput"]["additionalContext"]
assert ctx.startswith(d["systemMessage"]) and "AskUserQuestion" in ctx, d
' || fail "達筆數門檻的輸出不符：$OUT"

# 13) 筆數少但從未回顧且最早一筆 ≥ 7 天：輸出
mkq 1 8
echo "$(rrun)" | grep -q "從未回顧" || fail "久未回顧未提醒"

# 14) 上次回顧在近期：無輸出
mkq 1 8; date -u +%Y-%m-%dT%H:%M:%S+00:00 > "$RF/last-review"
[ -z "$(rrun)" ] || fail "近期回顧過卻輸出"

# 15) 上次回顧 ≥ 7 天前：輸出
echo "2000-01-01T00:00:00+00:00" > "$RF/last-review"
echo "$(rrun)" | grep -q "上次回顧" || fail "上次回顧已久未提醒"

# 16) 佇列含壞列、last-review 壞掉：不崩、壞列也算筆數
printf 'garbage\n{"ts":"bad"}\n' >> "$RF/queue.jsonl"; echo "nonsense" > "$RF/last-review"
OUT="$(rrun)" || fail "壞資料應 exit 0"
[ -z "$OUT" ] || echo "$OUT" | "$PY" -c 'import json,sys; json.load(sys.stdin)' || fail "壞資料時輸出不是合法 JSON"

# 16b) ts 為 null／數字的列也不崩、照算筆數
mkq 9 1; printf '{"ts":null}\n{"ts":5}\n' >> "$RF/queue.jsonl"; rm -f "$RF/last-review"
echo "$(rrun)" | grep -q "11 條" || fail "ts 非字串的列讓提醒失效"


# 16d) 歸檔中斷留下的 processing 檔也算未處理
: > "$RF/queue.jsonl"; mkq 0 0; cp /dev/null "$RF/queue.jsonl"
"$PY" -c 'import json,sys
with open(sys.argv[1],"w",encoding="utf-8") as f:
    [f.write(json.dumps({"id":f"p{i}","ts":"2000-01-01T00:00:00+00:00"})+"\n") for i in range(10)]' "$RF/queue.processing.jsonl"
echo "$(rrun)" | grep -q "10 條" || fail "processing 檔未計入"
rm -f "$RF/queue.processing.jsonl"

# 17) 空佇列：無輸出
: > "$RF/queue.jsonl"; rm -f "$RF/last-review"
[ -z "$(rrun)" ] || fail "空佇列不該輸出"

# --- hooks.json 的啟動殼：PATH 上的 python3 是壞掉的 stub 也要找到能跑的直譯器 ---
CMD="$("$PY" -c 'import json,sys; d=json.load(open(sys.argv[1],encoding="utf-8")); print([h["hooks"][0]["command"] for h in d["hooks"]["UserPromptSubmit"] if "feedback-capture" in h["hooks"][0]["command"]][0])' "$PLUGIN_DIR/hooks/hooks.json")"
FB="$TMP/fakebin"; LH="$TMP/lhome"; mkdir -p "$FB" "$LH/plugin/hooks"
cp "$CAPTURE" "$LH/plugin/hooks/"
export CLAUDE_PLUGIN_ROOT="$LH/plugin"
printf '#!/bin/sh\nexit 9009\n' > "$FB/python3"; chmod +x "$FB/python3"
REAL="$(command -v "$PY")"; printf '#!/bin/sh\nexec "%s" "$@"\n' "$REAL" > "$FB/python"; chmod +x "$FB/python"
payload "不是這樣" > "$TMP/in.json"   # 用檔案餵：啟動殼找不到直譯器時不讀 stdin，pipe 會讓 payload 吃 SIGPIPE
HOME="$LH" PATH="$FB:/usr/bin:/bin" eval "$CMD" < "$TMP/in.json" || fail "啟動殼應 exit 0"
[ -s "$LH/.claude/feedback-loop/queue.jsonl" ] || fail "python3 是 stub 時啟動殼沒退到 python"
rm "$FB/python"
HOME="$LH" PATH="$FB:/usr/bin:/bin" eval "$CMD" < "$TMP/in.json" || fail "找不到直譯器時啟動殼也應 exit 0"

echo "PASS: feedback-hooks"
