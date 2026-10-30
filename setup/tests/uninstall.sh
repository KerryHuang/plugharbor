#!/usr/bin/env bash
# uninstall.sh 驗證。HOME 導到暫存目錄、CLI 全換成 stub。
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
fail() { echo "FAIL: $1"; exit 1; }
STUB="$TMP/stub"; TOOLS="$TMP/tools"
bash "$REPO_DIR/setup/tests/lib/stub-cli.sh" "$STUB" "$TOOLS" claude codex agy herdr pi
export STUB_LOG="$TMP/cli.log" STUB_STATE="$TMP/state"
mkdir -p "$STUB_STATE"
H="$TMP/home"; C="$H/.claude"
mkdir -p "$H/.pi/agent"
printf '{"packages": ["npm:keep-me"]}\n' > "$H/.pi/agent/settings.json"
run() { HOME="$H" PATH="$STUB:$TOOLS:/usr/bin:/bin" PLUGHARBOR_PLUGINS="toolkit research" bash "$REPO_DIR/setup/$1"; }

run install.sh >/dev/null || fail "install exit 非 0"
[ -f "$H/.codex/AGENTS.md" ] || fail "前置：adapter 未產生 AGENTS.md"
echo "使用者自改" > "$C/rules/dotnet.md"
python3 - "$C/settings.json" <<'PY'
import json, sys
p = sys.argv[1]; d = json.load(open(p, encoding="utf-8")); d["foo"] = "bar"
json.dump(d, open(p, "w", encoding="utf-8"), indent=2)
PY
mkdir -p "$C/backups/plugharbor-20260101-000000"; echo "# 舊備份" > "$C/backups/plugharbor-20260101-000000/CLAUDE.md"
mkdir -p "$C/projects/demo/memory"
echo "自己的" > "$H/.codex/my-note.md"
# stub 回報已安裝，uninstall 才會呼叫移除
cat > "$STUB_STATE/claude-list" <<'J'
[{"id": "toolkit@plugharbor", "version": "0.1.0", "scope": "user"}, {"id": "other@x", "version": "1", "scope": "user"}]
J
echo '[{"name": "plugharbor", "source": "directory"}]' > "$STUB_STATE/claude-mkt"
printf 'PLUGIN  STATUS  VERSION  SOURCE\nresearch@plugharbor  installed, enabled  0.1.0  /x\ntoolkit@plugharbor  not installed    /x\n' > "$STUB_STATE/codex-list"
printf 'Installed plugins:\n- toolkit (enabled, 0.1.0)\n' > "$STUB_STATE/agy-list"
printf -- '- plugharbor.sidebar (Sidebar) enabled [local:/x]\n' > "$STUB_STATE/herdr-list"
: > "$STUB_LOG"
OUT="$(run uninstall.sh)" || fail "uninstall exit 非 0：$OUT"

[ ! -e "$C/CLAUDE.md" ]               || fail "未移除與 repo 一致的 CLAUDE.md"
[ ! -e "$C/rules/git-safety.md" ]     || fail "未移除與 repo 一致的 rule"
[ ! -e "$C/statusline.sh" ]           || fail "未移除 statusline.sh"
[ ! -e "$C/hooks/herdr-parent-tag.py" ] || fail "未移除 herdr-parent-tag.py"
grep -q "使用者自改" "$C/rules/dotnet.md" || fail "使用者改過的檔案不該被移除"
grep -q '"foo": "bar"' "$C/settings.json" || fail "settings.json 其他內容被動過"
if grep -q 'herdr-parent-tag' "$C/settings.json"; then fail "hook 檔已移除，settings 的 herdr-parent-tag 條目應一併移除"; fi
[ -f "$C/backups/plugharbor-20260101-000000/CLAUDE.md" ] || fail "既有備份不該被移除"
[ -d "$C/projects/demo/memory" ] || fail "repo 不管的目錄不該被移除"
[ ! -e "$H/.codex/AGENTS.md" ] || fail "adapter manifest 的檔案未移除"
[ ! -e "$H/.codex/plugharbor-manifest.json" ] || fail "adapter manifest 未移除"
[ -f "$H/.codex/my-note.md" ] || fail "manifest 以外的檔案不該被移除"
if grep -q 'plugharbor' "$H/.codex/hooks.json" 2>/dev/null; then fail "Codex hooks.json 的 plugharbor 條目未移除"; fi
grep -q 'npm:keep-me' "$H/.pi/agent/settings.json" || fail "pi 的其他 packages 被移除"
if grep -q 'plugins/toolkit' "$H/.pi/agent/settings.json"; then fail "pi packages 的 plugharbor 項目未移除"; fi
grep -qx 'claude plugin uninstall toolkit@plugharbor --scope user' "$STUB_LOG" || fail "claude 未移除 toolkit"
if grep -q 'claude plugin uninstall research@plugharbor' "$STUB_LOG"; then fail "claude 沒裝的不該移除"; fi
grep -qx 'claude plugin marketplace remove plugharbor' "$STUB_LOG" || fail "claude 未移除 marketplace"
grep -qx 'codex plugin remove research@plugharbor' "$STUB_LOG" || fail "codex 未移除 research"
if grep -q 'codex plugin remove toolkit@plugharbor' "$STUB_LOG"; then fail "codex not installed 的不該移除"; fi
grep -qx 'agy plugin uninstall toolkit' "$STUB_LOG" || fail "agy 未移除 toolkit"
grep -qx 'herdr plugin unlink plugharbor.sidebar' "$STUB_LOG" || fail "herdr 未 unlink plugharbor.sidebar"

echo "PASS: uninstall.sh"
