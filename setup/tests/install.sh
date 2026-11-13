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
  HOME="$h" PATH="${RUN_PATH:-$BASE_PATH}" PLUGHARBOR_PLUGINS="${PLUGINS-toolkit research}" bash "$INSTALL" "$@"
}

# ---------- 1) 舊 hook、重複 skill／agent、kerry.sidebar、codex 版號 ----------
H="$TMP/h1"; mkdir -p "$H/.claude/skills/config-doctor" "$H/.claude/agents"
echo "舊版" > "$H/.claude/skills/config-doctor/SKILL.md"
echo "舊版" > "$H/.claude/agents/skill-reviewer.md"
mkdir -p "$H/.claude/skills/my-own"; echo x > "$H/.claude/skills/my-own/SKILL.md"
old_settings() {  # $1=settings.json 路徑：含舊 claude-home hook，也含名字相近但不該動的
  cat > "$1" <<'JSON'
{"model":"my-model","permissions":{"deny":["Custom(x)"],"ask":["Bash(rm -rf *)","Bash(rm -r -f *)","Bash(my-ask *)"]},
 "hooks":{"PreToolUse":[
   {"matcher":"Bash","hooks":[{"type":"command","command":"sh -c 'exec python3 \"$HOME/.claude/hooks/guard.py\"'"}]},
   {"matcher":"Agent","hooks":[{"type":"command","command":"python3 $HOME/.claude/hooks/agent-model-guard.py"},{"type":"command","command":"my-agent-hook.sh"}]},
   {"matcher":"Edit","hooks":[{"type":"command","command":"python3 ~/.claude/hooks/guard.pyx"},{"type":"command","command":"python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/guard.py\""}]}],
  "Notification":[{"hooks":[{"type":"command","command":"bash ~/.claude/hooks/notification.sh notify"}]}],
  "Stop":[{"hooks":[{"type":"command","command":"python3 \"$HOME/.claude/hooks/feedback-reminder.py\""}]},{"hooks":[{"type":"command","command":"/opt/my/stop"}]}]}}
JSON
}
old_settings "$H/.claude/settings.json"
mkdir -p "$H/.codex"; echo '{"hooks":{"Stop":[{"hooks":[{"type":"command","command":"my-codex-stop"}]}]}}' > "$H/.codex/hooks.json"
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
[ -f "$C/subagent-statusline.sh" ]       || fail "subagent-statusline.sh 未安裝"
[ -f "$C/hooks/herdr-parent-tag.py" ]    || fail "herdr-parent-tag.py 未安裝"
# 舊 hook 移除、備份存在、本機自加的保留、herdr-parent-tag 補上
for old in 'exec python3' agent-model-guard.py notification.sh feedback-reminder.py; do
  if grep -qF "$old" "$C/settings.json"; then fail "舊 hook $old 未移除"; fi
