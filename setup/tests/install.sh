#!/usr/bin/env bash
# install.sh 驗證。HOME 導到暫存目錄、CLI 全換成 stub，不碰真的 ~/.claude 與真的 CLI。
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
fail() { echo "FAIL: $1"; exit 1; }
INSTALL="$REPO_DIR/setup/install.sh"
STUB="$TMP/stub"; TOOLS="$TMP/tools"
bash "$REPO_DIR/setup/tests/lib/stub-cli.sh" "$STUB" "$TOOLS"
export STUB_LOG="$TMP/cli.log" STUB_STATE="$TMP/state"
mkdir -p "$STUB_STATE"
BASE_PATH="$STUB:$TOOLS:/usr/bin:/bin"
hashes() { (cd "$1" && find . -type f | LC_ALL=C sort | while IFS= read -r f; do cksum "$f"; done); }
run() {  # $1=HOME，其餘為 install.sh 參數
  local h="$1"; shift
  HOME="$h" PATH="$BASE_PATH" PLUGHARBOR_PLUGINS="${PLUGINS-toolkit research}" bash "$INSTALL" "$@"
}

# ---------- 1) 舊 hook、重複 skill／agent、kerry.sidebar、codex 版號 ----------
H="$TMP/h1"; mkdir -p "$H/.claude/skills/config-doctor" "$H/.claude/agents"
echo "舊版" > "$H/.claude/skills/config-doctor/SKILL.md"
echo "舊版" > "$H/.claude/agents/skill-reviewer.md"
mkdir -p "$H/.claude/skills/my-own"; echo x > "$H/.claude/skills/my-own/SKILL.md"
cat > "$H/.claude/settings.json" <<'JSON'
{"model":"my-model","permissions":{"deny":["Custom(x)"]},
 "hooks":{"PreToolUse":[
   {"matcher":"Bash","hooks":[{"type":"command","command":"sh -c 'exec python3 \"$HOME/.claude/hooks/guard.py\"'"}]},
   {"matcher":"Agent","hooks":[{"type":"command","command":"python3 $HOME/.claude/hooks/agent-model-guard.py"},{"type":"command","command":"my-agent-hook.sh"}]}],
  "Notification":[{"hooks":[{"type":"command","command":"bash ~/.claude/hooks/notification.sh notify"}]}],
  "Stop":[{"hooks":[{"type":"command","command":"python3 \"$HOME/.claude/hooks/feedback-reminder.py\""}]},{"hooks":[{"type":"command","command":"/opt/my/stop"}]}]}}
