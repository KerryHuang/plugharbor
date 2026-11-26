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
        if kind == "j":  # 原樣寫入一筆 JSON（帶時間欄位、標題紀錄等）
            fh.write(text + "\n"); continue
        if kind == "u":
            rec = {"type": "user", "message": {"content": text}}
        elif kind == "r":
            rec = {"type": "user", "message": {"content": [{"type": "tool_result", "content": text}]}}
        else:
            rec = {"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
PYEOF
}
run() {  # $1=使用者這次的 prompt（選填）
  "$PY" -c 'import json,sys; print(json.dumps({"session_id":"s1","transcript_path":sys.argv[1],"prompt":sys.argv[2]}))' "$T" "${1:-}" \
    | env -u HC_TERMINAL_ID HOME="$H" USERPROFILE="$H" "$PY" "$HOOK"
}
ctx_of() { "$PY" -c 'import json,sys; s=sys.stdin.read(); print(json.loads(s)["hookSpecificOutput"].get("additionalContext","") if s.strip() else "")'; }
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

# 7) 句中引用建議句型（說明機制時）→ 不誤抓；行首的才算
transcript "u:x" "a:hook 看到「建議 session 標題：/rename …」，要等下一次送出才套用"
[ -z "$(run)" ] || fail "誤抓句中引用的建議句型"

# 8) 使用者在 assistant 還在跑時送出（排隊），送出時建議行還沒寫出 → 下一次送出補套用
A_SUG="$("$PY" -c 'import json,sys; print(json.dumps({"type":"assistant","timestamp":"2026-11-26T04:10:11.337Z","message":{"content":[{"type":"text","text":sys.argv[1]}]}}, ensure_ascii=False))' "$SUG")"
transcript "u:x" "j:$A_SUG" \
  'j:{"type":"user","promptSource":"system","origin":{"kind":"task-notification"},"message":{"content":"<task-notification>done</task-notification>"}}' \
  'j:{"type":"user","sentAtMs":1795666205252,"origin":{"kind":"human"},"message":{"content":"排隊的問題"}}' \
  "a:回答排隊的問題"
[ "$(run | title_of)" = "$TITLE" ] || fail "排隊送出的 prompt 擋住了建議標題"

# 9) 同樣情境但 prompt 是建議行寫出之後才送出 → 視為已處理，不套用
transcript "u:x" "j:$A_SUG" \
  'j:{"type":"user","sentAtMs":1795666299999,"origin":{"kind":"human"},"message":{"content":"之後才送"}}' \
  "a:好的"
[ -z "$(run)" ] || fail "建議行之後送出的 prompt 不該再補套用"

# 10) 提到標題 → 注入目前標題與來源；sessions 檔的 derived 名稱標明不是標題
session derived "proj-x-b5"
transcript 'j:{"type":"ai-title","aiTitle":"數獨遊戲"}' 'j:{"type":"custom-title","customTitle":"舊的手動標題"}' \
  'j:{"type":"ai-title","aiTitle":"4、6、9格數獨遊戲"}' "u:x" "a:好"
CTX="$(run "標題改了嗎？" | ctx_of)"
case "$CTX" in *"4、6、9格數獨遊戲"*) ;; *) fail "沒注入最新 ai-title：$CTX" ;; esac
case "$CTX" in *"舊的手動標題"*) ;; *) fail "沒注入 custom-title：$CTX" ;; esac
case "$CTX" in *"proj-x-b5"*) ;; *) fail "沒標出 sessions 檔名稱：$CTX" ;; esac
case "$CTX" in *"不是標題"*) ;; *) fail "沒說明 derived 名稱不是標題：$CTX" ;; esac

# 11) 沒提到標題 → 不注入
[ -z "$(run "下一題" | ctx_of)" ] || fail "沒提到標題也注入了"

# 12) 在 herdr 內 → 加上 terminal title 與分頁名
FAKE="$TMP/bin"; mkdir -p "$FAKE"
cat > "$FAKE/hc" <<'SH'
#!/bin/sh
echo '{"title":"✳ 終端機標題","labels":{"herdr.tab":"tb1"}}'
SH
cat > "$FAKE/herdr-app" <<'SH'
#!/bin/sh
echo '{"spaces":[{"tabs":[{"id":"tb1","name":"分頁名稱"}]}]}'
SH
chmod +x "$FAKE/hc" "$FAKE/herdr-app"
CTX="$("$PY" -c 'import json,sys; print(json.dumps({"session_id":"s1","transcript_path":sys.argv[1],"prompt":"rename 有生效嗎"}))' "$T" \
  | PATH="$FAKE:$PATH" HC_TERMINAL_ID=t1 HOME="$H" USERPROFILE="$H" "$PY" "$HOOK" | ctx_of)"
case "$CTX" in *"終端機標題"*"分頁名稱"*) ;; *) fail "沒注入 herdr 標題與分頁名：$CTX" ;; esac

# 13) 沒有任何標題紀錄 → 寫明「transcript 沒有紀錄」，不寫成「無標題」
transcript "u:x" "a:好"
CTX="$(run "標題呢" | ctx_of)"
case "$CTX" in *"沒有紀錄"*) ;; *) fail "沒有紀錄時沒照實寫：$CTX" ;; esac

echo "auto-session-title: all passed"