done
grep -q 'guard.pyx' "$C/settings.json" || fail "guard.pyx 不是舊 hook，不該移除"
grep -q 'CLAUDE_PROJECT_DIR/.claude/hooks/guard.py' "$C/settings.json" || fail "專案層的 guard.py 不該移除"
grep -q 'my-agent-hook.sh' "$C/settings.json" || fail "同組裡本機自加的 hook 被移除"
grep -q '/opt/my/stop'     "$C/settings.json" || fail "本機自加的 Stop hook 被移除"
grep -q '"my-model"'       "$C/settings.json" || fail "settings 合併弄丟既有值"
grep -q 'Custom(x)'        "$C/settings.json" || fail "settings 合併弄丟既有清單項"
if grep -qF 'Bash(rm -rf *)' "$C/settings.json" || grep -qF 'Bash(rm -r -f *)' "$C/settings.json"; then fail "已退役的 rm ask 規則未移除"; fi
grep -qF 'Bash(my-ask *)'  "$C/settings.json" || fail "本機自加的 ask 規則被移除"
grep -q 'bash ~/.claude/statusline.sh' "$C/settings.json" || fail "statusLine 未補上"
grep -q 'bash ~/.claude/subagent-statusline.sh' "$C/settings.json" || fail "subagentStatusLine 未補上"
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
grep -qx "claude plugin marketplace add https://github.com/KerryHuang/plugharbor.git" "$STUB_LOG" || fail "claude 應以 GitHub 來源註冊 marketplace"
grep -qx "claude plugin install toolkit@plugharbor --scope user" "$STUB_LOG" || fail "claude 未安裝 toolkit"
grep -qx "claude plugin install research@plugharbor --scope user" "$STUB_LOG" || fail "claude 未安裝 research"
if grep -q "codex plugin add toolkit@plugharbor" "$STUB_LOG"; then fail "codex 版號相同不該重裝 toolkit"; fi
grep -qx "codex plugin add research@plugharbor" "$STUB_LOG" || fail "codex 版號不同應重裝 research"
# codex 的 marketplace 是本機目錄（plugin add 直接讀 clone），upgrade 只對 git 來源有效，呼叫必失敗
if grep -q 'codex plugin marketplace upgrade' "$STUB_LOG"; then fail "codex 本機目錄 marketplace 不該呼叫 upgrade"; fi
grep -q 'my-codex-stop' "$H/.codex/hooks.json" || fail "Codex hooks.json 使用者的條目被移除"
ls "$C"/backups/plugharbor-*/codex/hooks.json >/dev/null 2>&1 || fail "Codex hooks.json 改動前未備份"
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
OUT="$(run "$H" --check)" || [ $? -eq 3 ] || fail "--check exit 不是 0／3"
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
OUT="$(PLUGINS="toolkit research" run "$H")" || fail "有 pi 的 install exit 非 0"
P="$H/.pi/agent/settings.json"
grep -q 'npm:keep-me' "$P" || fail "pi packages 既有項目被移除"
grep -q '"defaultModel": "x"' "$P" || fail "pi settings 其他鍵被動過"
REL_TK="$(sed -n 's/^ *"\(\.\.[^"]*plugins\/toolkit\)",*$/\1/p' "$P")"
# pi 以字串方式（node path.resolve）解析相對 ~/.pi/agent 的路徑，不走實體 symlink（macOS 的 /var → /private/var）
ABS_TK="$(python3 -c 'import os,sys;print(os.path.normpath(os.path.join(sys.argv[1], sys.argv[2])))' "$H/.pi/agent" "$REL_TK")"
# 期望值也經同一個 python normpath：Windows 上兩邊都會變成 C:\ 形式，直接比 $REPO_DIR（/c/...）比不上
EXP_TK="$(python3 -c 'import os,sys;print(os.path.normpath(sys.argv[1]))' "$REPO_DIR/plugins/toolkit")"
[ -n "$REL_TK" ] && [ "$ABS_TK" = "$EXP_TK" ] || fail "pi packages 未加指向 toolkit 的相對路徑：$(cat "$P")"
[ "$(head -2 "$P" | tail -1 | tr -d ' ')" = '"packages":[' ] || fail "pi settings 鍵順序被改：$(cat "$P")"
PB="$(ls "$H"/.claude/backups/plugharbor-*/pi/settings.json 2>/dev/null | head -1)"
[ -n "$PB" ] && grep -q 'npm:keep-me' "$PB" && ! grep -q 'plugins/toolkit' "$PB" || fail "pi settings 改動前未備份原檔"
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

# ---------- 8) 預設只裝 user 層 4 個 ----------
H="$TMP/h4"; mkdir -p "$H"; : > "$STUB_LOG"
PLUGINS="" run "$H" >/dev/null || fail "預設 plugin 清單 install exit 非 0"
[ "$(grep -c '^claude plugin install ' "$STUB_LOG")" = 4 ] || fail "預設應只裝 user 層 4 個：$(grep '^claude plugin install ' "$STUB_LOG")"
for p in toolkit research browser-docs workspace; do
  grep -qx "claude plugin install $p@plugharbor --scope user" "$STUB_LOG" || fail "預設應裝 user 層 $p"
done
if grep -q '^claude plugin install lifecycle' "$STUB_LOG"; then fail "專案層 lifecycle 不該裝到 user 層"; fi

# ---------- 9) 沒有 claude：舊 hook 保留並印 STALE（沒有 toolkit 替代就不拿掉 guard） ----------
NOCLAUDE="$TMP/stub-noclaude"
bash "$REPO_DIR/setup/tests/lib/stub-cli.sh" "$NOCLAUDE" "$TOOLS" codex agy herdr
H="$TMP/h5"; mkdir -p "$H/.claude"; old_settings "$H/.claude/settings.json"
OUT="$(RUN_PATH="$NOCLAUDE:$TOOLS:/usr/bin:/bin" run "$H")" || fail "沒有 claude 時 exit 非 0"
echo "$OUT" | grep -q '^SKIP: claude' || fail "沒有 claude 應印 SKIP: claude"
grep -q 'agent-model-guard.py' "$H/.claude/settings.json" || fail "沒有 claude 時不該移除舊 guard hook"
echo "$OUT" | grep -q 'STALE: *settings.json hooks.PreToolUse agent-model-guard.py' || fail "沒有 claude 時應印 STALE：$OUT"
if ls -d "$H"/.claude/backups/plugharbor-* >/dev/null 2>&1; then fail "沒清理就不該產生備份"; fi

# ---------- 10) 沒選 toolkit：舊 hook 保留 ----------
H="$TMP/h6"; mkdir -p "$H/.claude"; old_settings "$H/.claude/settings.json"
OUT="$(PLUGINS="research" run "$H")" || fail "只裝 research 時 exit 非 0"
grep -q 'agent-model-guard.py' "$H/.claude/settings.json" || fail "沒裝 toolkit 時不該移除舊 guard hook"
echo "$OUT" | grep -q '^STALE: ' || fail "沒裝 toolkit 時應印 STALE"

# ---------- 11) claude 裝 toolkit 失敗：舊 hook 保留、exit 1 ----------
export STUB_STATE="$TMP/state-fail"; mkdir -p "$STUB_STATE"
echo "claude plugin install toolkit@plugharbor --scope user" > "$STUB_STATE/fail"
H="$TMP/h7"; mkdir -p "$H/.claude"; old_settings "$H/.claude/settings.json"
if OUT="$(run "$H")"; then fail "claude 安裝失敗時應 exit 1"; fi
echo "$OUT" | grep -q '^FAIL: claude plugin install toolkit' || fail "沒印 claude 安裝失敗：$OUT"
grep -q 'agent-model-guard.py' "$H/.claude/settings.json" || fail "toolkit 沒裝好就不該移除舊 guard hook"

# ---------- 12) claude 升級：版號相同 UP-TO-DATE、不同先 marketplace update 再 plugin update ----------
export STUB_STATE="$TMP/state-up"; mkdir -p "$STUB_STATE"
echo '[{"name": "plugharbor", "source": "git", "url": "https://github.com/KerryHuang/plugharbor.git"}]' > "$STUB_STATE/claude-mkt"
printf '[{"id": "toolkit@plugharbor", "version": "%s", "scope": "user"},\n {"id": "research@plugharbor", "version": "0.0.1", "scope": "user"},\n {"id": "research@plugharbor", "version": "9.9.9", "scope": "project"}]\n' "$TOOLKIT_VER" > "$STUB_STATE/claude-list"
H="$TMP/h8"; mkdir -p "$H/.claude"; old_settings "$H/.claude/settings.json"; : > "$STUB_LOG"
OUT="$(run "$H")" || fail "claude 升級情境 exit 非 0：$OUT"
if grep -q 'claude plugin marketplace add' "$STUB_LOG"; then fail "已有 marketplace 不該再 add"; fi
echo "$OUT" | grep -q "UP-TO-DATE: claude toolkit $TOOLKIT_VER" || fail "claude 版號相同應 UP-TO-DATE"
if grep -q 'claude plugin \(install\|update\) toolkit' "$STUB_LOG"; then fail "claude 版號相同不該重裝 toolkit"; fi
grep -qx 'claude plugin update research@plugharbor --scope user' "$STUB_LOG" || fail "claude 版號不同應 update research"
[ "$(grep -n '^claude plugin marketplace update plugharbor$' "$STUB_LOG" | cut -d: -f1)" -lt "$(grep -n '^claude plugin update research' "$STUB_LOG" | cut -d: -f1)" ] \
  || fail "claude update 前應先 marketplace update"
if grep -q 'agent-model-guard.py' "$H/.claude/settings.json"; then fail "toolkit 已是最新也算裝好，應移除舊 hook"; fi
# marketplace 更新失敗：只警告，照樣 update
echo "claude plugin marketplace update plugharbor" > "$STUB_STATE/fail"; : > "$STUB_LOG"
OUT="$(run "$H")" || fail "marketplace update 失敗不該讓 install 失敗：$OUT"
echo "$OUT" | grep -q '^WARN: claude plugin marketplace update plugharbor' || fail "marketplace update 失敗應印 WARN"
grep -qx 'claude plugin update research@plugharbor --scope user' "$STUB_LOG" || fail "marketplace update 失敗後仍應 update"
export STUB_STATE="$TMP/state"

# ---------- 13) python 偵測：先 python3、要 3.6 以上 ----------
REAL_PY="$(command -v python3)"
PYS="$TMP/pys"; mkdir -p "$PYS"
printf '#!/bin/sh\nexit 1\n' > "$PYS/python3"
printf '#!/bin/sh\nexec "%s" "$@"\n' "$REAL_PY" > "$PYS/python"
chmod +x "$PYS/python3" "$PYS/python"
GOT="$(PATH="$PYS:/usr/bin:/bin" REPO_DIR="$REPO_DIR" bash -c '. "$REPO_DIR/setup/lib.sh"; echo "$PY"')"
[ "$GOT" = python ] || fail "python3 壞掉時應改用 python，實得「${GOT}」"
# 版本檢查失敗（例如 python 2.x）就不採用
printf '#!/bin/sh\ncase "$2" in *version_info*) exit 1 ;; esac\nexec "%s" "$@"\n' "$REAL_PY" > "$PYS/python"
GOT="$(PATH="$PYS:/usr/bin:/bin" REPO_DIR="$REPO_DIR" bash -c '. "$REPO_DIR/setup/lib.sh"; echo "$PY"')"
if [ "$GOT" = python ]; then fail "版本檢查沒過的 python 不該採用"; fi
GOT="$(PATH="$STUB:$TOOLS:/usr/bin:/bin" REPO_DIR="$REPO_DIR" bash -c '. "$REPO_DIR/setup/lib.sh"; echo "$PY"')"
[ "$GOT" = python3 ] || fail "python3 正常時應優先用 python3，實得「${GOT}」"

# ---------- 14) PLUGHARBOR_PLUGINS 有萬用字元或不存在的名字：拒絕 ----------
H="$TMP/h9"; mkdir -p "$H"
if (cd "$REPO_DIR/plugins" && PLUGINS='*' run "$H" >/dev/null); then fail "PLUGHARBOR_PLUGINS='*' 應被拒絕"; fi

# ---------- 15) marketplace 偵測：輸出很長（真實 codex plugin list 數百行）時，pipefail 下不能因 SIGPIPE 誤判沒有 ----------
. "$REPO_DIR/setup/lib.sh"
BIG="$(printf 'Marketplace `plugharbor`\n'; for i in $(seq 1 3000); do printf 'filler-%s@other  not installed  https://example.invalid/some/long/path/%s\n' "$i" "$i"; done)"
printf '%s\n' "$BIG" | ph_codex_has_marketplace || fail "codex 輸出很長時偵測不到 plugharbor marketplace"
BIGJ="$(printf '[{"name": "plugharbor"}'; for i in $(seq 1 3000); do printf ',{"name": "filler-%s", "source": "https://example.invalid/long/path/%s"}' "$i" "$i"; done; printf ']')"
printf '%s\n' "$BIGJ" | ph_claude_has_marketplace || fail "claude 輸出很長時偵測不到 plugharbor marketplace"

# ---------- 16) 舊的本機目錄 marketplace：先 remove 再以 GitHub 來源重加 ----------
export STUB_STATE="$TMP/state-dir"; mkdir -p "$STUB_STATE"
echo '[{"name": "plugharbor", "source": "directory", "path": "/old/clone"}]' > "$STUB_STATE/claude-mkt"
H="$TMP/h10"; mkdir -p "$H"; : > "$STUB_LOG"
OUT="$(run "$H")" || fail "目錄來源遷移 exit 非 0：$OUT"
RM="$(grep -n '^claude plugin marketplace remove plugharbor$' "$STUB_LOG" | cut -d: -f1)"
AD="$(grep -n '^claude plugin marketplace add https://github.com/KerryHuang/plugharbor.git$' "$STUB_LOG" | cut -d: -f1)"
[ -n "$RM" ] && [ -n "$AD" ] && [ "$RM" -lt "$AD" ] || fail "目錄來源應先 remove 再加 GitHub 來源：$(cat "$STUB_LOG")"
OUT="$(run "$H" --check)" || [ $? -eq 3 ] || fail "--check exit 不是 0／3"
echo "$OUT" | grep -q 'STALE: claude marketplace plugharbor' || fail "--check 應報目錄來源 STALE：$OUT"
export STUB_STATE="$TMP/state"

# ---------- 17) 專案層 plugin 裝在 user 層：四個 CLI 都移除；專案 scope 不動；PLUGHARBOR_PLUGINS 指定的保留 ----------
bash "$REPO_DIR/setup/tests/lib/stub-cli.sh" "$STUB" "$TOOLS" pi
export STUB_STATE="$TMP/state-proj"; mkdir -p "$STUB_STATE"
echo '[{"name": "plugharbor", "source": "git"}]' > "$STUB_STATE/claude-mkt"
printf '[{"id": "lifecycle@plugharbor", "version": "1.0.0", "scope": "user"},\n {"id": "blog@plugharbor", "version": "1.0.0", "scope": "user"},\n {"id": "ui-ux@plugharbor", "version": "1.0.0", "scope": "local", "projectPath": "/p"}]\n' > "$STUB_STATE/claude-list"
{
  echo 'Marketplace `plugharbor`'
  echo "lifecycle@plugharbor   installed, enabled  1.0.0    $REPO_DIR/plugins/lifecycle"
  echo "ui-ux@plugharbor    not installed       1.0.0    $REPO_DIR/plugins/ui-ux"
} > "$STUB_STATE/codex-list"
printf 'Installed plugins:\n- lifecycle (enabled, 1.0.0)\n' > "$STUB_STATE/agy-list"
H="$TMP/h11"; mkdir -p "$H/.pi/agent"
python3 -c 'import json,os,sys;h,r=sys.argv[1],sys.argv[2];d=os.path.join(h,".pi/agent");json.dump({"packages":["npm:keep-me",os.path.relpath(os.path.join(r,"plugins/lifecycle"),d).replace(os.sep,"/"),os.path.relpath(os.path.join(r,"plugins/toolkit"),d).replace(os.sep,"/")]},open(os.path.join(d,"settings.json"),"w"))' "$H" "$REPO_DIR"
cp "$H/.pi/agent/settings.json" "$TMP/pi-before"
OUT="$(run "$H" --check)" || [ $? -eq 3 ] || fail "--check exit 不是 0／3"
for x in "claude lifecycle" "claude blog" "codex lifecycle" "agy lifecycle" "pi lifecycle"; do
  echo "$OUT" | grep -q "STALE: ${x}（專案層" || fail "--check 應報 STALE: ${x}：$OUT"
done
cmp -s "$H/.pi/agent/settings.json" "$TMP/pi-before" || fail "--check 不該改 pi settings"
: > "$STUB_LOG"
OUT="$(PLUGINS="toolkit research blog" run "$H")" || fail "移除專案層 exit 非 0：$OUT"
grep -qx 'claude plugin uninstall lifecycle@plugharbor --scope user' "$STUB_LOG" || fail "claude 應移除 user 層 lifecycle"
if grep -q 'claude plugin uninstall blog' "$STUB_LOG"; then fail "PLUGHARBOR_PLUGINS 指定的 blog 不該移除"; fi
if grep -q 'uninstall ui-ux' "$STUB_LOG"; then fail "local scope 的 ui-ux 不該動"; fi
grep -qx 'codex plugin remove lifecycle@plugharbor' "$STUB_LOG" || fail "codex 應移除 lifecycle"
if grep -q 'codex plugin remove ui-ux' "$STUB_LOG"; then fail "codex 沒裝的 ui-ux 不該移除"; fi
grep -qx 'agy plugin uninstall lifecycle' "$STUB_LOG" || fail "agy 應移除 lifecycle"
P="$H/.pi/agent/settings.json"
if grep -q 'plugins/lifecycle' "$P"; then fail "pi packages 應移除 lifecycle：$(cat "$P")"; fi
grep -q 'npm:keep-me' "$P" && grep -q 'plugins/toolkit' "$P" || fail "pi packages 其他項目被動到：$(cat "$P")"
ls "$H"/.claude/backups/plugharbor-*/pi/settings.json >/dev/null 2>&1 || fail "pi settings 移除前未備份"
rm "$STUB/pi"
export STUB_STATE="$TMP/state"

# ---------- 18) Git Bash（有 cygpath）：交給 Windows 原生 python 的 pi 路徑要先轉成 C:/ 形式 ----------
bash "$REPO_DIR/setup/tests/lib/stub-cli.sh" "$STUB" "$TOOLS" pi
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
H="$TMP/h12"; mkdir -p "$H/.pi/agent"; : > "$STUB_LOG"
run "$H" >/dev/null || fail "有 cygpath 的 install exit 非 0"
grep -qx "cygpath -m $H/.pi/agent" "$STUB_LOG" || fail "pi 設定目錄應先經 cygpath -m 轉換：$(grep cygpath "$STUB_LOG")"
grep -qx "cygpath -m $REPO_DIR/plugins/toolkit" "$STUB_LOG" || fail "pi package 路徑應先經 cygpath -m 轉換"
rm "$STUB/pi" "$STUB/cygpath"

# ---------- 19) 舊名→新名：--check 報 RENAME，實跑在四個 CLI 卸舊名，不裝舊名 ----------
bash "$REPO_DIR/setup/tests/lib/stub-cli.sh" "$STUB" "$TOOLS" pi
export STUB_STATE="$TMP/state-rename"; mkdir -p "$STUB_STATE"
echo '[{"name": "plugharbor", "source": "git"}]' > "$STUB_STATE/claude-mkt"
printf '[{"id": "old-tool@plugharbor", "version": "0.9.0", "scope": "user"}]\n' > "$STUB_STATE/claude-list"
{
  echo 'Marketplace `plugharbor`'
  echo "old-tool@plugharbor  installed, enabled  0.9.0    $REPO_DIR/plugins/old-tool"
} > "$STUB_STATE/codex-list"
printf 'Installed plugins:\n- old-tool (enabled, 0.9.0)\n' > "$STUB_STATE/agy-list"
H="$TMP/h13"; mkdir -p "$H/.pi/agent"
python3 -c 'import json,os,sys;h,r=sys.argv[1],sys.argv[2];d=os.path.join(h,".pi/agent");json.dump({"packages":["npm:keep-me",os.path.relpath(os.path.join(r,"plugins/old-tool"),d).replace(os.sep,"/")]},open(os.path.join(d,"settings.json"),"w"))' "$H" "$REPO_DIR"
cp "$H/.pi/agent/settings.json" "$TMP/pi-before"
OUT="$(PLUGHARBOR_RENAMES="old-tool:toolkit" run "$H" --check)" || [ $? -eq 3 ] || fail "改名 --check exit 不是 0／3：$OUT"
for x in claude codex agy pi; do
  echo "$OUT" | grep -q "^RENAME: $x old-tool → toolkit" || fail "--check 應報 RENAME: $x old-tool → toolkit：$OUT"
done
cmp -s "$H/.pi/agent/settings.json" "$TMP/pi-before" || fail "--check 不該改 pi settings"
: > "$STUB_LOG"
OUT="$(PLUGHARBOR_RENAMES="old-tool:toolkit" run "$H")" || fail "改名實跑 exit 非 0：$OUT"
grep -qx 'claude plugin uninstall old-tool@plugharbor --scope user' "$STUB_LOG" || fail "claude 應卸 old-tool：$(cat "$STUB_LOG")"
grep -qx 'codex plugin remove old-tool@plugharbor' "$STUB_LOG" || fail "codex 應卸 old-tool"
grep -qx 'agy plugin uninstall old-tool' "$STUB_LOG" || fail "agy 應卸 old-tool"
if grep -q ' install old-tool\| add old-tool' "$STUB_LOG"; then fail "不該安裝舊名"; fi
grep -qx 'claude plugin install toolkit@plugharbor --scope user' "$STUB_LOG" || fail "新名 toolkit 應照常安裝"
P="$H/.pi/agent/settings.json"
if grep -q 'plugins/old-tool' "$P"; then fail "pi 應移除 old-tool：$(cat "$P")"; fi
grep -q 'npm:keep-me' "$P" && grep -q 'plugins/toolkit' "$P" || fail "pi 其他項目被動到或新名沒加：$(cat "$P")"

# ---------- 20) 舊名與新名都已安裝、新名是最新：只卸舊名，不重裝新名 ----------
printf '[{"id": "old-tool@plugharbor", "version": "0.9.0", "scope": "user"},\n {"id": "toolkit@plugharbor", "version": "%s", "scope": "user"}]\n' "$TOOLKIT_VER" > "$STUB_STATE/claude-list"
mkdir -p "$TMP/h14" "$TMP/h15"; : > "$STUB_LOG"
OUT="$(PLUGHARBOR_RENAMES="old-tool:toolkit" PLUGINS="toolkit" run "$TMP/h14")" || fail "新舊並存 exit 非 0：$OUT"
grep -qx 'claude plugin uninstall old-tool@plugharbor --scope user' "$STUB_LOG" || fail "新舊並存應卸舊名"
if grep -q '^claude plugin \(install\|update\) toolkit' "$STUB_LOG"; then fail "新名已是最新不該重裝：$(cat "$STUB_LOG")"; fi

# ---------- 21) 沒有改名對照（正式值）：不印 RENAME ----------
OUT="$(run "$TMP/h15" --check)" || [ $? -eq 3 ] || fail "無對照 --check exit 不是 0／3"
if echo "$OUT" | grep -q '^RENAME:'; then fail "沒有對照不該印 RENAME：$OUT"; fi
# 新名是專案層：訊息要指向 install-project.sh，不能說「新名照常安裝」
printf '[{"id": "old-blog@plugharbor", "version": "0.9.0", "scope": "user"}]\n' > "$STUB_STATE/claude-list"
OUT="$(PLUGHARBOR_RENAMES="old-blog:blog" run "$TMP/h15" --check)" || [ $? -eq 3 ] || fail "專案層改名 --check exit 不是 0／3"
echo "$OUT" | grep -q '^RENAME: claude old-blog → blog.*install-project.sh' || fail "專案層新名應指向 install-project.sh：$OUT"
if echo "$OUT" | grep -q '^RENAME: claude old-blog.*照常安裝'; then fail "專案層新名不該說照常安裝：$OUT"; fi

# ---------- 22) 正式對照 dev-flow → workspace：workspace 已是最新，四個 CLI 只卸 dev-flow、不重裝 workspace ----------
case " $(bash -c '. "$1/setup/lib.sh"; echo $PH_USER_PLUGINS' _ "$REPO_DIR") " in *" dev-flow "*) fail "PH_USER_PLUGINS 不該含 dev-flow" ;; esac
WS_VER="$(sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$REPO_DIR/plugins/workspace/.claude-plugin/plugin.json" | head -1)"
printf '[{"id": "dev-flow@plugharbor", "version": "0.9.0", "scope": "user"},\n {"id": "workspace@plugharbor", "version": "%s", "scope": "user"}]\n' "$WS_VER" > "$STUB_STATE/claude-list"
{
  echo 'Marketplace `plugharbor`'
  echo "dev-flow@plugharbor  installed, enabled  0.9.0    $REPO_DIR/plugins/dev-flow"
  echo "workspace@plugharbor  installed, enabled  $WS_VER    $REPO_DIR/plugins/workspace"
} > "$STUB_STATE/codex-list"
printf 'Installed plugins:\n- dev-flow (enabled, 0.9.0)\n- workspace (enabled, %s)\n' "$WS_VER" > "$STUB_STATE/agy-list"
H="$TMP/h16"; mkdir -p "$H/.pi/agent"
python3 -c 'import json,os,sys;h,r=sys.argv[1],sys.argv[2];d=os.path.join(h,".pi/agent");json.dump({"packages":[os.path.relpath(os.path.join(r,p),d).replace(os.sep,"/") for p in ("plugins/dev-flow","plugins/workspace")]},open(os.path.join(d,"settings.json"),"w"))' "$H" "$REPO_DIR"
OUT="$(PLUGINS="workspace" run "$H" --check)" || [ $? -eq 3 ] || fail "(22) --check exit 不是 0／3：$OUT"
for x in claude codex agy pi; do
  echo "$OUT" | grep -q "^RENAME: $x dev-flow → workspace" || fail "(22) --check 應報 RENAME: $x dev-flow → workspace：$OUT"
