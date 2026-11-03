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
OUT="$(run "$P" sa-flow ui-ux)" || fail "local 安裝 exit 非 0：$OUT"
grep -qx "claude plugin install sa-flow@plugharbor --scope local @ $P" "$STUB_CWD_LOG" || fail "claude 應在專案根裝 sa-flow --scope local：$(cat "$STUB_CWD_LOG")"
grep -qx "claude plugin install ui-ux@plugharbor --scope local @ $P" "$STUB_CWD_LOG" || fail "claude 應裝 ui-ux"
if grep -q 'marketplace add' "$STUB_LOG"; then fail "user 層已有 marketplace，local 模式不該再 add"; fi
S="$P/.pi/settings.json"
grep -q "$REPO_DIR/plugins/sa-flow" "$S" || fail "pi 應寫入 sa-flow 的絕對路徑：$(cat "$S" 2>/dev/null)"
grep -qx '.pi/settings.json' "$P/.git/info/exclude" || fail ".pi/settings.json 應加進 .git/info/exclude"
[ -L "$P/.agents/skills/explore" ] || fail "codex／agy 應建 .agents/skills/explore 的 link：$OUT"
[ -L "$P/.agents/skills/designing-ui" ] || fail "codex／agy 應建 ui-ux 的 skill link"
if grep -q -E '^(codex|agy) plugin (add|install)' "$STUB_LOG"; then fail "codex／agy 不該用 plugin 指令安裝專案層 plugin"; fi
# 重跑：pi 不重複、exclude 不重複
run "$P" sa-flow ui-ux >/dev/null || fail "重跑 exit 非 0"
[ "$(grep -c 'plugins/sa-flow' "$S")" = 1 ] || fail "pi packages 重跑重複"
[ "$(grep -cx '.pi/settings.json' "$P/.git/info/exclude")" = 1 ] || fail "exclude 重跑重複"

# ---------- 2) 已裝且版號相同略過、不同 update；其他專案的同名 local 不算 ----------
P2="$(newproj p2)"; : > "$STUB_LOG"
printf '[{"id": "sa-flow@plugharbor", "version": "%s", "scope": "local", "projectPath": "%s"},\n {"id": "ui-ux@plugharbor", "version": "0.0.1", "scope": "local", "projectPath": "%s"},\n {"id": "blog@plugharbor", "version": "%s", "scope": "local", "projectPath": "/other"}]\n' \
  "$(ver sa-flow)" "$P2" "$P2" "$(ver blog)" > "$STUB_STATE/claude-list"
OUT="$(run "$P2" sa-flow ui-ux blog)" || fail "版號比對 exit 非 0：$OUT"
echo "$OUT" | grep -q "UP-TO-DATE: claude sa-flow" || fail "版號相同應 UP-TO-DATE：$OUT"
if grep -q 'claude plugin \(install\|update\) sa-flow' "$STUB_LOG"; then fail "版號相同不該重裝"; fi
grep -qx 'claude plugin update ui-ux@plugharbor --scope local' "$STUB_LOG" || fail "版號不同應 update"
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

# ---------- 7) Git Bash（有 cygpath）：交給 Windows 原生 python 的路徑要先轉成 C:/ 形式 ----------
cat > "$STUB/cygpath" <<'SH'
#!/usr/bin/env bash
[ "$1" = "-m" ] && shift
echo "cygpath -m $1" >> "$STUB_LOG"
printf '%s\n' "$1"
SH
chmod +x "$STUB/cygpath"
P7="$(newproj p7)"; : > "$STUB_LOG"
run "$P7" sa-flow >/dev/null || fail "有 cygpath 的 install-project exit 非 0"
grep -qx "cygpath -m $P7/.pi/settings.json" "$STUB_LOG" || fail "pi 設定檔路徑應先經 cygpath -m 轉換：$(grep cygpath "$STUB_LOG")"
grep -qx "cygpath -m $REPO_DIR/plugins/sa-flow" "$STUB_LOG" || fail "pi package 路徑應先經 cygpath -m 轉換"
rm "$STUB/cygpath"

