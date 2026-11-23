#!/bin/sh
# 重測試排隊：同一台機器一次只跑一支，其餘等前一支結束。
# 用法：sh test-lock.sh <測試指令…>；結束碼是測試指令的結束碼。
# 鎖是檔案，用 noclobber（open O_EXCL）建立，內容是持有者 pid；持有者已不在就視為殘留鎖、接手。
# 不用 mkdir：CI runner 上的 mkdir 指令不保證互斥（issue #67），兩支同時 mkdir 同一路徑可能都回傳成功。
set -u
[ $# -gt 0 ] || { echo "用法：test-lock.sh <測試指令…>" >&2; exit 2; }
LOCK="${UNATTENDED_TEST_LOCK:-${TMPDIR:-/tmp}/unattended-test.pid}"
WAIT="${UNATTENDED_TEST_LOCK_POLL:-5}"
said=0
until (set -C; echo $$ > "$LOCK") 2>/dev/null; do
  pid="$(cat "$LOCK" 2>/dev/null || true)"
  if [ -n "$pid" ] && ! kill -0 "$pid" 2>/dev/null; then rm -f "$LOCK"; continue; fi
  [ "$said" -eq 1 ] || { echo "[test-lock] 等前一支重測試結束（pid ${pid:-?}）" >&2; said=1; }
  sleep "$WAIT"
done
trap 'rm -f "$LOCK"' EXIT INT TERM
"$@"