done
: > "$STUB_LOG"
OUT="$(PLUGINS="workspace" run "$H")" || fail "(22) 實跑 exit 非 0：$OUT"
grep -qx 'claude plugin uninstall dev-flow@plugharbor --scope user' "$STUB_LOG" || fail "(22) claude 應卸 dev-flow：$(cat "$STUB_LOG")"
grep -qx 'codex plugin remove dev-flow@plugharbor' "$STUB_LOG" || fail "(22) codex 應卸 dev-flow"
grep -qx 'agy plugin uninstall dev-flow' "$STUB_LOG" || fail "(22) agy 應卸 dev-flow"
if grep -q '^claude plugin \(install\|update\) workspace\|^codex plugin add workspace\|^agy plugin install .*/workspace$' "$STUB_LOG"; then fail "(22) workspace 已是最新不該重裝：$(cat "$STUB_LOG")"; fi
P="$H/.pi/agent/settings.json"
if grep -q 'plugins/dev-flow' "$P"; then fail "(22) pi 應移除 dev-flow：$(cat "$P")"; fi
[ "$(grep -c 'plugins/workspace' "$P")" = 1 ] || fail "(22) pi 的 workspace 應保留且不重複：$(cat "$P")"
rm "$STUB/pi"
export STUB_STATE="$TMP/state"

