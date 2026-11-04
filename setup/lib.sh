# install.sh／uninstall.sh 共用：檔案對照表、plugin 清單、各 CLI 版號解析。呼叫端先設 REPO_DIR。
# bash 3.2 與 Windows Git Bash 相容：不用 declare -A、mapfile、${var,,}；CLI 輸出一律先去掉 \r。

# <repo 相對路徑>|<~/.claude 下相對路徑>|<file|dir>
PH_ENTRIES='setup/home/CLAUDE.md|CLAUDE.md|file
setup/home/shared|shared|dir
setup/home/rules|rules|dir
setup/config/statusline.sh|statusline.sh|file
setup/herdr/hooks/herdr-parent-tag.py|hooks/herdr-parent-tag.py|file'

SIDEBAR_DIR="$REPO_DIR/setup/herdr/plugins/sidebar"

# 找真的跑得起來的 python 3.6+（Windows 的 python3 可能是 Store 捷徑，command -v 找得到卻不能執行；python 可能是 2.x）
PY=""
for c in python3 python; do
  if "$c" -c 'import sys; sys.exit(sys.version_info < (3, 6))' >/dev/null 2>&1; then PY="$c"; break; fi
done

# 交給 python 的路徑：Git Bash 的 /c/Users/... 在 Windows 原生 python 會被當成 \c\Users，有 cygpath 就先轉成 C:/Users/...
ph_native_path() {
  if command -v cygpath >/dev/null 2>&1; then cygpath -m "$1"; else printf '%s\n' "$1"; fi
}

ph_all_plugins() {
  local f
  for f in "$REPO_DIR"/plugins/*/.claude-plugin/plugin.json; do
    [ -f "$f" ] && basename "$(dirname "$(dirname "$f")")"
  done
}

# 分層：工具類裝 user 層（每個專案都有），其餘是專案層，由 setup/install-project.sh 依專案安裝
PH_USER_PLUGINS="toolkit research browser-docs workspace"
# 改名對照：空白分隔「舊名:新名」。install.sh 從 user 層卸舊名；install-project.sh 對專案裡的舊名先卸再裝新名。
# 每批只開放已完成的改名（第②批：職責 plugin）。PLUGHARBOR_RENAMES 只給測試覆寫。
PH_RENAMES_DEFAULT="backend-dotnet:backend frontend-vue:frontend database-sqlserver:database desktop-avalonia:desktop kid-ui:ui-ux"
PH_RENAMES="${PLUGHARBOR_RENAMES-$PH_RENAMES_DEFAULT}"

ph_rename_pairs() {  # 每行印「舊名 新名」
  local x
  for x in $PH_RENAMES; do
    case "$x" in *:?*) printf '%s %s\n' "${x%%:*}" "${x#*:}" ;; esac
  done
}

ph_rename_new() {  # $1=舊名；印新名，沒有對照 return 1
  local x
  for x in $PH_RENAMES; do
    [ "${x%%:*}" != "$1" ] || { printf '%s\n' "${x#*:}"; return 0; }
  done
  return 1
}
# Claude Code 的 marketplace 來源（git，與 bootstrap.sh 同一變數）
PH_REPO_URL="${PLUGHARBOR_REPO:-https://github.com/KerryHuang/plugharbor.git}"

# 要裝到 user 層的 plugin：PLUGHARBOR_PLUGINS="toolkit research" 覆寫，沒設（或空字串）就是 PH_USER_PLUGINS
ph_plugins() {
  if [ -n "${PLUGHARBOR_PLUGINS:-}" ]; then
    ( set -f; printf '%s\n' $PLUGHARBOR_PLUGINS )  # 只按空白切字，不展開萬用字元
  else
    printf '%s\n' $PH_USER_PLUGINS
  fi
}

ph_is_user_plugin() { case " $PH_USER_PLUGINS " in *" $1 "*) return 0 ;; *) return 1 ;; esac; }

# 專案層 plugin（全部減去 user 層）
ph_project_plugins() {
  local p
  for p in $(ph_all_plugins); do ph_is_user_plugin "$p" || echo "$p"; done
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
# 不用 grep -q：它找到就提早結束，輸出很長時上游 printf 收到 SIGPIPE，pipefail 下整條 pipe 算失敗
ph_codex_has_marketplace() { grep '^Marketplace `plugharbor`' >/dev/null; }
ph_claude_has_marketplace() { grep '"name"[[:space:]]*:[[:space:]]*"plugharbor"' >/dev/null; }

# claude plugin marketplace list --json：plugharbor 是本機目錄來源（舊的就地載入）就成功
ph_claude_mkt_is_dir() {
  [ -n "$PY" ] || { cat >/dev/null; return 1; }
  "$PY" -c '
import json, sys
try:
    items = json.load(sys.stdin)
except Exception:
    items = []
sys.exit(0 if any(isinstance(x, dict) and x.get("name") == "plugharbor" and x.get("source") == "directory"
                  for x in (items if isinstance(items, list) else [])) else 1)
'
}