# ---------- 8) 改名對照：本專案裝著舊名 → 先卸舊名再裝新名；命令列給舊名自動換新名；pi 舊路徑換新 ----------
P8="$(newproj p8)"; : > "$STUB_LOG"; : > "$STUB_CWD_LOG"
printf '[{"id": "old-kid@plugharbor", "version": "0.1.0", "scope": "local", "projectPath": "%s"},\n {"id": "old-kid@plugharbor", "version": "0.1.0", "scope": "local", "projectPath": "/other"}]\n' "$P8" > "$STUB_STATE/claude-list"
mkdir -p "$P8/.pi"
printf '{"packages": ["npm:keep-me", "%s"]}\n' "$REPO_DIR/plugins/old-kid" > "$P8/.pi/settings.json"
OUT="$(PLUGHARBOR_RENAMES="old-kid:ui-ux" run --check "$P8" ui-ux)" || fail "改名 --check exit 非 0：$OUT"
echo "$OUT" | grep -q '^RENAME: claude old-kid → ui-ux' || fail "--check 應報 RENAME: claude：$OUT"
echo "$OUT" | grep -q '^RENAME: pi old-kid → ui-ux' || fail "--check 應報 RENAME: pi：$OUT"
if grep -q 'uninstall' "$STUB_LOG"; then fail "--check 不該卸載"; fi
OUT="$(PLUGHARBOR_RENAMES="old-kid:ui-ux" run "$P8" ui-ux)" || fail "改名實跑 exit 非 0：$OUT"
U="$(grep -n "^claude plugin uninstall old-kid@plugharbor --scope local @ $P8$" "$STUB_CWD_LOG" | cut -d: -f1)"
I="$(grep -n "^claude plugin install ui-ux@plugharbor --scope local @ $P8$" "$STUB_CWD_LOG" | cut -d: -f1)"
[ -n "$U" ] && [ -n "$I" ] && [ "$U" -lt "$I" ] || fail "應先在專案根卸 old-kid 再裝 ui-ux：$(cat "$STUB_CWD_LOG")"
[ "$(grep -c 'uninstall old-kid' "$STUB_LOG")" = 1 ] || fail "別的專案的 old-kid 不該卸"
S="$P8/.pi/settings.json"
if grep -q 'plugins/old-kid' "$S"; then fail "pi 舊路徑應移除：$(cat "$S")"; fi
grep -q "$REPO_DIR/plugins/ui-ux" "$S" && grep -q 'npm:keep-me' "$S" || fail "pi 應加新路徑、保留其他：$(cat "$S")"
OUT="$(PLUGHARBOR_RENAMES="old-kid:ui-ux" run --check "$P8" old-kid)" || fail "命令列給舊名 exit 非 0：$OUT"
echo "$OUT" | grep -q '^RENAME: old-kid → ui-ux（改用新名）' || fail "命令列舊名應自動換新名：$OUT"
rm "$STUB_STATE/claude-list"

