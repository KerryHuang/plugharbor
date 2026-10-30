#!/bin/bash
# qa-verify 前置檢查。同事第一次用之前先跑；缺什麼停在那裡說怎麼補。
#   preflight.sh <workspace-root>
WS="$1"; MISSING=0
say() { printf "%-26s %s\n" "$1" "$2"; }
[ -n "$WS" ] || { echo "用法: preflight.sh <workspace-root>" >&2; exit 2; }

PY=$(command -v python || command -v python3)
if [ -n "$PY" ]; then say "python" "✅ ($PY)"; else say "python" "❌ 請安裝 Python 3"; MISSING=1; fi

if [ -n "$PY" ] && "$PY" -c "import yaml" 2>/dev/null; then say "PyYAML" "✅"
else say "PyYAML" "❌ ${PY:-python} -m pip install pyyaml"; MISSING=1; fi

if [ -f "$WS/.claude/live-drive.local.md" ]; then say "live-drive.local.md" "✅"
else say "live-drive.local.md" "❌ 缺 $WS/.claude/live-drive.local.md（登入網址／帳密，本機檔）——skill 會問你並代寫"; MISSING=1; fi

say "MCP（chrome-devtools／唯讀 DB 工具／linear）" "由 skill Step 0 以 ToolSearch 檢查"
exit $MISSING
