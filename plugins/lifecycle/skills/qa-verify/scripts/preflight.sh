#!/bin/bash
# qa-verify 前置檢查。第一次用之前先跑；缺什麼停在那裡說怎麼補。
#   preflight.sh <專案根>
WS="$1"; MISSING=0
say() { printf "%-26s %s\n" "$1" "$2"; }
[ -n "$WS" ] || { echo "用法: preflight.sh <專案根>" >&2; exit 2; }

PY=$(command -v python3 || command -v python)
if [ -n "$PY" ]; then say "python" "OK ($PY)"; else say "python" "缺：請安裝 Python 3"; MISSING=1; fi

if [ -n "$PY" ] && "$PY" -c "import yaml" 2>/dev/null; then say "PyYAML" "OK"
else say "PyYAML" "缺：${PY:-python} -m pip install pyyaml"; MISSING=1; fi

CFG="$(cd "$(dirname "$0")" && pwd)/../../../scripts/config.py"
if [ -f "$WS/.plugharbor/delivery-flow.yml" ] && [ ! -f "$WS/.plugharbor/lifecycle.yml" ]; then
  say "設定檔" "舊檔：請把 .plugharbor/delivery-flow.yml 改名為 lifecycle.yml（鍵不變），不要重新填寫"; MISSING=1
elif [ -n "$PY" ] && (cd "$WS" && "$PY" "$CFG" get qa.environments 2>/dev/null | grep -qv "^\[\]$"); then say "qa.environments" "OK"
else say "qa.environments" "缺：.plugharbor/lifecycle.yml 要有 qa.environments（格式見 references/config.md）——skill 會問你並代寫"; MISSING=1; fi

if [ -f "$WS/.plugharbor/qa.local.md" ]; then say "qa.local.md" "OK"
else say "qa.local.md" "缺：$WS/.plugharbor/qa.local.md（登入帳密，本機檔、須 gitignore）——skill 會問你並代寫"; MISSING=1; fi

say "MCP（chrome-devtools／票務工具）" "由 skill Step 0 以 ToolSearch 與 ticket-ops 檢查"
exit $MISSING
