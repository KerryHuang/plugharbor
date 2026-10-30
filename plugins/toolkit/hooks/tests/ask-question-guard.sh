#!/usr/bin/env bash
# ask-question-guard hook 的行為驗證：題目太短、選項沒說明、沒標（推薦）要擋；合格的放行；壞輸入 fail-open。
set -euo pipefail
PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
fail() { echo "FAIL: $1"; exit 1; }

PY=""
for c in python3 python; do
  if "$c" -c "" >/dev/null 2>&1; then PY="$c"; break; fi
done
[ -n "$PY" ] || fail "找不到可執行的 python"
GUARD="$PLUGIN_DIR/hooks/ask-question-guard.py"

# $1=question  $2=第一個選項 label  $3=第一個選項 description
payload() {
  "$PY" -c '
import json, sys
q, l1, d1 = sys.argv[1:4]
print(json.dumps({"tool_name": "AskUserQuestion", "tool_input": {"questions": [{
  "question": q, "header": "測試", "multiSelect": False,
  "options": [{"label": l1, "description": d1},
              {"label": "維持現狀", "description": "不改任何東西，問題會繼續發生，之後還要再處理一次。"}]}]}},
  ensure_ascii=False))' "$1" "$2" "$3"
}
GOOD_Q="存檔格式從 v1 改成 v2 後，舊裝置上的進度要怎麼處理？選錯的話小孩的金幣和關卡進度可能會被清掉。"
GOOD_D="開機時自動把 v1 轉成 v2，舊進度全部保留；要多寫一段轉換程式和測試。"
denied() { echo "$1" | grep -q '"permissionDecision": "deny"'; }

# 1) 合格：放行、不輸出
OUT="$(payload "$GOOD_Q" "自動轉換舊檔（推薦）" "$GOOD_D" | "$PY" "$GUARD")"
[ -z "$OUT" ] || fail "合格題目不該被擋：$OUT"

# 2) 題目太短
OUT="$(payload "要選 A 還是 B？" "自動轉換舊檔（推薦）" "$GOOD_D" | "$PY" "$GUARD")"
denied "$OUT" || fail "短題目沒被擋"
echo "$OUT" | grep -q "question" || fail "退回訊息沒指出 question 太短"

# 3) 選項沒說明
OUT="$(payload "$GOOD_Q" "自動轉換舊檔（推薦）" "" | "$PY" "$GUARD")"
denied "$OUT" || fail "空 description 沒被擋"
echo "$OUT" | grep -q "自動轉換舊檔" || fail "退回訊息沒指出是哪個選項"

# 4) 沒標（推薦）；（建議）與 Recommended 都不算
for L in "自動轉換舊檔" "自動轉換舊檔（建議）" "自動轉換舊檔 (Recommended)"; do
  OUT="$(payload "$GOOD_Q" "$L" "$GOOD_D" | "$PY" "$GUARD")"
  denied "$OUT" || fail "沒標（推薦）沒被擋：$L"
done

# 5) 預設值類標「（預設）」也算（sa-flow／sdlc 的 preludes 規定）
OUT="$(payload "$GOOD_Q" "自動轉換舊檔（預設）" "$GOOD_D" | "$PY" "$GUARD")"
[ -z "$OUT" ] || fail "標（預設）不該被擋：$OUT"

# 6) 其他工具、壞 stdin：fail-open
OUT="$(echo '{"tool_name":"Bash","tool_input":{"command":"ls"}}' | "$PY" "$GUARD")"
[ -z "$OUT" ] || fail "非 AskUserQuestion 不該輸出"
for BAD in '[]' '{"tool_name":"AskUserQuestion","tool_input":{"questions":"x"}}' '{"tool_name":"AskUserQuestion","tool_input":{"questions":["x",{"question":"這一題的題目寫得夠長，發現了什麼、要決定的事情，以及選錯之後會造成的後果，全部都有交代清楚了","options":["a"]}]}}'; do
  OUT="$(echo "$BAD" | "$PY" "$GUARD" 2>&1)" || fail "怪結構應 fail-open（exit 0）：$BAD"
  [ -z "$OUT" ] || fail "怪結構不該輸出：$BAD → $OUT"
done
OUT="$(echo 'not json' | "$PY" "$GUARD")"; RC=$?
[ "$RC" = 0 ] && [ -z "$OUT" ] || fail "壞 stdin 應 fail-open"

echo "PASS: ask-question-guard"
