#!/usr/bin/env bash
# 專案層 plugin → 指定專案：Claude Code 裝到 local（預設，不進 git）或 project（--shared，進 git 與團隊共用）scope；
# pi 寫專案的 .pi/settings.json（只限 local）；Codex、agy 沒有專案範圍，略過。user 層 plugin 由 install.sh 負責。
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
. "$REPO_DIR/setup/lib.sh"

usage() { echo "用法：install-project.sh [--shared] [--check] <專案根> <plugin…>"; exit 2; }
SHARED=0; CHECK=0; ROOT=""; WANT=""
for a in "$@"; do
  case "$a" in
    --shared) SHARED=1 ;;
    --check) CHECK=1 ;;
    -*) usage ;;
    *) if [ -z "$ROOT" ]; then ROOT="$a"; else WANT="$WANT $a"; fi ;;
  esac
done
[ -n "$ROOT" ] && [ -n "$WANT" ] || usage
[ -d "$ROOT" ] || { echo "FAIL: 專案根不存在：${ROOT}"; exit 2; }
ROOT="$(cd "$ROOT" && pwd -P)"
SCOPE=local; [ "$SHARED" -eq 0 ] || SCOPE=project

PLUGINS=""
for p in $WANT; do
  if new="$(ph_rename_new "$p")"; then echo "RENAME: ${p} → ${new}（改用新名）"; p="$new"; fi
  if [ ! -f "$REPO_DIR/plugins/$p/.claude-plugin/plugin.json" ]; then echo "FAIL: 找不到 plugin「${p}」"; exit 2; fi
  if ph_is_user_plugin "$p"; then echo "SKIP: ${p} 是 user 層，已由 install.sh 安裝"; else PLUGINS="$PLUGINS $p"; fi
done

DIFFS=0; FAILS=0
note_diff() { echo "$1"; DIFFS=$((DIFFS + 1)); }
run() { echo "RUN:  $*"; "$@" || { echo "FAIL: $*"; FAILS=$((FAILS + 1)); }; }

# 這次要裝的新名所對應的舊名（改名對照）；每行「舊名 新名」
# （寫成函式：bash 3.2 解析 $( ) 裡的 case 會出錯）
renamed_pairs() {
  local o n
  while read -r o n; do
    [ -n "$o" ] || continue
    case " $PLUGINS " in *" $n "*) echo "$o $n" ;; esac
  done <<< "$(ph_rename_pairs)"
}
RENAMED="$(renamed_pairs)"

[ "$CHECK" -eq 1 ] && echo "比對專案層 plugin（${SCOPE}）↔ ${ROOT}（只報不改）" || echo "安裝專案層 plugin（${SCOPE}）→ ${ROOT}"

# claude plugin list --json：印出 <plugin>@plugharbor 在本專案、指定 scope 的版號
claude_ver() {  # $1=plugin
  [ -n "$PY" ] || { cat >/dev/null; return 0; }
  "$PY" -c '
import json, os, sys
try:
    items = json.load(sys.stdin)
except Exception:
    items = []
pid, scope, root = sys.argv[1] + "@plugharbor", sys.argv[2], os.path.realpath(sys.argv[3])
for x in items if isinstance(items, list) else []:
    pp = x.get("projectPath")
    if x.get("id") == pid and x.get("scope") == scope and pp and os.path.realpath(pp) == root:
        print(x.get("version", "")); break
' "$1" "$SCOPE" "$ROOT"
}

# 專案 .claude/settings.json 已登記 plugharbor marketplace
project_has_mkt() {
  [ -f "$ROOT/.claude/settings.json" ] && [ -n "$PY" ] || return 1
  "$PY" -c '
import json, sys
try:
    d = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception:
    sys.exit(1)
sys.exit(0 if "plugharbor" in (d.get("extraKnownMarketplaces") or {}) else 1)
' "$ROOT/.claude/settings.json"
}

# ---------- Claude Code：在專案根執行，scope 才會落在這個專案 ----------
if [ -z "$PLUGINS" ]; then
  :
elif command -v claude >/dev/null 2>&1; then
  cd "$ROOT"
  if [ "$SHARED" -eq 1 ]; then
    if ! project_has_mkt; then
      if [ "$CHECK" -eq 1 ]; then note_diff "MISSING: claude marketplace plugharbor（專案 scope）"
      else run claude plugin marketplace add "$PH_REPO_URL" --scope project; fi
    fi
  else
    out="$(claude plugin marketplace list --json 2>/dev/null | tr -d '\r')" || out=""
    if ! printf '%s\n' "$out" | ph_claude_has_marketplace; then
      if [ "$CHECK" -eq 1 ]; then note_diff "MISSING: claude marketplace plugharbor（user 層，先跑 setup/install.sh）"
      else run claude plugin marketplace add "$PH_REPO_URL"; fi
    fi
  fi
  out="$(claude plugin list --json 2>/dev/null | tr -d '\r')" || out=""
  while read -r o n; do
    [ -n "$o" ] && [ -n "$(printf '%s\n' "$out" | claude_ver "$o")" ] || continue
    if [ "$CHECK" -eq 1 ]; then note_diff "RENAME: claude ${o} → ${n}（舊名，install-project 會卸載後裝新名）"
    else run claude plugin uninstall "$o@plugharbor" --scope "$SCOPE"; fi
  done <<< "$RENAMED"
  REFRESHED=0
  for p in $PLUGINS; do
    cur="$(printf '%s\n' "$out" | claude_ver "$p")"; want="$(ph_version "$p")"
    if [ -n "$cur" ] && [ "$cur" = "$want" ]; then
      echo "UP-TO-DATE: claude $p $want"
    elif [ "$CHECK" -eq 1 ]; then
      if [ -n "$cur" ]; then note_diff "OUTDATED: claude $p $cur → $want"; else note_diff "MISSING: claude $p"; fi
    elif [ -n "$cur" ]; then
      if [ "$REFRESHED" -eq 0 ]; then
        REFRESHED=1; echo "RUN:  claude plugin marketplace update plugharbor"
        claude plugin marketplace update plugharbor || echo "WARN: marketplace update 失敗，照舊更新"
      fi
      run claude plugin update "$p@plugharbor" --scope "$SCOPE"
    else
      run claude plugin install "$p@plugharbor" --scope "$SCOPE"
    fi
  done