# ---------- 9) Codex／agy：.agents/skills/<skill> → ../plugharbor/<plugin>/skills/<skill>，plugin 根是 realpath 往上兩層 ----------
realp() { python3 -c 'import os,sys;print(os.path.realpath(sys.argv[1]))' "$1"; }
P9="$(newproj "p 九")"
OUT="$(run "$P9" sa-flow)" || fail "symlink 安裝 exit 非 0：$OUT"
L="$P9/.agents/skills/explore"
[ -L "$L" ] || fail "(a) 應建 link：$OUT"
[ "$(readlink "$L")" = "../plugharbor/sa-flow/skills/explore" ] || fail "(a) skill link 應為相對路徑：$(readlink "$L")"
[ "$(realp "$L")" = "$(realp "$REPO_DIR/plugins/sa-flow/skills/explore")" ] || fail "(a) realpath 應落在 plugharbor clone：$(realp "$L")"
EX="$P9/.git/info/exclude"
grep -qx '.agents/plugharbor/' "$EX" || fail "(a) exclude 應含 .agents/plugharbor/"
grep -qx '.agents/skills/explore' "$EX" || fail "(a) exclude 應含每個 skill link"
if grep -qx '.agents/skills/' "$EX"; then fail "(a) 不該排除整個 .agents/skills/"; fi
echo "$OUT" | grep -q '^OK:   codex/agy link explore' || fail "(a) 應印 OK link：$OUT"
# (b) 重跑：UP-TO-DATE、exclude 不重複
OUT="$(run "$P9" sa-flow)" || fail "(b) 重跑 exit 非 0"
echo "$OUT" | grep -q '^UP-TO-DATE: link explore' || fail "(b) 重跑應 UP-TO-DATE：$OUT"
[ "$(grep -cx '.agents/plugharbor/' "$EX")" = 1 ] || fail "(b) exclude 重複"
[ "$(grep -cx '.agents/skills/explore' "$EX")" = 1 ] || fail "(b) skill exclude 重複"
# (c) 使用者自己的同名實體目錄：SKIP、內容不動
P9c="$(newproj p9c)"; mkdir -p "$P9c/.agents/skills/write-doc"; echo mine > "$P9c/.agents/skills/write-doc/SKILL.md"
OUT="$(run "$P9c" sa-flow)" || fail "(c) exit 非 0"
echo "$OUT" | grep -q "^SKIP: .*write-doc 已存在且不是 plugharbor 的 link" || fail "(c) 應 SKIP 使用者目錄：$OUT"
[ "$(cat "$P9c/.agents/skills/write-doc/SKILL.md")" = mine ] && [ ! -L "$P9c/.agents/skills/write-doc" ] || fail "(c) 使用者目錄被動到"
# (d) 失效的 plugharbor link：--check 報 BROKEN，實跑移除；別人的失效 link 不動
ln -s "$REPO_DIR/plugins/no-such/skills/x" "$P9/.agents/skills/x"
ln -s "/nowhere/else" "$P9/.agents/skills/theirs"
OUT="$(run --check "$P9" sa-flow)" || fail "(d) --check exit 非 0"
echo "$OUT" | grep -q '^BROKEN: .*\.agents/skills/x' || fail "(d) --check 應報 BROKEN：$OUT"
[ -L "$P9/.agents/skills/x" ] || fail "(d) --check 不該移除"
OUT="$(run "$P9" sa-flow)" || fail "(d) 實跑 exit 非 0"
[ ! -L "$P9/.agents/skills/x" ] || fail "(d) 失效 link 應移除：$OUT"
[ -L "$P9/.agents/skills/theirs" ] || fail "(d) 不是 plugharbor 的 link 不該動"
# (e) --shared：不建 link
P9e="$(newproj p9e)"
OUT="$(run --shared "$P9e" sa-flow)" || fail "(e) exit 非 0"
echo "$OUT" | grep -q '^SKIP: codex/agy 不支援 --shared' || fail "(e) 應印 SKIP：$OUT"
[ ! -e "$P9e/.agents" ] || fail "(e) --shared 不該建 .agents"
# (f) 建不了 symlink（Windows 無開發人員模式）：複製 skill，同目錄 .plugharbor-root 記 plugin 根
P9f="$(newproj p9f)"
OUT="$(PLUGHARBOR_LINK_MODE=copy run "$P9f" sa-flow)" || fail "(f) exit 非 0：$OUT"
echo "$OUT" | grep -q '^WARN: 無法建 symlink，改用複製' || fail "(f) 應 WARN：$OUT"
D="$P9f/.agents/skills/explore"
[ -d "$D" ] && [ ! -L "$D" ] && [ -f "$D/SKILL.md" ] || fail "(f) 應複製 skill 目錄"
[ "$(cat "$D/.plugharbor-root")" = "$REPO_DIR/plugins/sa-flow" ] || fail "(f) .plugharbor-root 應記 plugin 根：$(cat "$D/.plugharbor-root" 2>/dev/null)"
OUT="$(PLUGHARBOR_LINK_MODE=copy run --check "$P9f" sa-flow)" || fail "(f) --check exit 非 0"
echo "$OUT" | grep -q '^UP-TO-DATE: link explore' || fail "(f) 內容相同應 UP-TO-DATE：$OUT"
echo changed >> "$D/SKILL.md"
OUT="$(PLUGHARBOR_LINK_MODE=copy run --check "$P9f" sa-flow)" || fail "(f) --check exit 非 0"
echo "$OUT" | grep -q '^DIFF: .*explore' || fail "(f) 內容不同應報 DIFF：$OUT"
PLUGHARBOR_LINK_MODE=copy run "$P9f" sa-flow >/dev/null || fail "(f) 重跑 exit 非 0"
cmp -s "$D/SKILL.md" "$REPO_DIR/plugins/sa-flow/skills/explore/SKILL.md" || fail "(f) 重跑應更新複本"
# (g) 複製模式：clone 搬家後 .plugharbor-root 過期 → --check 報 DIFF、實跑修正；root 指的 plugin 不存在 → BROKEN、實跑移除
echo "/old/clone/plugins/sa-flow" > "$D/.plugharbor-root"
OUT="$(PLUGHARBOR_LINK_MODE=copy run --check "$P9f" sa-flow)" || fail "(g) --check exit 非 0"
echo "$OUT" | grep -q '^DIFF: .*explore' || fail "(g) marker 過期應報 DIFF：$OUT"
PLUGHARBOR_LINK_MODE=copy run "$P9f" sa-flow >/dev/null || fail "(g) 實跑 exit 非 0"
[ "$(cat "$D/.plugharbor-root")" = "$REPO_DIR/plugins/sa-flow" ] || fail "(g) 實跑應修正 marker：$(cat "$D/.plugharbor-root")"
mkdir -p "$P9f/.agents/skills/gone"; echo x > "$P9f/.agents/skills/gone/SKILL.md"; echo "$REPO_DIR/plugins/no-such" > "$P9f/.agents/skills/gone/.plugharbor-root"
OUT="$(PLUGHARBOR_LINK_MODE=copy run --check "$P9f" sa-flow)" || fail "(g) --check exit 非 0"
echo "$OUT" | grep -q '^BROKEN: .*\.agents/skills/gone' || fail "(g) 失效複本應報 BROKEN：$OUT"
PLUGHARBOR_LINK_MODE=copy run "$P9f" sa-flow >/dev/null || fail "(g) 實跑 exit 非 0"
[ ! -e "$P9f/.agents/skills/gone" ] || fail "(g) 失效複本應移除"

# ---------- 10) 正式改名對照：每條新名都存在、舊名都已移除；命令列給舊名自動換新名 ----------
PAIRS="$(bash -c '. "$1/setup/lib.sh"; ph_rename_pairs' _ "$REPO_DIR")"
[ -n "$PAIRS" ] || fail "正式改名對照不該是空的"
while read -r o n; do
  [ -f "$REPO_DIR/plugins/$n/.claude-plugin/plugin.json" ] || fail "改名對照的新名不存在：$n"
  [ ! -e "$REPO_DIR/plugins/$o" ] || fail "改名對照的舊名還在：$o"
done <<< "$PAIRS"
P10="$(newproj p10)"
OUT="$(run --check "$P10" database-sqlserver desktop-avalonia)" || fail "正式對照 --check exit 非 0：$OUT"
echo "$OUT" | grep -q '^RENAME: database-sqlserver → database（改用新名）' || fail "應換成 database：$OUT"
echo "$OUT" | grep -q '^MISSING: claude desktop' || fail "應以新名 desktop 比對：$OUT"

echo "PASS: install-project.sh（10 組）"
