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
# stub 裡有 agy：不帶 PLUGHARBOR_LINK_MODE 會因偵測到 agy 改走複製，既有斷言預設釘 symlink（第 9 節 (h) 另測偵測）
run() { HOME="$TMP/home" PATH="$STUB:$TOOLS:/usr/bin:/bin" PLUGHARBOR_LINK_MODE="${PLUGHARBOR_LINK_MODE:-symlink}" bash "$SCRIPT" "$@"; }
ver() { sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$REPO_DIR/plugins/$1/.claude-plugin/plugin.json" | head -1; }
newproj() {  # $1=名稱 → 建 git repo，印出實體路徑
  local d="$TMP/$1"; mkdir -p "$d"; git -C "$d" init -q; (cd "$d" && pwd -P)
}
URL="https://github.com/KerryHuang/plugharbor.git"
# Git Bash 上腳本寫給原生程式（pi、.plugharbor-root）的是 C:/ 形式，斷言要用同一形式比
native() { if command -v cygpath >/dev/null 2>&1; then cygpath -m "$1"; else printf '%s\n' "$1"; fi; }
# 這台能不能建 symlink（Windows 沒開開發人員模式就不能）：不能時 install-project 走複製退路
CAN_LINK=0; mkdir -p "$TMP/lt"; MSYS=winsymlinks:nativestrict ln -s "$TMP/lt" "$TMP/lt-link" 2>/dev/null && [ -L "$TMP/lt-link" ] && CAN_LINK=1
linked() {  # $1=.agents/skills/<skill>：能建 symlink 就要是 link，不能就要是帶 marker 的複本
  if [ "$CAN_LINK" -eq 1 ]; then [ -L "$1" ]; else [ -d "$1" ] && [ -f "$1/.plugharbor-root" ]; fi
}

# ---------- 1) 預設 local：claude 在專案根裝 --scope local；pi 寫 .pi/settings.json 並加進 exclude；codex／agy 略過 ----------
P="$(newproj "p 一")"; : > "$STUB_LOG"; : > "$STUB_CWD_LOG"
echo '[{"name": "plugharbor", "source": "git"}]' > "$STUB_STATE/claude-mkt"
OUT="$(run "$P" lifecycle ui-ux)" || fail "local 安裝 exit 非 0：$OUT"
grep -qx "claude plugin install lifecycle@plugharbor --scope local @ $P" "$STUB_CWD_LOG" || fail "claude 應在專案根裝 lifecycle --scope local：$(cat "$STUB_CWD_LOG")"
grep -qx "claude plugin install ui-ux@plugharbor --scope local @ $P" "$STUB_CWD_LOG" || fail "claude 應裝 ui-ux"
if grep -q 'marketplace add' "$STUB_LOG"; then fail "user 層已有 marketplace，local 模式不該再 add"; fi
S="$P/.pi/settings.json"
grep -q "$(native "$REPO_DIR/plugins/lifecycle")" "$S" || fail "pi 應寫入 lifecycle 的絕對路徑：$(cat "$S" 2>/dev/null)"
grep -qx '.pi/settings.json' "$P/.git/info/exclude" || fail ".pi/settings.json 應加進 .git/info/exclude"
linked "$P/.agents/skills/release" || fail "codex／agy 應建 .agents/skills/release 的 link：$OUT"
linked "$P/.agents/skills/designing-ui" || fail "codex／agy 應建 ui-ux 的 skill link"
if grep -q -E '^(codex|agy) plugin (add|install)' "$STUB_LOG"; then fail "codex／agy 不該用 plugin 指令安裝專案層 plugin"; fi
# 重跑：pi 不重複、exclude 不重複
run "$P" lifecycle ui-ux >/dev/null || fail "重跑 exit 非 0"
[ "$(grep -c 'plugins/lifecycle' "$S")" = 1 ] || fail "pi packages 重跑重複"
[ "$(grep -cx '.pi/settings.json' "$P/.git/info/exclude")" = 1 ] || fail "exclude 重跑重複"

# ---------- 2) 已裝且版號相同略過、不同 update；其他專案的同名 local 不算 ----------
P2="$(newproj p2)"; : > "$STUB_LOG"
printf '[{"id": "lifecycle@plugharbor", "version": "%s", "scope": "local", "projectPath": "%s"},\n {"id": "ui-ux@plugharbor", "version": "0.0.1", "scope": "local", "projectPath": "%s"},\n {"id": "blog@plugharbor", "version": "%s", "scope": "local", "projectPath": "/other"}]\n' \
  "$(ver lifecycle)" "$(native "$P2")" "$(native "$P2")" "$(ver blog)" > "$STUB_STATE/claude-list"
OUT="$(run "$P2" lifecycle ui-ux blog)" || fail "版號比對 exit 非 0：$OUT"
echo "$OUT" | grep -q "UP-TO-DATE: claude lifecycle" || fail "版號相同應 UP-TO-DATE：$OUT"
if grep -q 'claude plugin \(install\|update\) lifecycle' "$STUB_LOG"; then fail "版號相同不該重裝"; fi
grep -qx 'claude plugin update ui-ux@plugharbor --scope local' "$STUB_LOG" || fail "版號不同應 update"
grep -qx 'claude plugin install blog@plugharbor --scope local' "$STUB_LOG" || fail "別的專案裝過不算，應 install"
rm "$STUB_STATE/claude-list"

# ---------- 3) --shared：專案 scope 先 marketplace add 再 install；pi 不寫 ----------
P3="$(newproj p3)"; : > "$STUB_CWD_LOG"
OUT="$(run --shared "$P3" lifecycle)" || fail "--shared exit 非 0：$OUT"
A="$(grep -n "^claude plugin marketplace add $URL --scope project @ $P3$" "$STUB_CWD_LOG" | cut -d: -f1)"
I="$(grep -n "^claude plugin install lifecycle@plugharbor --scope project @ $P3$" "$STUB_CWD_LOG" | cut -d: -f1)"
[ -n "$A" ] && [ -n "$I" ] && [ "$A" -lt "$I" ] || fail "--shared 應先 marketplace add --scope project 再 install：$(cat "$STUB_CWD_LOG")"
[ ! -e "$P3/.pi/settings.json" ] || fail "--shared 不該寫 pi 設定"
echo "$OUT" | grep -q '^SKIP: pi' || fail "--shared 應印 SKIP: pi"
# 專案設定已登記 plugharbor 就不重 add
mkdir -p "$P3/.claude"; echo '{"extraKnownMarketplaces": {"plugharbor": {"source": {"source": "git"}}}}' > "$P3/.claude/settings.json"
: > "$STUB_LOG"; run --shared "$P3" lifecycle >/dev/null || fail "--shared 重跑 exit 非 0"
if grep -q 'marketplace add' "$STUB_LOG"; then fail "專案已登記 plugharbor 不該再 add"; fi

# ---------- 4) user 層名字略過、不存在的名字拒絕、沒給 plugin 拒絕 ----------
OUT="$(run "$P" toolkit lifecycle)" || fail "含 user 層名字 exit 非 0"
echo "$OUT" | grep -q '^SKIP: toolkit 是 user 層' || fail "user 層名字應印 SKIP：$OUT"
if run "$P" no-such >/dev/null 2>&1; then fail "不存在的 plugin 應 exit 非 0"; fi
if run "$P" >/dev/null 2>&1; then fail "沒給 plugin 應 exit 非 0"; fi
if run "$TMP/not-there" lifecycle >/dev/null 2>&1; then fail "專案根不存在應 exit 非 0"; fi

# ---------- 5) .pi/settings.json 已進版控：local 模式不寫 pi、印 WARN ----------
P5="$(newproj p5)"; mkdir -p "$P5/.pi"; echo '{"packages": []}' > "$P5/.pi/settings.json"
git -C "$P5" add .pi/settings.json
OUT="$(run "$P5" lifecycle)" || fail "追蹤檔情境 exit 非 0"
echo "$OUT" | grep -q '^WARN: pi' || fail "pi 設定已進版控應印 WARN：$OUT"
if grep -q 'plugins/lifecycle' "$P5/.pi/settings.json"; then fail "已進版控的 pi 設定不該寫入個人路徑"; fi

# ---------- 6) --check 只報不改 ----------
P6="$(newproj p6)"; : > "$STUB_LOG"
rc=0; OUT="$(run --check "$P6" lifecycle)" || rc=$?
[ "$rc" -eq 3 ] || fail "--check 有差異應 exit 3，實際 ${rc}：$OUT"
echo "$OUT" | grep -q 'MISSING: claude lifecycle' || fail "--check 應報 MISSING：$OUT"
if grep -q 'claude plugin install' "$STUB_LOG"; then fail "--check 不該安裝"; fi
[ ! -e "$P6/.pi/settings.json" ] || fail "--check 不該寫 pi 設定"

# ---------- 7) Git Bash（有 cygpath）：交給 Windows 原生 python 的路徑要先轉成 C:/ 形式 ----------
export REAL_CYGPATH="$(command -v cygpath 2>/dev/null || true)"
cat > "$STUB/cygpath" <<'SH'
#!/usr/bin/env bash
[ "$1" = "-m" ] && shift
echo "cygpath -m $1" >> "$STUB_LOG"
# 真的 Git Bash 上轉呼叫原本的 cygpath：原樣回傳 /c/... 會讓 Windows 原生 python 比對不到路徑
if [ -n "${REAL_CYGPATH:-}" ]; then exec "$REAL_CYGPATH" -m "$1"; fi
printf '%s\n' "$1"
SH
chmod +x "$STUB/cygpath"
P7="$(newproj p7)"; : > "$STUB_LOG"
run "$P7" lifecycle >/dev/null || fail "有 cygpath 的 install-project exit 非 0"
grep -qx "cygpath -m $P7/.pi/settings.json" "$STUB_LOG" || fail "pi 設定檔路徑應先經 cygpath -m 轉換：$(grep cygpath "$STUB_LOG")"
grep -qx "cygpath -m $REPO_DIR/plugins/lifecycle" "$STUB_LOG" || fail "pi package 路徑應先經 cygpath -m 轉換"
rm "$STUB/cygpath"

# ---------- 8) 改名對照：本專案裝著舊名 → 先卸舊名再裝新名；命令列給舊名自動換新名；pi 舊路徑換新 ----------
P8="$(newproj p8)"; : > "$STUB_LOG"; : > "$STUB_CWD_LOG"
printf '[{"id": "old-kid@plugharbor", "version": "0.1.0", "scope": "local", "projectPath": "%s"},\n {"id": "old-kid@plugharbor", "version": "0.1.0", "scope": "local", "projectPath": "/other"}]\n' "$(native "$P8")" > "$STUB_STATE/claude-list"
mkdir -p "$P8/.pi"
printf '{"packages": ["npm:keep-me", "%s"]}\n' "$(native "$REPO_DIR/plugins/old-kid")" > "$P8/.pi/settings.json"
OUT="$(PLUGHARBOR_RENAMES="old-kid:ui-ux" run --check "$P8" ui-ux)" || [ $? -eq 3 ] || fail "改名 --check exit 不是 0／3：$OUT"
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
grep -q "$(native "$REPO_DIR/plugins/ui-ux")" "$S" && grep -q 'npm:keep-me' "$S" || fail "pi 應加新路徑、保留其他：$(cat "$S")"
OUT="$(PLUGHARBOR_RENAMES="old-kid:ui-ux" run --check "$P8" old-kid)" || [ $? -eq 3 ] || fail "命令列給舊名 exit 不是 0／3：$OUT"
echo "$OUT" | grep -q '^RENAME: old-kid → ui-ux（改用新名）' || fail "命令列舊名應自動換新名：$OUT"
rm "$STUB_STATE/claude-list"

# ---------- 9) Codex／agy：.agents/skills/<skill> → ../plugharbor/<plugin>/skills/<skill>，plugin 根是 realpath 往上兩層 ----------
realp() { python3 -c 'import os,sys;print(os.path.realpath(sys.argv[1]))' "$1"; }
if [ "$CAN_LINK" -eq 1 ]; then
P9="$(newproj "p 九")"
OUT="$(run "$P9" lifecycle)" || fail "symlink 安裝 exit 非 0：$OUT"
L="$P9/.agents/skills/release"
[ -L "$L" ] || fail "(a) 應建 link：$OUT"
[ "$(readlink "$L")" = "../plugharbor/lifecycle/skills/release" ] || fail "(a) skill link 應為相對路徑：$(readlink "$L")"
[ "$(realp "$L")" = "$(realp "$REPO_DIR/plugins/lifecycle/skills/release")" ] || fail "(a) realpath 應落在 plugharbor clone：$(realp "$L")"
EX="$P9/.git/info/exclude"
grep -qx '.agents/plugharbor/' "$EX" || fail "(a) exclude 應含 .agents/plugharbor/"
grep -qx '.agents/skills/release' "$EX" || fail "(a) exclude 應含每個 skill link"
if grep -qx '.agents/skills/' "$EX"; then fail "(a) 不該排除整個 .agents/skills/"; fi
echo "$OUT" | grep -q '^OK:   codex/agy link release' || fail "(a) 應印 OK link：$OUT"
# (b) 重跑：UP-TO-DATE、exclude 不重複
OUT="$(run "$P9" lifecycle)" || fail "(b) 重跑 exit 非 0"
echo "$OUT" | grep -q '^UP-TO-DATE: link release' || fail "(b) 重跑應 UP-TO-DATE：$OUT"
[ "$(grep -cx '.agents/plugharbor/' "$EX")" = 1 ] || fail "(b) exclude 重複"
[ "$(grep -cx '.agents/skills/release' "$EX")" = 1 ] || fail "(b) skill exclude 重複"
fi
# (c) 使用者自己的同名實體目錄：SKIP、內容不動
P9c="$(newproj p9c)"; mkdir -p "$P9c/.agents/skills/qa-verify"; echo mine > "$P9c/.agents/skills/qa-verify/SKILL.md"
OUT="$(run "$P9c" lifecycle)" || fail "(c) exit 非 0"
echo "$OUT" | grep -q "^SKIP: .*qa-verify 已存在且不是 plugharbor 的 link" || fail "(c) 應 SKIP 使用者目錄：$OUT"
[ "$(cat "$P9c/.agents/skills/qa-verify/SKILL.md")" = mine ] && [ ! -L "$P9c/.agents/skills/qa-verify" ] || fail "(c) 使用者目錄被動到"
# (d) 失效的 plugharbor link：--check 報 BROKEN，實跑移除；別人的失效 link 不動
if [ "$CAN_LINK" -eq 1 ]; then
ln -s "$REPO_DIR/plugins/no-such/skills/x" "$P9/.agents/skills/x"
ln -s "/nowhere/else" "$P9/.agents/skills/theirs"
OUT="$(run --check "$P9" lifecycle)" || [ $? -eq 3 ] || fail "(d) --check exit 不是 0／3"
echo "$OUT" | grep -q '^BROKEN: .*\.agents/skills/x' || fail "(d) --check 應報 BROKEN：$OUT"
[ -L "$P9/.agents/skills/x" ] || fail "(d) --check 不該移除"
OUT="$(run "$P9" lifecycle)" || fail "(d) 實跑 exit 非 0"
[ ! -L "$P9/.agents/skills/x" ] || fail "(d) 失效 link 應移除：$OUT"
[ -L "$P9/.agents/skills/theirs" ] || fail "(d) 不是 plugharbor 的 link 不該動"
else
echo "SKIP: 這台不能建 symlink，略過 9(a)(b)(d)"
fi
# (e) --shared：不建 link
P9e="$(newproj p9e)"
OUT="$(run --shared "$P9e" lifecycle)" || fail "(e) exit 非 0"
echo "$OUT" | grep -q '^SKIP: codex/agy 不支援 --shared' || fail "(e) 應印 SKIP：$OUT"
[ ! -e "$P9e/.agents" ] || fail "(e) --shared 不該建 .agents"
# (f) 建不了 symlink（Windows 無開發人員模式）：複製 skill，同目錄 .plugharbor-root 記 plugin 根
P9f="$(newproj p9f)"
OUT="$(PLUGHARBOR_LINK_MODE=copy run "$P9f" lifecycle)" || fail "(f) exit 非 0：$OUT"
echo "$OUT" | grep -q '^NOTE: PLUGHARBOR_LINK_MODE=copy，使用複製模式' || fail "(f) 強制複製應印 NOTE、不說建不了 symlink：$OUT"
if echo "$OUT" | grep -q '無法建 symlink'; then fail "(f) 強制複製不該說無法建 symlink：$OUT"; fi
D="$P9f/.agents/skills/release"
ROOT_SA="$(native "$REPO_DIR/plugins/lifecycle")"
[ -d "$D" ] && [ ! -L "$D" ] && [ -f "$D/SKILL.md" ] || fail "(f) 應複製 skill 目錄"
[ "$(cat "$D/.plugharbor-root")" = "$ROOT_SA" ] || fail "(f) .plugharbor-root 應記 plugin 根：$(cat "$D/.plugharbor-root" 2>/dev/null)"
# Codex 不會讀 .plugharbor-root，也追不到複本的 plugin 根：複本裡的 ${CLAUDE_PLUGIN_ROOT} 要換成 clone 的絕對路徑
if grep -rq '\${CLAUDE_PLUGIN_ROOT}' "$D"; then fail "(f) 複本仍有 \${CLAUDE_PLUGIN_ROOT}：$(grep -rn '\${CLAUDE_PLUGIN_ROOT}' "$D" | head -2)"; fi
grep -q "$ROOT_SA/references/" "$D/SKILL.md" || fail "(f) 複本應把 plugin 根換成 $ROOT_SA"
OUT="$(PLUGHARBOR_LINK_MODE=copy run --check "$P9f" lifecycle)" || [ $? -eq 3 ] || fail "(f) --check exit 不是 0／3"
echo "$OUT" | grep -q '^UP-TO-DATE: link release' || fail "(f) 內容相同應 UP-TO-DATE：$OUT"
echo changed >> "$D/SKILL.md"
OUT="$(PLUGHARBOR_LINK_MODE=copy run --check "$P9f" lifecycle)" || [ $? -eq 3 ] || fail "(f) --check exit 不是 0／3"
echo "$OUT" | grep -q '^DIFF: .*release' || fail "(f) 內容不同應報 DIFF：$OUT"
PLUGHARBOR_LINK_MODE=copy run "$P9f" lifecycle >/dev/null || fail "(f) 重跑 exit 非 0"
if grep -q '^changed$' "$D/SKILL.md"; then fail "(f) 重跑應更新複本"; fi
# (f2) 複製模式遇到完全不含 ${CLAUDE_PLUGIN_ROOT} 的 skill（ui-ux-pro-max）不能中止（grep 沒命中＋pipefail）
P9f2="$(newproj p9f2)"
OUT="$(PLUGHARBOR_LINK_MODE=copy run "$P9f2" ui-ux)" || fail "(f2) 不含 plugin 根的 skill 讓複製模式中止：$OUT"
[ -f "$P9f2/.agents/skills/ui-ux-pro-max/SKILL.md" ] || fail "(f2) 應複製 ui-ux-pro-max"
OUT="$(PLUGHARBOR_LINK_MODE=copy run --check "$P9f" lifecycle)" || [ $? -eq 3 ] || fail "(f) --check exit 不是 0／3"
echo "$OUT" | grep -q '^UP-TO-DATE: link release' || fail "(f) 換過路徑的複本應視為一致：$OUT"
# (g) 複製模式：clone 搬家後 .plugharbor-root 過期 → --check 報 DIFF、實跑修正；root 指的 plugin 不存在 → BROKEN、實跑移除
echo "/old/clone/plugins/lifecycle" > "$D/.plugharbor-root"
OUT="$(PLUGHARBOR_LINK_MODE=copy run --check "$P9f" lifecycle)" || [ $? -eq 3 ] || fail "(g) --check exit 不是 0／3"
echo "$OUT" | grep -q '^DIFF: .*release' || fail "(g) marker 過期應報 DIFF：$OUT"
PLUGHARBOR_LINK_MODE=copy run "$P9f" lifecycle >/dev/null || fail "(g) 實跑 exit 非 0"
[ "$(cat "$D/.plugharbor-root")" = "$ROOT_SA" ] || fail "(g) 實跑應修正 marker：$(cat "$D/.plugharbor-root")"
mkdir -p "$P9f/.agents/skills/gone"; echo x > "$P9f/.agents/skills/gone/SKILL.md"; echo "$REPO_DIR/plugins/no-such" > "$P9f/.agents/skills/gone/.plugharbor-root"
OUT="$(PLUGHARBOR_LINK_MODE=copy run --check "$P9f" lifecycle)" || [ $? -eq 3 ] || fail "(g) --check exit 不是 0／3"
echo "$OUT" | grep -q '^BROKEN: .*\.agents/skills/gone' || fail "(g) 失效複本應報 BROKEN：$OUT"
PLUGHARBOR_LINK_MODE=copy run "$P9f" lifecycle >/dev/null || fail "(g) 實跑 exit 非 0"
[ ! -e "$P9f/.agents/skills/gone" ] || fail "(g) 失效複本應移除"
# (h) 沒指定連結模式：PATH 有 agy（只載入實體檔，不跟隨 symlink）→ 預設複製並說明原因；沒有 agy → 維持 symlink
P9h="$(newproj p9h)"
OUT="$(HOME="$TMP/home" PATH="$STUB:$TOOLS:/usr/bin:/bin" bash "$SCRIPT" "$P9h" lifecycle)" || fail "(h) exit 非 0：$OUT"
[ -d "$P9h/.agents/skills/release" ] && [ ! -L "$P9h/.agents/skills/release" ] && [ -f "$P9h/.agents/skills/release/.plugharbor-root" ] || fail "(h) 有 agy 應建實體複本：$OUT"
echo "$OUT" | grep -q '^NOTE: 偵測到 agy' || fail "(h) 應說明因 agy 改用複製：$OUT"
NOAGY="$TMP/stub-noagy"; mkdir -p "$NOAGY"; for c in claude codex pi; do cp "$STUB/$c" "$NOAGY/$c"; done
if [ "$CAN_LINK" -eq 1 ]; then
P9i="$(newproj p9i)"
OUT="$(HOME="$TMP/home" PATH="$NOAGY:$TOOLS:/usr/bin:/bin" bash "$SCRIPT" "$P9i" lifecycle)" || fail "(h) 無 agy exit 非 0：$OUT"
[ -L "$P9i/.agents/skills/release" ] || fail "(h) 沒有 agy 應維持 symlink：$OUT"
fi

# ---------- 10) 正式改名對照：每條新名都存在、舊名都已移除；命令列給舊名自動換新名 ----------
PAIRS="$(bash -c '. "$1/setup/lib.sh"; ph_rename_pairs' _ "$REPO_DIR")"
[ -n "$PAIRS" ] || fail "正式改名對照不該是空的"
while read -r o n; do
  [ -f "$REPO_DIR/plugins/$n/.claude-plugin/plugin.json" ] || fail "改名對照的新名不存在：$n"
  [ ! -e "$REPO_DIR/plugins/$o" ] || fail "改名對照的舊名還在：$o"
done <<< "$PAIRS"
P10="$(newproj p10)"
OUT="$(run --check "$P10" database-sqlserver desktop-avalonia)" || [ $? -eq 3 ] || fail "正式對照 --check exit 不是 0／3：$OUT"
echo "$OUT" | grep -q '^RENAME: database-sqlserver → database（改用新名）' || fail "應換成 database：$OUT"
echo "$OUT" | grep -q '^MISSING: claude desktop' || fail "應以新名 desktop 比對：$OUT"

# ---------- 11) 多個舊名併成同一新名（sa-flow、delivery-flow → lifecycle）：各卸一次，新名只裝一次 ----------
P11="$(newproj p11)"; : > "$STUB_LOG"
printf '[{"id": "sa-flow@plugharbor", "version": "0.9.0", "scope": "local", "projectPath": "%s"},\n {"id": "delivery-flow@plugharbor", "version": "0.9.0", "scope": "local", "projectPath": "%s"}]\n' \
  "$(native "$P11")" "$(native "$P11")" > "$STUB_STATE/claude-list"
OUT="$(run --check "$P11" sa-flow delivery-flow)" || [ $? -eq 3 ] || fail "(11) --check exit 不是 0／3：$OUT"
echo "$OUT" | grep -q '^RENAME: claude sa-flow → lifecycle' || fail "(11) --check 應報 RENAME: claude sa-flow：$OUT"
echo "$OUT" | grep -q '^RENAME: claude delivery-flow → lifecycle' || fail "(11) --check 應報 RENAME: claude delivery-flow：$OUT"
[ "$(echo "$OUT" | grep -c '^MISSING: claude lifecycle')" = 1 ] || fail "(11) 新名只該比對一次：$OUT"
if grep -q 'uninstall' "$STUB_LOG"; then fail "(11) --check 不該卸載"; fi
: > "$STUB_LOG"
OUT="$(run "$P11" sa-flow delivery-flow)" || fail "(11) 實跑 exit 非 0：$OUT"
[ "$(grep -c '^claude plugin install lifecycle@plugharbor --scope local$' "$STUB_LOG")" = 1 ] || fail "(11) lifecycle 應只裝一次：$(cat "$STUB_LOG")"
grep -qx 'claude plugin uninstall sa-flow@plugharbor --scope local' "$STUB_LOG" || fail "(11) 應卸 sa-flow"
grep -qx 'claude plugin uninstall delivery-flow@plugharbor --scope local' "$STUB_LOG" || fail "(11) 應卸 delivery-flow"
[ "$(grep -c '^claude plugin uninstall ' "$STUB_LOG")" = 2 ] || fail "(11) 應只卸兩次：$(cat "$STUB_LOG")"
rm "$STUB_STATE/claude-list"

# ---------- 12) 裝 lifecycle：不再停用 Superpowers（lifecycle 3.0.0 起兩者並存）；舊版寫過的停用鍵原樣保留 ----------
SP="superpowers@claude-plugins-official"; SP2="superpowers@superpowers-marketplace"
sp_val() {  # $1=settings 檔 $2=plugin id；印 enabledPlugins 的值（json 形式），沒有印 MISSING
  python3 -c 'import json,sys;d=json.load(open(sys.argv[1],encoding="utf-8"));e=d.get("enabledPlugins",{});print(json.dumps(e[sys.argv[2]]) if sys.argv[2] in e else "MISSING")' "$1" "$2"
}
printf '[{"id": "%s", "version": "5.0.0", "scope": "user"}]\n' "${SP2}" > "$STUB_STATE/claude-list"
# (a) 新專案裝 lifecycle：--check 不報 DISABLE，實跑不在 settings.local.json 寫 superpowers 鍵
P12="$(newproj p12)"
OUT="$(run --check "$P12" lifecycle)" || [ $? -eq 3 ] || fail "(12a) --check exit 不是 0／3：$OUT"
if echo "$OUT" | grep -q '^DISABLE:'; then fail "(12a) 不該再報 DISABLE：$OUT"; fi
OUT="$(run "$P12" lifecycle)" || fail "(12a) 實跑 exit 非 0：$OUT"
if echo "$OUT" | grep -q '停用 superpowers'; then fail "(12a) 不該停用 superpowers：$OUT"; fi
if [ -f "$P12/.claude/settings.local.json" ]; then
  [ "$(sp_val "$P12/.claude/settings.local.json" "${SP}")" = MISSING ] || fail "(12a) 不該寫 ${SP}：$(cat "$P12/.claude/settings.local.json")"
  [ "$(sp_val "$P12/.claude/settings.local.json" "${SP2}")" = MISSING ] || fail "(12a) 不該寫 ${SP2}"
fi
# (b) 舊版已寫入停用鍵的專案重跑：鍵原樣保留（不刪、不改 true），其他鍵不動
P12b="$(newproj p12b)"; mkdir -p "$P12b/.claude"
echo '{"permissions": {"allow": ["Bash(ls)"]}, "enabledPlugins": {"superpowers@claude-plugins-official": false, "mine@x": true}}' > "$P12b/.claude/settings.local.json"
cp "$P12b/.claude/settings.local.json" "$TMP/sl-before"
OUT="$(run "$P12b" lifecycle)" || fail "(12b) 實跑 exit 非 0：$OUT"
cmp -s "$P12b/.claude/settings.local.json" "$TMP/sl-before" || fail "(12b) settings.local.json 不該被改：$(cat "$P12b/.claude/settings.local.json")"
rm "$STUB_STATE/claude-list"

# ---------- 13) --no-claude：整段 Claude 略過（含 marketplace），pi／Codex／agy 照 local 裝；與 --shared 互斥 ----------
P13="$(newproj p13)"; : > "$STUB_LOG"
OUT="$(run --no-claude "$P13" lifecycle)" || fail "(13) --no-claude exit 非 0：$OUT"
[ "$(echo "$OUT" | grep -c '^SKIP: claude（--no-claude）$')" = 1 ] || fail "(13) 應印一次 SKIP: claude（--no-claude）：$OUT"
if grep -q '^claude ' "$STUB_LOG"; then fail "(13) --no-claude 不該呼叫 claude：$(cat "$STUB_LOG")"; fi
[ ! -e "$P13/.claude" ] || fail "(13) --no-claude 不該建 .claude（含 settings.local.json）"
grep -q "$(native "$REPO_DIR/plugins/lifecycle")" "$P13/.pi/settings.json" || fail "(13) pi 應照常寫入"
linked "$P13/.agents/skills/release" || fail "(13) codex／agy 應照常建 link：$OUT"
rc=0; run --shared --no-claude "$P13" lifecycle >/dev/null 2>&1 || rc=$?
[ "$rc" -eq 2 ] || fail "(13) --shared --no-claude 應 exit 2，實際 ${rc}"
rc=0; run --no-claude --shared "$P13" lifecycle >/dev/null 2>&1 || rc=$?
[ "$rc" -eq 2 ] || fail "(13) --no-claude --shared 應 exit 2，實際 ${rc}"
# --check：不報任何 claude／Superpowers 差異，pi／link 仍報
P13c="$(newproj p13c)"; : > "$STUB_LOG"
rc=0; OUT="$(run --no-claude --check "$P13c" lifecycle)" || rc=$?
[ "$rc" -eq 3 ] || fail "(13) --no-claude --check 有 pi／link 差異應 exit 3，實際 ${rc}：$OUT"
if echo "$OUT" | grep -q -E 'claude (lifecycle|marketplace)|DISABLE|RENAME: claude|OUTDATED: claude'; then fail "(13) --no-claude --check 不該報 claude 差異：$OUT"; fi
echo "$OUT" | grep -q '^MISSING: pi lifecycle' || fail "(13) --no-claude --check 仍應報 pi：$OUT"
if grep -q '^claude ' "$STUB_LOG"; then fail "(13) --no-claude --check 不該呼叫 claude"; fi

# ---------- 14) lifecycle 拆分遷移：lifecycle.yml 有 ticket: 就自動補 tickets；--check 也套用；舊 link 換指向 ----------
mkticket() {  # $1=專案；$2=yes 時寫 ticket: 區塊
  mkdir -p "$1/.plugharbor"
  if [ "${2:-}" = yes ]; then printf 'ticket:\n  tool: github\n' > "$1/.plugharbor/lifecycle.yml"; else printf 'spec:\n  dir: docs/specs\n' > "$1/.plugharbor/lifecycle.yml"; fi
}
# (a) 有 ticket: → 補裝 tickets
P14="$(newproj p14)"; mkticket "$P14" yes; : > "$STUB_CWD_LOG"
OUT="$(run "$P14" lifecycle)" || fail "(14a) exit 非 0：$OUT"
echo "$OUT" | grep -q 'ADD: tickets（.plugharbor/lifecycle.yml 有 ticket: 區塊）' || fail "(14a) 應印 ADD: tickets：$OUT"
grep -qx "claude plugin install tickets@plugharbor --scope local @ $P14" "$STUB_CWD_LOG" || fail "(14a) 應裝 tickets：$(cat "$STUB_CWD_LOG")"
# (b) 沒有 ticket: → 不裝
P14b="$(newproj p14b)"; mkticket "$P14b" no; : > "$STUB_CWD_LOG"
OUT="$(run "$P14b" lifecycle)" || fail "(14b) exit 非 0：$OUT"
if echo "$OUT" | grep -q 'ADD: tickets'; then fail "(14b) 不該補 tickets：$OUT"; fi
if grep -q 'install tickets@' "$STUB_CWD_LOG"; then fail "(14b) 不該裝 tickets"; fi
# (c) --check：只有 lifecycle 裝著 → tickets MISSING、exit 3
P14c="$(newproj p14c)"; mkticket "$P14c" yes
printf '[{"id": "lifecycle@plugharbor", "version": "%s", "scope": "local", "projectPath": "%s"}]\n' "$(ver lifecycle)" "$(native "$P14c")" > "$STUB_STATE/claude-list"
rc=0; OUT="$(run --check "$P14c" lifecycle)" || rc=$?
[ "$rc" -eq 3 ] || fail "(14c) --check 應 exit 3，實際 ${rc}：$OUT"
echo "$OUT" | grep -q 'ADD: tickets' || fail "(14c) --check 應印 ADD：$OUT"
echo "$OUT" | grep -q 'MISSING: claude tickets' || fail "(14c) 應報 tickets MISSING：$OUT"
rm "$STUB_STATE/claude-list"
# (d) 舊 lifecycle 的 triage link 已失效 → 移除並改指 tickets，並提示 skill 搬去哪
if [ "$CAN_LINK" -eq 1 ]; then
P14d="$(newproj p14d)"; mkticket "$P14d" yes; mkdir -p "$P14d/.agents/skills"
ln -s ../plugharbor/lifecycle/skills/triage "$P14d/.agents/skills/triage"
OUT="$(run "$P14d" lifecycle)" || fail "(14d) exit 非 0：$OUT"
echo "$OUT" | grep -q '移除失效 link' || fail "(14d) 應印移除失效 link：$OUT"
echo "$OUT" | grep -q '^NOTE: triage 已搬到 tickets（install-project.sh <專案根> tickets）' || fail "(14d) 應提示 triage 已搬到 tickets：$OUT"
[ "$(readlink "$P14d/.agents/skills/triage")" = "../plugharbor/tickets/skills/triage" ] || fail "(14d) triage 應改指 tickets：$(readlink "$P14d/.agents/skills/triage")"
else
echo "SKIP: 這台不能建 symlink，略過 14(d)"
fi
# (e) 複製模式：舊 lifecycle 的 triage 複本（.plugharbor-root 指 lifecycle）→ 移除失效複本、提示、從 tickets 重建
P14e="$(newproj p14e)"; mkticket "$P14e" yes; mkdir -p "$P14e/.agents/skills/triage"
printf 'old\n' > "$P14e/.agents/skills/triage/SKILL.md"
printf '%s\n' "$(native "$REPO_DIR/plugins/lifecycle")" > "$P14e/.agents/skills/triage/.plugharbor-root"
OUT="$(PLUGHARBOR_LINK_MODE=copy run "$P14e" lifecycle)" || fail "(14e) exit 非 0：$OUT"
echo "$OUT" | grep -q '移除失效複本' || fail "(14e) 應印移除失效複本：$OUT"
echo "$OUT" | grep -q '^NOTE: triage 已搬到 tickets' || fail "(14e) 應提示 triage 已搬到 tickets：$OUT"
[ "$(cat "$P14e/.agents/skills/triage/.plugharbor-root")" = "$(native "$REPO_DIR/plugins/tickets")" ] || fail "(14e) triage 複本應改從 tickets 建：$OUT"

echo "PASS: install-project.sh（14 組）"
