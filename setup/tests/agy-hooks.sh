#!/usr/bin/env bash
# setup/lib/agy_hooks.py：check 報 DIFF、apply 改成絕對路徑、再跑不動（冪等）、非相對指令不碰
set -euo pipefail
root="$(cd "$(dirname "$0")/../.." && pwd)"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/plugins/toolkit" "$tmp/plugins/research"
cat > "$tmp/plugins/toolkit/hooks.json" <<'EOF'
{"toolkit":{"PreToolUse":[{"matcher":".*","hooks":[
  {"type":"command","command":"sh \"./hooks/run-py.sh\" guard.py","timeout":5},
  {"type":"command","command":"bash \"./hooks/notification.sh\"","timeout":5},
  {"type":"command","command":"node \"C:/x/notify.mjs\"","timeout":5}]}]}}
EOF
py="$(command -v python3 || command -v python)"
run() { PYTHONUTF8=1 "$py" "$root/setup/lib/agy_hooks.py" "$tmp/plugins" "C:/Git/usr/bin" "$1" toolkit research missing; }

out="$(run check)"
echo "$out" | grep -q '^DIFF: agy hooks toolkit（2 條' || { echo "FAIL check：$out"; exit 1; }
grep -q 'sh \\"./hooks/run-py.sh' "$tmp/plugins/toolkit/hooks.json" || { echo "FAIL check 不該改檔"; exit 1; }

out="$(run apply)"
echo "$out" | grep -q '^OK:   agy hooks toolkit（改寫 2 條' || { echo "FAIL apply：$out"; exit 1; }
f="$tmp/plugins/toolkit/hooks.json"
grep -q '"\\"C:/Git/usr/bin/sh.exe\\" \\"[^"]*/plugins/toolkit/hooks/run-py.sh\\" guard.py"' "$f" || { echo "FAIL sh 未改寫：$(cat "$f")"; exit 1; }
grep -q 'C:/Git/usr/bin/bash.exe' "$f" || { echo "FAIL bash 未改寫"; exit 1; }
grep -q '"node \\"C:/x/notify.mjs\\""' "$f" || { echo "FAIL 非相對指令被動到"; exit 1; }

out="$(run apply)"
[ -z "$out" ] || { echo "FAIL 第二次 apply 應無輸出：$out"; exit 1; }
[ -z "$(run check)" ] || { echo "FAIL apply 後 check 應一致"; exit 1; }
echo "OK agy-hooks"