# ---------- 23) codex：marketplace 已移除舊名時 plugin list 不列它，改看 config.toml 的登記 ----------
printf '[{"id": "workspace@plugharbor", "version": "%s", "scope": "user"}]\n' "$WS_VER" > "$STUB_STATE/claude-list"
{
  echo 'Marketplace `plugharbor`'
  echo "workspace@plugharbor  installed, enabled  $WS_VER    $REPO_DIR/plugins/workspace"
} > "$STUB_STATE/codex-list"
printf 'Installed plugins:\n- workspace (enabled, %s)\n' "$WS_VER" > "$STUB_STATE/agy-list"
H="$TMP/h23"; mkdir -p "$H/.codex"
printf '[plugins."dev-flow@plugharbor"]\nenabled = true\n\n[plugins."workspace@plugharbor"]\nenabled = true\n' > "$H/.codex/config.toml"
OUT="$(PLUGINS="workspace" run "$H" --check)" || [ $? -eq 3 ] || fail "(23) --check exit 不是 0／3：$OUT"
echo "$OUT" | grep -q "^RENAME: codex dev-flow → workspace" || fail "(23) config.toml 登記的 dev-flow 應報 RENAME：$OUT"
: > "$STUB_LOG"
OUT="$(PLUGINS="workspace" run "$H")" || fail "(23) 實跑 exit 非 0：$OUT"
grep -qx 'codex plugin remove dev-flow@plugharbor' "$STUB_LOG" || fail "(23) codex 應卸 config.toml 登記的 dev-flow：$(cat "$STUB_LOG")"
if grep -q 'codex plugin remove workspace' "$STUB_LOG"; then fail "(23) workspace 不該被卸"; fi

