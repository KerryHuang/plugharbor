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
{"model":"my-model","permissions":{"deny":["Custom(x)"]},
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
[ "$(grep -n 'codex plugin marketplace upgrade plugharbor' "$STUB_LOG" | cut -d: -f1)" -lt "$(grep -n 'codex plugin add research' "$STUB_LOG" | cut -d: -f1)" ] \
  || fail "codex 重裝前應先 marketplace upgrade"
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

# ---------- 8) 預設裝全部 plugin ----------
H="$TMP/h4"; mkdir -p "$H"; : > "$STUB_LOG"
PLUGINS="" run "$H" >/dev/null || fail "預設 plugin 清單 install exit 非 0"
N_ALL="$(ls -d "$REPO_DIR"/plugins/*/.claude-plugin | wc -l | tr -d ' ')"
[ "$(grep -c '^claude plugin install ' "$STUB_LOG")" = "$N_ALL" ] || fail "預設應裝全部 $N_ALL 個 plugin"

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
echo '[{"name": "plugharbor", "source": "directory"}]' > "$STUB_STATE/claude-mkt"
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

echo "PASS: install.sh（14 組）"
