# install.sh／uninstall.sh 共用：檔案對照表、plugin 清單、各 CLI 版號解析。呼叫端先設 REPO_DIR。
# bash 3.2 與 Windows Git Bash 相容：不用 declare -A、mapfile、${var,,}；CLI 輸出一律先去掉 \r。

# <repo 相對路徑>|<~/.claude 下相對路徑>|<file|dir>
PH_ENTRIES='setup/home/CLAUDE.md|CLAUDE.md|file
setup/home/shared|shared|dir
setup/home/rules|rules|dir
setup/config/statusline.sh|statusline.sh|file
setup/herdr/hooks/herdr-parent-tag.py|hooks/herdr-parent-tag.py|file'

SIDEBAR_DIR="$REPO_DIR/setup/herdr/plugins/sidebar"

# 找真的跑得起來的 python（Windows 的 python3 可能是 Store 捷徑，command -v 找得到卻不能執行）
PY=""
for c in python python3; do
  if "$c" -c "" >/dev/null 2>&1; then PY="$c"; break; fi
done

ph_all_plugins() {
  local f
  for f in "$REPO_DIR"/plugins/*/.claude-plugin/plugin.json; do
    [ -f "$f" ] && basename "$(dirname "$(dirname "$f")")"
  done
}

# 要裝的 plugin：PLUGHARBOR_PLUGINS="toolkit research" 覆寫，沒設（或空字串）就全部
ph_plugins() {
  if [ -n "${PLUGHARBOR_PLUGINS:-}" ]; then
    printf '%s\n' $PLUGHARBOR_PLUGINS
  else
    ph_all_plugins
  fi
}

ph_version() {  # $1=plugin；讀 .claude-plugin/plugin.json 的 version
  sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' \
    "$REPO_DIR/plugins/$1/.claude-plugin/plugin.json" | tr -d '\r' | head -1
}

# 以下從 stdin 讀 CLI 輸出，印出 <plugin>@plugharbor 的已安裝版號；沒裝印空字串。

# codex plugin list：「toolkit@plugharbor  installed, enabled  0.1.0  <source>」
ph_codex_ver() {
  awk -v id="$1@plugharbor" '$1 == id {
    if ($0 ~ /not installed/) exit
    for (i = 2; i <= NF; i++) if ($i ~ /^[0-9]/) { print $i; exit }
  }'
}

# agy plugin list：「- toolkit (enabled, 0.1.0)」
ph_agy_ver() {
  awk -v n="$1" '$1 == "-" && $2 == n && /, [^,)]*\)/ {
    s = $0; sub(/.*, /, "", s); sub(/\).*/, "", s); print s; exit
  }'
}

# claude plugin list --json：只看 user scope
ph_claude_ver() {
  [ -n "$PY" ] || { cat >/dev/null; return 0; }
  "$PY" -c '
import json, sys
try:
    items = json.load(sys.stdin)
except Exception:
    items = []
for x in items if isinstance(items, list) else []:
    if x.get("id") == sys.argv[1] + "@plugharbor" and x.get("scope", "user") == "user":
        print(x.get("version", "")); break
' "$1"
}

# codex 有沒有設定 plugharbor marketplace（看 plugin list 的 section 標題）
ph_codex_has_marketplace() { grep -q '^Marketplace `plugharbor`'; }
ph_claude_has_marketplace() { grep -q '"name"[[:space:]]*:[[:space:]]*"plugharbor"'; }