# ---------- 24) PLUGHARBOR_PLUGINS 寫舊名：改用新名並提示，不 FAIL；新舊並列只裝一次 ----------
H="$TMP/h24"; mkdir -p "$H"
OUT="$(PLUGINS="dev-flow workspace" run "$H" --check || true)"
echo "$OUT" | grep -q "^NOTE: PLUGHARBOR_PLUGINS 的 dev-flow 已改名為 workspace" || fail "(24) 舊名應提示改用新名：$OUT"
if echo "$OUT" | grep -q "^FAIL"; then fail "(24) 舊名不該 FAIL：$OUT"; fi
[ "$(echo "$OUT" | grep -c "claude workspace")" -eq 1 ] || fail "(24) workspace 應只處理一次：$OUT"
rc=0; PLUGINS="workspace" run "$H" --check >/dev/null || rc=$?
[ "$rc" -eq 3 ] || fail "(24) --check 有差異應 exit 3，實際 ${rc}"

# ---------- 25) 只有 claude：codex、agy 印 SKIP 並照常完成，不呼叫它們 ----------
ONLYCLAUDE="$TMP/stub-onlyclaude"
bash "$REPO_DIR/setup/tests/lib/stub-cli.sh" "$ONLYCLAUDE" "$TOOLS" claude
H="$TMP/h25"; mkdir -p "$H"; : > "$STUB_LOG"
OUT="$(RUN_PATH="$ONLYCLAUDE:$TOOLS:/usr/bin:/bin" run "$H")" || fail "(25) 只有 claude 時 exit 非 0：$OUT"
echo "$OUT" | grep -q '^SKIP: codex（未安裝）' || fail "(25) 沒有 codex 應印 SKIP: codex：$OUT"
echo "$OUT" | grep -q '^SKIP: agy（未安裝）' || fail "(25) 沒有 agy 應印 SKIP: agy：$OUT"
if grep -qE '^(codex|agy) ' "$STUB_LOG"; then fail "(25) 沒裝的 CLI 不該被呼叫：$(cat "$STUB_LOG")"; fi

