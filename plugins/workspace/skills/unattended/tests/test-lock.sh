#!/usr/bin/env bash
# test-lock.sh 行為測試：兩支同時跑不重疊、殘留鎖會被接手、結束碼照傳
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SCRIPT="$HERE/../scripts/test-lock.sh"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
export UNATTENDED_TEST_LOCK="$TMP/lock" UNATTENDED_TEST_LOCK_POLL=0.1
fail=0
check() { if [ "$2" -eq 0 ]; then echo "PASS $1"; else echo "FAIL $1"; fail=1; fi; }

job() { sh "$SCRIPT" sh -c "echo start-$1 >> '$TMP/log'; sleep 0.5; echo end-$1 >> '$TMP/log'"; }
job a & job b & wait
# 不重疊：每個 start 後面緊接自己的 end
echo "[DEBUG67] log:" >&2; cat "$TMP/log" >&2
check "兩支不重疊" "$(awk 'NR%2==1{s=substr($0,7)} NR%2==0{if(substr($0,5)!=s)exit 1}' "$TMP/log"; echo $?)"
check "結束後鎖已釋放" "$([ ! -e "$TMP/lock" ]; echo $?)"

mkdir "$TMP/lock"; echo 999999 > "$TMP/lock/pid"
sh "$SCRIPT" true; check "殘留鎖被接手" "$?"

set +e; sh "$SCRIPT" sh -c 'exit 7'; rc=$?; set -e
check "結束碼照傳" "$([ "$rc" -eq 7 ]; echo $?)"
exit $fail