JSON
TOOLKIT_VER="$(sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$REPO_DIR/plugins/toolkit/.claude-plugin/plugin.json" | head -1)"
cat > "$STUB_STATE/codex-list" <<EOF
Marketplace \`plugharbor\`
$REPO_DIR/.claude-plugin/marketplace.json

PLUGIN               STATUS              VERSION  SOURCE
toolkit@plugharbor   installed, enabled  $TOOLKIT_VER    $REPO_DIR/plugins/toolkit
research@plugharbor  installed, enabled  0.0.1    $REPO_DIR/plugins/research
EOF
printf 'Installed plugins:\r\n- toolkit (enabled, %s)\r\n    Components: 7 skills\r\n' "$TOOLKIT_VER" > "$STUB_STATE/agy-list"
cat > "$STUB_STATE/herdr-list" <<'EOF'
1 plugins installed:
- kerry.sidebar (Sidebar) enabled [local:/old/claude-home/herdr/plugins/sidebar]
  config: /x/kerry.sidebar
EOF
: > "$STUB_LOG"
OUT="$(run "$H")" || fail "install exit 非 0：$OUT"
C="$H/.claude"
[ -f "$C/CLAUDE.md" ]                    || fail "CLAUDE.md 未安裝"
[ -f "$C/shared/engineering.md" ]        || fail "shared/ 未安裝"
[ -f "$C/rules/git-safety.md" ]          || fail "rules/ 未安裝"
[ -f "$C/statusline.sh" ]                || fail "statusline.sh 未安裝"
[ -f "$C/hooks/herdr-parent-tag.py" ]    || fail "herdr-parent-tag.py 未安裝"
# 舊 hook 移除、備份存在、本機自加的保留、herdr-parent-tag 補上
for old in guard.py agent-model-guard.py notification.sh feedback-reminder.py; do
  if grep -q "$old" "$C/settings.json"; then fail "舊 hook $old 未移除"; fi
done
grep -q 'my-agent-hook.sh' "$C/settings.json" || fail "同組裡本機自加的 hook 被移除"
grep -q '/opt/my/stop'     "$C/settings.json" || fail "本機自加的 Stop hook 被移除"
grep -q '"my-model"'       "$C/settings.json" || fail "settings 合併弄丟既有值"
grep -q 'Custom(x)'        "$C/settings.json" || fail "settings 合併弄丟既有清單項"
grep -q 'bash ~/.claude/statusline.sh' "$C/settings.json" || fail "statusLine 未補上"
[ "$(grep -o 'herdr-parent-tag.py' "$C/settings.json" | wc -l | tr -d ' ')" = 2 ] || fail "herdr-parent-tag 應有 Pre／Post 各一筆"
if grep -q '"Notification"' "$C/settings.json"; then fail "清空的 Notification 事件應移除"; fi
BK="$(ls -d "$C"/backups/plugharbor-* 2>/dev/null | head -1)"
[ -n "$BK" ] && grep -q 'guard.py' "$BK/settings.json" || fail "舊 hook 移除前未備份 settings.json"
# 重複偵測：沒 --yes 只報不搬
echo "$OUT" | grep -q '^DUP: skills/config-doctor' || fail "沒印 DUP: skills/config-doctor：$OUT"
echo "$OUT" | grep -q '^DUP: agents/skill-reviewer.md' || fail "沒印 DUP: agents/skill-reviewer.md"
if echo "$OUT" | grep -q 'DUP: skills/my-own'; then fail "非 plugharbor 的 skill 不該報 DUP"; fi
[ -f "$C/skills/config-doctor/SKILL.md" ] || fail "沒 --yes 不該搬走 config-doctor"
# CLI
echo "$OUT" | grep -q '^SKIP: pi' || fail "沒有 pi 應印 SKIP: pi"
grep -qx "claude plugin marketplace add $REPO_DIR" "$STUB_LOG" || fail "claude 未註冊 marketplace"
grep -qx "claude plugin install toolkit@plugharbor --scope user" "$STUB_LOG" || fail "claude 未安裝 toolkit"
grep -qx "claude plugin install research@plugharbor --scope user" "$STUB_LOG" || fail "claude 未安裝 research"
if grep -q "codex plugin add toolkit@plugharbor" "$STUB_LOG"; then fail "codex 版號相同不該重裝 toolkit"; fi
grep -qx "codex plugin add research@plugharbor" "$STUB_LOG" || fail "codex 版號不同應重裝 research"
echo "$OUT" | grep -q 'UP-TO-DATE: codex toolkit' || fail "codex 版號相同應印 UP-TO-DATE"
if grep -q "codex plugin marketplace add" "$STUB_LOG"; then fail "codex 已有 plugharbor marketplace 不該再 add"; fi
if grep -q "agy plugin install $REPO_DIR/plugins/toolkit" "$STUB_LOG"; then fail "agy 版號相同（CRLF 輸出）不該重裝 toolkit"; fi
grep -qx "agy plugin install $REPO_DIR/plugins/research" "$STUB_LOG" || fail "agy 未安裝 research"
grep -qx "herdr plugin unlink kerry.sidebar" "$STUB_LOG" || fail "herdr 未 unlink kerry.sidebar"
grep -qx "herdr plugin link $REPO_DIR/setup/herdr/plugins/sidebar" "$STUB_LOG" || fail "herdr 未 link 新 sidebar"
[ -f "$H/.codex/AGENTS.md" ] || fail "adapter 未產生 Codex AGENTS.md"

# ---------- 2) 重跑：所有檔案 hash 不變 ----------
hashes "$H" > "$TMP/before"
run "$H" >/dev/null || fail "第二次 install exit 非 0"
hashes "$H" > "$TMP/after"
diff "$TMP/before" "$TMP/after" >/dev/null || fail "重跑不冪等：$(diff "$TMP/before" "$TMP/after" | head -5)"

# ---------- 3) --check 只報不改 ----------
echo "改過" > "$C/rules/git-safety.md"
hashes "$H" > "$TMP/before"
OUT="$(run "$H" --check)" || fail "--check exit 非 0"
hashes "$H" > "$TMP/after"
diff "$TMP/before" "$TMP/after" >/dev/null || fail "--check 改了檔案"
echo "$OUT" | grep -q 'DIFF: *rules/git-safety.md' || fail "--check 沒報 rules 差異：$OUT"
echo "$OUT" | grep -q 'DUP: skills/config-doctor' || fail "--check 沒報 DUP"

# ---------- 4) 衝突預設不覆蓋，--force 覆蓋且先備份 ----------
run "$H" >/dev/null
grep -q "改過" "$C/rules/git-safety.md" || fail "未加 --force 卻覆蓋使用者檔案"
run "$H" --force >/dev/null
if grep -q "改過" "$C/rules/git-safety.md"; then fail "--force 未覆蓋"; fi
ls "$C"/backups/plugharbor-*/rules/git-safety.md >/dev/null 2>&1 || fail "--force 未備份"

# ---------- 5) --yes 把重複的搬進備份 ----------
OUT="$(run "$H" --yes)" || fail "--yes exit 非 0"
[ ! -e "$C/skills/config-doctor" ]   || fail "--yes 後 config-doctor 應搬走"
[ ! -e "$C/agents/skill-reviewer.md" ] || fail "--yes 後 skill-reviewer.md 應搬走"
ls -d "$C"/backups/plugharbor-*/skills/config-doctor >/dev/null 2>&1 || fail "config-doctor 未搬進備份"
[ -d "$C/skills/my-own" ] || fail "非 plugharbor 的 skill 不該被搬"

# ---------- 6) 有 pi：packages 加相對路徑，保留其他項目，重跑不重複 ----------
bash "$REPO_DIR/setup/tests/lib/stub-cli.sh" "$STUB" "$TOOLS" pi
H="$TMP/h2"; mkdir -p "$H/.pi/agent"
printf '{\n  "packages": ["npm:keep-me"],\n  "defaultModel": "x"\n}\n' > "$H/.pi/agent/settings.json"
OUT="$(PLUGINS="toolkit research backend-dotnet" run "$H")" || fail "有 pi 的 install exit 非 0"
echo "$OUT" | grep -q '^SKIP: pi backend-dotnet' || fail "沒有 pi 設定的 plugin 應印 SKIP：$OUT"
P="$H/.pi/agent/settings.json"
grep -q 'npm:keep-me' "$P" || fail "pi packages 既有項目被移除"
grep -q '"defaultModel": "x"' "$P" || fail "pi settings 其他鍵被動過"
if grep -q 'plugins/backend-dotnet' "$P"; then fail "沒有 pi 設定的 plugin 不該加進 packages"; fi
REL_TK="$(sed -n 's/^ *"\(\.\.[^"]*plugins\/toolkit\)",*$/\1/p' "$P")"
# pi 以字串方式（node path.resolve）解析相對 ~/.pi/agent 的路徑，不走實體 symlink（macOS 的 /var → /private/var）
ABS_TK="$(python3 -c 'import os,sys;print(os.path.normpath(os.path.join(sys.argv[1], sys.argv[2])))' "$H/.pi/agent" "$REL_TK")"
[ -n "$REL_TK" ] && [ "$ABS_TK" = "$REPO_DIR/plugins/toolkit" ] || fail "pi packages 未加指向 toolkit 的相對路徑：$(cat "$P")"
[ "$(head -2 "$P" | tail -1 | tr -d ' ')" = '"packages":[' ] || fail "pi settings 鍵順序被改：$(cat "$P")"
cp "$P" "$TMP/pi1"; run "$H" >/dev/null
cmp -s "$P" "$TMP/pi1" || fail "pi packages 重跑不冪等"
rm "$STUB/pi"

# ---------- 7) 沒有 node、沒有 herdr：清楚 SKIP，exit 0 ----------
mv "$STUB/herdr" "$TMP/herdr.off"; rm -f "$TOOLS/node"
H="$TMP/h3"; mkdir -p "$H"
if PATH="$BASE_PATH" command -v node >/dev/null 2>&1; then
  echo "NOTE: 系統目錄有 node，略過「沒有 node」案例"
else
  OUT="$(run "$H")" || fail "沒有 node 時 exit 非 0：$OUT"
  echo "$OUT" | grep -q '^SKIP: node' || fail "沒有 node 應印 SKIP: node：$OUT"
fi
OUT="$(run "$H")" || fail "沒有 herdr 時 exit 非 0"
echo "$OUT" | grep -q '^SKIP: herdr' || fail "沒有 herdr 應印 SKIP: herdr"
mv "$TMP/herdr.off" "$STUB/herdr"

# ---------- 8) 預設裝全部 plugin ----------
H="$TMP/h4"; mkdir -p "$H"; : > "$STUB_LOG"
PLUGINS="" run "$H" >/dev/null || fail "預設 plugin 清單 install exit 非 0"
N_ALL="$(ls -d "$REPO_DIR"/plugins/*/.claude-plugin | wc -l | tr -d ' ')"
[ "$(grep -c '^claude plugin install ' "$STUB_LOG")" = "$N_ALL" ] || fail "預設應裝全部 $N_ALL 個 plugin"

echo "PASS: install.sh（8 組）"
