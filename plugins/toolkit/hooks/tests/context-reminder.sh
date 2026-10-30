#!/usr/bin/env bash
# context-size-reminder hook 驗證。
# HOME 一律導到暫存目錄，絕不碰真的 ~/.claude/context-reminder。
set -euo pipefail
PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
fail() { echo "FAIL: $1"; exit 1; }

PY=""
for c in python3 python; do
  if "$c" -c "" >/dev/null 2>&1; then PY="$c"; break; fi
done
[ -n "$PY" ] || fail "找不到可執行的 python"

HOOK="$PLUGIN_DIR/hooks/context-size-reminder.py"
H="$TMP/home"; mkdir -p "$H"; T="$TMP/t.jsonl"
# 寫一筆主鏈 assistant（context＝cache_read），外加一筆更晚的 sidechain 大 context 當干擾
turn() {
  "$PY" -c 'import json,sys
n=int(sys.argv[1])
print(json.dumps({"type":"assistant","message":{"usage":{"input_tokens":2,"cache_read_input_tokens":n,"cache_creation_input_tokens":0}}}))
print(json.dumps({"type":"assistant","isSidechain":True,"message":{"usage":{"input_tokens":2,"cache_read_input_tokens":900000}}}))' "$1" >> "$T"
}
run() { printf '{"session_id":"s1","transcript_path":"%s","hook_event_name":"Stop"}' "$T" | HOME="$H" USERPROFILE="$H" "$PY" "$HOOK"; }

turn 120000; [ -z "$(run)" ] || fail "120K 不該提醒（也不該被 sidechain 900K 誤觸）"
turn 230000; OUT="$(run)"; echo "$OUT" | grep -q '"systemMessage"' || fail "230K 應提醒"
echo "$OUT" | grep -q '230K' || fail "訊息應帶 230K：$OUT"
turn 240000; [ -z "$(run)" ] || fail "同一級距（200～250K）不重複提醒"
turn 260000; [ -n "$(run)" ] || fail "跨到下一級距 260K 應再提醒"
turn 150000; [ -z "$(run)" ] || fail "掉回門檻下不提醒"
turn 210000; [ -n "$(run)" ] || fail "compact 後再長回 210K 應重新提醒"
OUT="$(echo 'not json' | HOME="$H" "$PY" "$HOOK")"; RC=$?
[ "$RC" = 0 ] && [ -z "$OUT" ] || fail "壞輸入應靜默 exit 0"
OUT="$(printf '{"session_id":"s2","transcript_path":"%s/none.jsonl"}' "$TMP" | HOME="$H" "$PY" "$HOOK")"
[ -z "$OUT" ] || fail "transcript 不存在應靜默"

echo "PASS: context-reminder（9 項）"
