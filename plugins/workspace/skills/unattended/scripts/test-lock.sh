#!/bin/sh
# 重測試排隊：同一台機器一次只跑一支，其餘等前一支結束。
# 用法：sh test-lock.sh <測試指令…>；結束碼是測試指令的結束碼。
# 鎖是目錄（mkdir 不可分割、各平台都有）；持有者的 pid 寫在裡面，持有者已不在就視為殘留鎖、接手。
set -u
[ $# -gt 0 ] || { echo "用法：test-lock.sh <測試指令…>" >&2; exit 2; }
LOCK="${UNATTENDED_TEST_LOCK:-${TMPDIR:-/tmp}/unattended-test.lock}"
WAIT="${UNATTENDED_TEST_LOCK_POLL:-5}"
said=0
until mkdir "$LOCK" 2>/dev/null; do
  pid="$(cat "$LOCK/pid" 2>/dev/null || true)"
  if [ -n "$pid" ] && ! kill -0 "$pid" 2>/dev/null; then echo "[DEBUG67] stale takeover me=$$ pid=$pid" >&2; ps -o pid,ppid,stat,args >&2; rm -rf "$LOCK"; continue; fi
  [ "$said" -eq 1 ] || { echo "[test-lock] 等前一支重測試結束（pid ${pid:-?}）" >&2; said=1; }
  sleep "$WAIT"
done
echo $$ > "$LOCK/pid"
trap 'rm -rf "$LOCK"' EXIT INT TERM
"$@"
