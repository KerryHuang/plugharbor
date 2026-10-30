#!/usr/bin/env bash
# auto-session-title hook 行為驗證：只套用 skill 建議的標題，不覆寫手動命名。
# HOME（與 Windows 的 USERPROFILE）一律導到暫存目錄，絕不碰真的 ~/.claude/sessions。
set -euo pipefail
PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
fail() { echo "FAIL: $1"; exit 1; }

PY=""
for c in python3 python; do
  if "$c" -c "" >/dev/null 2>&1; then PY="$c"; break; fi
done
[ -n "$PY" ] || fail "找不到可執行的 python"

HOOK="$PLUGIN_DIR/hooks/auto-session-title.py"
H="$TMP/home"; mkdir -p "$H/.claude/sessions"
T="$TMP/t.jsonl"
SUG='建議 session 標題（請複製到輸入框執行）：/rename [Bug] ABC-123 登入頁 flag 不同步'
TITLE='[Bug] ABC-123 登入頁 flag 不同步'

session() {  # $1=nameSource $2=name
  "$PY" -c 'import json,sys; print(json.dumps({"sessionId":"s1","nameSource":sys.argv[1],"name":sys.argv[2]}, ensure_ascii=False))' "$1" "$2" > "$H/.claude/sessions/1.json"
}
# 依序寫入 transcript：u=使用者 prompt、a=assistant 文字、r=tool_result
transcript() {
  "$PY" - "$T" "$@" <<'PYEOF'
import json, sys
out, items = sys.argv[1], sys.argv[2:]
with open(out, "w", encoding="utf-8") as fh:
    for it in items:
        kind, text = it.split(":", 1)
        if kind == "u":
            rec = {"type": "user", "message": {"content": text}}
        elif kind == "r":
            rec = {"type": "user", "message": {"content": [{"type": "tool_result", "content": text}]}}
        else:
            rec = {"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
PYEOF
}
run() {
  "$PY" -c 'import json,sys; print(json.dumps({"session_id":"s1","transcript_path":sys.argv[1]}))' "$T" \
    | HOME="$H" USERPROFILE="$H" "$PY" "$HOOK"
}
title_of() { "$PY" -c 'import json,sys; s=sys.stdin.read(); print(json.loads(s)["hookSpecificOutput"]["sessionTitle"] if s.strip() else "")'; }

# 1) 上一回合有建議（夾在 tool_result 之後的最後一段文字）→ 套用，蓋過自動命名
session hook "linear-triage 啟"
transcript "u:/sdlc:linear-triage ABC-123" "a:先讀票" "r:ok" "a:報告…
$SUG"
[ "$(run | title_of)" = "$TITLE" ] || fail "建議標題未套用"

# 2) 當輪 prompt 已寫入 transcript 仍抓得到上一回合
transcript "u:/sdlc:linear-triage ABC-123" "a:$SUG" "u:確認"
[ "$(run | title_of)" = "$TITLE" ] || fail "當輪 prompt 已寫入時未套用"

# 3) 使用者手動 /rename 過 → 不覆寫
session user "我自己取的"
transcript "u:x" "a:$SUG"
[ -z "$(run)" ] || fail "覆寫了手動命名"

# 4) 已是同名 → 不重複輸出
session hook "$TITLE"
[ -z "$(run)" ] || fail "同名仍重複輸出"

# 5) 只是提到 /rename、沒有固定句型 → 不誤抓
session derived "x-3f"
transcript "u:x" "a:model 無法自己執行 /rename 這類內建指令"
[ -z "$(run)" ] || fail "誤抓一般的 /rename 字樣"

# 6) 建議出現在更早的回合 → 不套用（只看上一回合）
transcript "u:x" "a:$SUG" "u:下一題" "a:好的"
[ -z "$(run)" ] || fail "套用了更早回合的建議"

echo "auto-session-title: all passed"