else
  echo "SKIP: claude（未安裝）"
fi

# ---------- pi：專案 .pi/settings.json 的 packages（絕對路徑，只限 local） ----------
PI_PKGS=""; PI_OLD=""
for p in $PLUGINS; do
  grep -q '"pi"' "$REPO_DIR/plugins/$p/package.json" 2>/dev/null && PI_PKGS="$PI_PKGS $(ph_native_path "$REPO_DIR/plugins/$p")"
done
while read -r o n; do
  [ -z "$o" ] || PI_OLD="$PI_OLD $(ph_native_path "$REPO_DIR/plugins/$o")=$n"
done <<< "$RENAMED"
if [ -z "$PI_PKGS" ]; then
  :
elif ! command -v pi >/dev/null 2>&1; then
  echo "SKIP: pi（未安裝）"
elif [ "$SHARED" -eq 1 ]; then
  echo "SKIP: pi 不支援 --shared（packages 是本機絕對路徑，進 git 別人用不了）"
elif git -C "$ROOT" ls-files --error-unmatch .pi/settings.json >/dev/null 2>&1; then
  echo "WARN: pi 的 .pi/settings.json 已進版控，不寫入本機路徑；請手動在 pi 安裝，或把該檔移出版控"
elif [ -z "$PY" ]; then
  echo "FAIL: pi 設定需要 python 3"; FAILS=$((FAILS + 1))
else
  PYTHONUTF8=1 "$PY" -c '
import json, os, sys
path, check, pkgs = sys.argv[1], sys.argv[2] == "1", sys.argv[3].split()
renamed = dict(r.split("=", 1) for r in sys.argv[4].split())  # 舊路徑=新名
try:
    d = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}
except Exception as e:
    print(f"FAIL: 讀不了 {path}：{e}"); sys.exit(1)
cur = d.setdefault("packages", [])
old = [p for p in cur if p in renamed]
for p in old:
    print(f"RENAME: pi {os.path.basename(p)} → {renamed[p]}" if check else f"OK:   pi 移除舊名 {os.path.basename(p)}（改名為 {renamed[p]}）")
if old and not check:
    cur[:] = [p for p in cur if p not in renamed]
add = [p for p in pkgs if p not in cur]
for p in pkgs:
    name = os.path.basename(p)
    if p in cur: print(f"UP-TO-DATE: pi {name}")
    elif check: print(f"MISSING: pi {name}")
if (add or old) and not check:
    cur.extend(add)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2); f.write("\n")
    for p in add: print(f"OK:   pi {os.path.basename(p)}")
sys.exit(2 if (add or old) and check else 0)
' "$(ph_native_path "$ROOT/.pi/settings.json")" "$CHECK" "$PI_PKGS" "$PI_OLD" && rc=0 || rc=$?
  case "$rc" in 0) ;; 2) DIFFS=$((DIFFS + 1)) ;; *) FAILS=$((FAILS + 1)) ;; esac
  if [ "$CHECK" -eq 0 ] && [ "$rc" -eq 0 ]; then
    ex="$(git -C "$ROOT" rev-parse --git-path info/exclude 2>/dev/null)" || ex=""
    if [ -n "$ex" ]; then
      case "$ex" in /*) ;; *) ex="$ROOT/$ex" ;; esac
      mkdir -p "$(dirname "$ex")"; touch "$ex"
      grep -qxF '.pi/settings.json' "$ex" || echo '.pi/settings.json' >> "$ex"
    fi
    echo "NOTE: 第一次在 pi 開這個專案時要信任專案，packages 才會載入"
  fi
fi

if [ -n "$PLUGINS" ]; then
  echo "SKIP: codex 沒有專案範圍（專案層 plugin 不安裝）"
  echo "SKIP: agy 沒有專案範圍（專案層 plugin 不安裝）"
fi

if [ "$FAILS" -gt 0 ]; then echo "完成，但有 ${FAILS} 項失敗"; exit 1; fi
if [ "$CHECK" -eq 1 ]; then echo "差異 ${DIFFS} 項"; else echo "完成"; fi