# ---------- 26) --check-projects：依 claude plugin list 的專案層紀錄逐一比對，只報不改 ----------
H="$TMP/h26"; mkdir -p "$H"; echo '[{"name": "plugharbor", "source": "git"}]' > "$STUB_STATE/claude-mkt"
P26="$TMP/p26"; mkdir -p "$P26"; git -C "$P26" init -q; P26="$(cd "$P26" && pwd -P)"
OK26="$TMP/ok26"; mkdir -p "$OK26"; git -C "$OK26" init -q; OK26="$(cd "$OK26" && pwd -P)"
HOME="$H" PATH="$BASE_PATH" bash "$REPO_DIR/setup/install-project.sh" "$OK26" ui-ux >/dev/null || fail "(26) 前置安裝失敗"
UIV="$(sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$REPO_DIR/plugins/ui-ux/.claude-plugin/plugin.json" | head -1)"
printf '[{"id": "lifecycle@plugharbor", "version": "0.0.1", "scope": "local", "projectPath": "%s"},
 {"id": "ui-ux@plugharbor", "version": "%s", "scope": "local", "projectPath": "%s"},
 {"id": "blog@plugharbor", "version": "0.1.0", "scope": "local", "projectPath": "%s/gone"},
 {"id": "toolkit@plugharbor", "version": "0.0.1", "scope": "user"},
 {"id": "other@elsewhere", "version": "1", "scope": "local", "projectPath": "%s"}]\n' \
  "$P26" "$UIV" "$OK26" "$TMP" "$P26" > "$STUB_STATE/claude-list"
