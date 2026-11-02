#!/usr/bin/env bash
# install-project.sh 驗證：專案層 plugin 裝進指定專案。HOME 導到暫存目錄、CLI 全換成 stub。
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
fail() { echo "FAIL: $1"; exit 1; }
SCRIPT="$REPO_DIR/setup/install-project.sh"
STUB="$TMP/stub"; TOOLS="$TMP/tools"
bash "$REPO_DIR/setup/tests/lib/stub-cli.sh" "$STUB" "$TOOLS" claude codex agy pi
export STUB_LOG="$TMP/cli.log" STUB_STATE="$TMP/state" STUB_CWD_LOG="$TMP/cwd.log"
mkdir -p "$STUB_STATE" "$TMP/home"
run() { HOME="$TMP/home" PATH="$STUB:$TOOLS:/usr/bin:/bin" bash "$SCRIPT" "$@"; }
ver() { sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$REPO_DIR/plugins/$1/.claude-plugin/plugin.json" | head -1; }
newproj() {  # $1=名稱 → 建 git repo，印出實體路徑
  local d="$TMP/$1"; mkdir -p "$d"; git -C "$d" init -q; (cd "$d" && pwd -P)
}
URL="https://github.com/KerryHuang/plugharbor.git"

# ---------- 1) 預設 local：claude 在專案根裝 --scope local；pi 寫 .pi/settings.json 並加進 exclude；codex／agy 略過 ----------
P="$(newproj "p 一")"; : > "$STUB_LOG"; : > "$STUB_CWD_LOG"
echo '[{"name": "plugharbor", "source": "git"}]' > "$STUB_STATE/claude-mkt"
OUT="$(run "$P" sa-flow kid-ui)" || fail "local 安裝 exit 非 0：$OUT"
grep -qx "claude plugin install sa-flow@plugharbor --scope local @ $P" "$STUB_CWD_LOG" || fail "claude 應在專案根裝 sa-flow --scope local：$(cat "$STUB_CWD_LOG")"
grep -qx "claude plugin install kid-ui@plugharbor --scope local @ $P" "$STUB_CWD_LOG" || fail "claude 應裝 kid-ui"
if grep -q 'marketplace add' "$STUB_LOG"; then fail "user 層已有 marketplace，local 模式不該再 add"; fi
S="$P/.pi/settings.json"
grep -q "$REPO_DIR/plugins/sa-flow" "$S" || fail "pi 應寫入 sa-flow 的絕對路徑：$(cat "$S" 2>/dev/null)"
grep -qx '.pi/settings.json' "$P/.git/info/exclude" || fail ".pi/settings.json 應加進 .git/info/exclude"
echo "$OUT" | grep -q '^SKIP: codex' || fail "codex 應印 SKIP"
echo "$OUT" | grep -q '^SKIP: agy' || fail "agy 應印 SKIP"
if grep -q -E '^(codex|agy) plugin (add|install)' "$STUB_LOG"; then fail "codex／agy 不該安裝專案層 plugin"; fi
# 重跑：pi 不重複、exclude 不重複
run "$P" sa-flow kid-ui >/dev/null || fail "重跑 exit 非 0"
[ "$(grep -c 'plugins/sa-flow' "$S")" = 1 ] || fail "pi packages 重跑重複"
[ "$(grep -cx '.pi/settings.json' "$P/.git/info/exclude")" = 1 ] || fail "exclude 重跑重複"

# ---------- 2) 已裝且版號相同略過、不同 update；其他專案的同名 local 不算 ----------
P2="$(newproj p2)"; : > "$STUB_LOG"
printf '[{"id": "sa-flow@plugharbor", "version": "%s", "scope": "local", "projectPath": "%s"},\n {"id": "kid-ui@plugharbor", "version": "0.0.1", "scope": "local", "projectPath": "%s"},\n {"id": "blog@plugharbor", "version": "%s", "scope": "local", "projectPath": "/other"}]\n' \
  "$(ver sa-flow)" "$P2" "$P2" "$(ver blog)" > "$STUB_STATE/claude-list"
OUT="$(run "$P2" sa-flow kid-ui blog)" || fail "版號比對 exit 非 0：$OUT"
echo "$OUT" | grep -q "UP-TO-DATE: claude sa-flow" || fail "版號相同應 UP-TO-DATE：$OUT"
if grep -q 'claude plugin \(install\|update\) sa-flow' "$STUB_LOG"; then fail "版號相同不該重裝"; fi
grep -qx 'claude plugin update kid-ui@plugharbor --scope local' "$STUB_LOG" || fail "版號不同應 update"
grep -qx 'claude plugin install blog@plugharbor --scope local' "$STUB_LOG" || fail "別的專案裝過不算，應 install"
rm "$STUB_STATE/claude-list"

# ---------- 3) --shared：專案 scope 先 marketplace add 再 install；pi 不寫 ----------
P3="$(newproj p3)"; : > "$STUB_CWD_LOG"
OUT="$(run --shared "$P3" delivery-flow)" || fail "--shared exit 非 0：$OUT"
A="$(grep -n "^claude plugin marketplace add $URL --scope project @ $P3$" "$STUB_CWD_LOG" | cut -d: -f1)"
I="$(grep -n "^claude plugin install delivery-flow@plugharbor --scope project @ $P3$" "$STUB_CWD_LOG" | cut -d: -f1)"
[ -n "$A" ] && [ -n "$I" ] && [ "$A" -lt "$I" ] || fail "--shared 應先 marketplace add --scope project 再 install：$(cat "$STUB_CWD_LOG")"
[ ! -e "$P3/.pi/settings.json" ] || fail "--shared 不該寫 pi 設定"
echo "$OUT" | grep -q '^SKIP: pi' || fail "--shared 應印 SKIP: pi"
# 專案設定已登記 plugharbor 就不重 add
mkdir -p "$P3/.claude"; echo '{"extraKnownMarketplaces": {"plugharbor": {"source": {"source": "git"}}}}' > "$P3/.claude/settings.json"
: > "$STUB_LOG"; run --shared "$P3" delivery-flow >/dev/null || fail "--shared 重跑 exit 非 0"
if grep -q 'marketplace add' "$STUB_LOG"; then fail "專案已登記 plugharbor 不該再 add"; fi

# ---------- 4) user 層名字略過、不存在的名字拒絕、沒給 plugin 拒絕 ----------
OUT="$(run "$P" toolkit sa-flow)" || fail "含 user 層名字 exit 非 0"
echo "$OUT" | grep -q '^SKIP: toolkit 是 user 層' || fail "user 層名字應印 SKIP：$OUT"
if run "$P" no-such >/dev/null 2>&1; then fail "不存在的 plugin 應 exit 非 0"; fi
if run "$P" >/dev/null 2>&1; then fail "沒給 plugin 應 exit 非 0"; fi
if run "$TMP/not-there" sa-flow >/dev/null 2>&1; then fail "專案根不存在應 exit 非 0"; fi

# ---------- 5) .pi/settings.json 已進版控：local 模式不寫 pi、印 WARN ----------
P5="$(newproj p5)"; mkdir -p "$P5/.pi"; echo '{"packages": []}' > "$P5/.pi/settings.json"
git -C "$P5" add .pi/settings.json
OUT="$(run "$P5" sa-flow)" || fail "追蹤檔情境 exit 非 0"
echo "$OUT" | grep -q '^WARN: pi' || fail "pi 設定已進版控應印 WARN：$OUT"
if grep -q 'plugins/sa-flow' "$P5/.pi/settings.json"; then fail "已進版控的 pi 設定不該寫入個人路徑"; fi

# ---------- 6) --check 只報不改 ----------
P6="$(newproj p6)"; : > "$STUB_LOG"
OUT="$(run --check "$P6" sa-flow)" || fail "--check exit 非 0"
echo "$OUT" | grep -q 'MISSING: claude sa-flow' || fail "--check 應報 MISSING：$OUT"
if grep -q 'claude plugin install' "$STUB_LOG"; then fail "--check 不該安裝"; fi
[ ! -e "$P6/.pi/settings.json" ] || fail "--check 不該寫 pi 設定"

echo "PASS: install-project.sh（6 組）"
