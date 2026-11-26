#!/usr/bin/env bash
# worker_ctx.py 行為測試：取指定 session 最後一筆 usage 的 context 大小；副本與 toolkit 一致
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SCRIPT="$HERE/../scripts/worker_ctx.py"
PY="$(command -v python3 || command -v python)"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
fail=0
check() { if [ "$2" -eq 0 ]; then echo "PASS $1"; else echo "FAIL $1"; fail=1; fi; }
run() { HOME="$TMP" USERPROFILE="$TMP" "$PY" "$SCRIPT" "$@"; }

mkdir -p "$TMP/.claude/projects/p"
cat > "$TMP/.claude/projects/p/abc-123.jsonl" <<'EOF'
{"type":"assistant","message":{"usage":{"input_tokens":1,"cache_read_input_tokens":1000,"cache_creation_input_tokens":10}}}
{"type":"assistant","message":{"usage":{"input_tokens":2,"cache_read_input_tokens":200000,"cache_creation_input_tokens":300}}}
{"type":"user","message":{"content":"tool result"}}
EOF
OUT="$(run abc-123)"; check "印最後一筆 usage 三項合計" "$([ "$OUT" = 200302 ]; echo $?)"

set +e; run nope >/dev/null 2>&1; rc=$?; set -e
check "找不到 session 回 1" "$([ "$rc" -eq 1 ]; echo $?)"

# 副本同步：在本 repo 內與 toolkit 的同名腳本必須一致
OTHER="$HERE/../../../../toolkit/skills/agent-dispatch/scripts/worker_ctx.py"
if [ -f "$OTHER" ]; then check "與 toolkit 副本一致" "$(cmp -s "$SCRIPT" "$OTHER"; echo $?)"; fi

exit $fail