hashes "$P26" > "$TMP/before26"; : > "$STUB_LOG"
rc=0; OUT="$(run "$H" --check-projects)" || rc=$?
[ "$rc" -eq 3 ] || fail "(26) 有落後應 exit 3，實際 ${rc}：$OUT"
echo "$OUT" | grep -q "^PROJECT: ${P26}（local：lifecycle）" || fail "(26) 應列出落後的專案：$OUT"
echo "$OUT" | grep -q "^  OUTDATED: claude lifecycle 0.0.1 → " || fail "(26) 應帶出 install-project 的差異：$OUT"
echo "$OUT" | grep -q "^STALE: $TMP/gone" || fail "(26) 不存在的專案目錄應報 STALE：$OUT"
echo "$OUT" | grep -q "^UP-TO-DATE: ${OK26}（" || fail "(26) 一致的專案應報 UP-TO-DATE：$OUT"
if echo "$OUT" | grep -q 'toolkit\|other'; then fail "(26) user 層與其他 marketplace 不該列入：$OUT"; fi
if grep -qE 'plugin (install|update|uninstall)' "$STUB_LOG"; then fail "(26) 只報不改，不該安裝：$(cat "$STUB_LOG")"; fi
hashes "$P26" > "$TMP/after26"
diff "$TMP/before26" "$TMP/after26" >/dev/null || fail "(26) --check-projects 改了專案檔案"
# 只剩一致的專案 → exit 0；沒有 claude → SKIP、exit 0
printf '[{"id": "ui-ux@plugharbor", "version": "%s", "scope": "local", "projectPath": "%s"}]\n' "$UIV" "$OK26" > "$STUB_STATE/claude-list"
run "$H" --check-projects >/dev/null || fail "(26) 全部一致應 exit 0"
OUT="$(RUN_PATH="$TOOLS:/usr/bin:/bin" run "$H" --check-projects)" || fail "(26) 沒有 claude 應 exit 0：$OUT"
echo "$OUT" | grep -q '^SKIP: claude' || fail "(26) 沒有 claude 應印 SKIP：$OUT"
rm "$STUB_STATE/claude-list"

echo "PASS: install.sh（26 組）"

