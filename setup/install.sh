#!/usr/bin/env bash
# plugharbor → 本機：user 層檔案、settings 合併、舊 claude-home hook 清理、四個 CLI 的 plugin 註冊、adapter 副本。
# claude-home 還裝著時也能跑：同名檔內容不同就 SKIP、重複的 skill／agent 只報 DUP，不動使用者的東西。
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
. "$REPO_DIR/setup/lib.sh"
TARGET="$HOME/.claude"

FORCE=0; CHECK=0; YES=0
for a in "$@"; do
  case "$a" in
    --force) FORCE=1 ;;
    --check) CHECK=1 ;;
    --yes) YES=1 ;;
    *) echo "用法：install.sh [--check] [--force] [--yes]"; exit 2 ;;
  esac
done
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP="$TARGET/backups/plugharbor-$STAMP"
DIFFS=0; FAILS=0
PLUGINS="$(ph_plugins)"
while IFS= read -r p; do
  [ -f "$REPO_DIR/plugins/$p/.claude-plugin/plugin.json" ] || { echo "FAIL: 找不到 plugin「${p}」（PLUGHARBOR_PLUGINS）"; exit 2; }
done <<< "$PLUGINS"

note_diff() { echo "$1"; DIFFS=$((DIFFS + 1)); }
LAST_OK=0
run() {  # 執行 CLI 指令；失敗只記下（LAST_OK=0），繼續做其他步驟
  echo "RUN:  $*"
  if "$@"; then LAST_OK=1; else LAST_OK=0; echo "FAIL: $*"; FAILS=$((FAILS + 1)); fi
}
backup_once() {  # $1=原檔 $2=備份目錄下的相對路徑；同一次執行只留第一份
  [ -f "$1" ] && [ ! -e "$BACKUP/$2" ] || return 0
  mkdir -p "$(dirname "$BACKUP/$2")"; cp "$1" "$BACKUP/$2"
}

install_file() {  # $1=來源絕對路徑  $2=目標相對路徑
  local src="$1" rel="$2" dst="$TARGET/$2"
  if [ "$CHECK" -eq 1 ]; then
    if [ ! -e "$dst" ]; then note_diff "MISSING: ${rel}（install.sh 會裝上）"
    elif ! cmp -s "$src" "$dst"; then note_diff "DIFF:    $rel"
    fi
    return 0
  fi
  if [ -e "$dst" ] && ! cmp -s "$src" "$dst"; then
    if [ "$FORCE" -eq 1 ]; then
      mkdir -p "$BACKUP/$(dirname "$rel")"; cp "$dst" "$BACKUP/$rel"
    else
      echo "SKIP: $rel 已存在且內容不同（--force 覆蓋會先備份）"; return 0
    fi
  elif [ -e "$dst" ]; then
    return 0
  fi
  mkdir -p "$(dirname "$dst")"; cp "$src" "$dst"; echo "OK:   $rel"
}

install_dir() {   # $1=來源目錄  $2=目標相對目錄
  local src="$1" rel="$2" f
  [ -d "$src" ] || return 0
  while IFS= read -r f; do
    install_file "$src/$f" "$rel/$f"
  done < <(cd "$src" && find . -type f ! -name '*.pyc' ! -path './__pycache__/*' | sed 's|^\./||' | LC_ALL=C sort)
}

[ "$CHECK" -eq 1 ] && echo "比對 plugharbor ↔ 本機（只報不改）" || echo "安裝 plugharbor → $HOME"

# ---------- 1) user 層檔案 ----------
while IFS='|' read -r from to kind; do
  [ -n "$from" ] || continue
  if [ "$kind" = "dir" ]; then install_dir "$REPO_DIR/$from" "$to"; else install_file "$REPO_DIR/$from" "$to"; fi
done <<< "$PH_ENTRIES"

# ---------- 2) settings 合併；3) 的舊 hook 清理等 claude 裝好 toolkit 之後才做 ----------
# 模式：check（只報）、merge（範本合併）、clean（備份後移除舊 hook）、stale（只印舊 hook）
SETTINGS_PY="$(cat <<'PYEOF'
import json, os, re, shutil, sys
MANAGED = ("statusLine",)   # 以範本為準（--force 才換）
TEMPLATE_HOOKS = "hooks"     # 範本的 hook 依腳本檔名認同一筆，缺就補
HOME = os.path.expanduser("~")
# 只認 HOME 底下 .claude/hooks/ 的舊 claude-home 腳本；專案層（$CLAUDE_PROJECT_DIR/.claude/hooks）不算
HOME_PREFIX = r"(?:~|\$HOME|\$\{HOME\}|" + re.escape(HOME) + r"|" + re.escape(HOME.replace("\\", "/")) + r")"
LEGACY = re.compile(HOME_PREFIX + r"[/\\]+\.claude[/\\]+hooks[/\\]+(?:(?:guard|agent-model-guard|ask-question-guard|"
                    r"auto-session-title|feedback-capture|feedback-reminder|context-size-reminder)\.py|notification\.sh)(?![\w.])")

def key(cmd):
    m = re.findall(r"[\w.-]+\.(?:py|sh|ps1)", cmd or "")
    return m[-1] if m else cmd

def owned(group, keys):
    return any(key(h.get("command")) in keys for h in group.get("hooks", []))

mode, tpl_path, path, force, backup = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4] == "1", sys.argv[5]
tpl = json.load(open(tpl_path, encoding="utf-8"))
try:
    cur = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}
except ValueError as e:
    print(f"FAIL: settings.json 不是合法 JSON，未處理：{e}"); sys.exit(1)

def write(obj, msg):
    body = json.dumps(obj, ensure_ascii=False, indent=2) + "\n"
    old = open(path, encoding="utf-8").read() if os.path.exists(path) else None
    if body != old:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        open(path, "w", encoding="utf-8", newline="\n").write(body)
        print(msg)

# 舊 claude-home hook：同組裡本機自加的保留，只拿掉舊條目；被清空的組與事件一併移除
stale = []
hooks = cur.get("hooks") if isinstance(cur.get("hooks"), dict) else {}
for event in list(hooks):
    groups = hooks[event] if isinstance(hooks[event], list) else []
    new, touched = [], False
    for g in groups:
        hs = g.get("hooks", []) if isinstance(g, dict) else []
        bad = [h for h in hs if isinstance(h, dict) and LEGACY.search(h.get("command") or "")]
        stale += [f"hooks.{event} {key(h.get('command'))}" for h in bad]
        touched = touched or bool(bad)
        if not bad:
            new.append(g)
        elif len(bad) < len(hs):
            new.append(dict(g, hooks=[h for h in hs if h not in bad]))
    if touched:
        if new:
            hooks[event] = new
        else:
            del hooks[event]

if mode in ("check", "stale"):
    why = "install 裝好 claude 的 toolkit 後會備份並移除" if mode == "check" else "未移除：這次沒有裝好 claude 的 toolkit plugin，移除會失去 guard"
    for s in stale:
        print(f"STALE:   settings.json {s}（舊 claude-home hook；{why}）")
    if mode == "stale":
        sys.exit(0)
    def walk(t, c, p0):
        for k, val in t.items():
            if not p0 and (k in MANAGED or k == TEMPLATE_HOOKS):
                continue
            p = f"{p0}.{k}" if p0 else k
            if not isinstance(c, dict) or k not in c:
                print(f"MISSING: settings.json {p}")
            elif isinstance(val, dict):
                walk(val, c[k], p)
            elif isinstance(val, list) and isinstance(c[k], list):
                for x in val:
                    if x not in c[k]:
                        print(f"MISSING: settings.json {p}[] {json.dumps(x, ensure_ascii=False)[:120]}")
    walk(tpl, cur, "")
    if "statusLine" in tpl:
        if "statusLine" not in cur:
            print("MISSING: settings.json statusLine")
        elif cur["statusLine"] != tpl["statusLine"]:
            print("DIFF:    settings.json statusLine（範本管，--force 以範本為準）")
    for event, groups in tpl.get(TEMPLATE_HOOKS, {}).items():
        curg = hooks.get(event, [])
        for tg in groups:
            keys = {key(h["command"]) for h in tg["hooks"]}
            mine = [g for g in curg if owned(g, keys)]
            label = "/".join(sorted(keys))
            if not mine:
                print(f"MISSING: settings.json hooks.{event} {label}")
            elif mine != [tg]:
                print(f"DIFF:    settings.json hooks.{event} {label}（與範本不同或重複，--force 以範本為準）")
    sys.exit(0)

if mode == "clean":
    if stale:
        os.makedirs(backup, exist_ok=True)
        shutil.copy2(path, os.path.join(backup, "settings.json"))
        write(cur, "CLEAN: settings.json 移除舊 claude-home hook：" + "、".join(stale) + f"（原檔備份在 {backup}/settings.json）")
    sys.exit(0)

# mode == "merge"：用未清理的原始內容合併，舊 hook 留給 clean 處理
cur = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}
def merge(template, current):
    for k, val in template.items():
        if k not in current:
            current[k] = val
        elif isinstance(val, dict) and isinstance(current[k], dict):
            merge(val, current[k])
        elif isinstance(val, list) and isinstance(current[k], list):
            current[k] = current[k] + [x for x in val if x not in current[k]]
    return current

if "statusLine" in tpl and ("statusLine" not in cur or force):
    cur["statusLine"] = tpl["statusLine"]
for event, groups in tpl.get(TEMPLATE_HOOKS, {}).items():
    curg = cur.setdefault("hooks", {}).setdefault(event, [])
    for tg in groups:
        keys = {key(h["command"]) for h in tg["hooks"]}
        mine = [g for g in curg if owned(g, keys)]
        if not mine:
            curg.append(tg)
        elif force and mine != [tg]:
            for g in mine:
                g["hooks"] = [h for h in g.get("hooks", []) if key(h.get("command")) not in keys]
            curg[:] = [g for g in curg if g.get("hooks")] + [tg]

merged = merge({k: v for k, v in tpl.items() if k not in MANAGED and k != TEMPLATE_HOOKS}, cur)
write(merged, "OK:   settings.json（合併；statusLine／herdr-parent-tag hook " + ("以範本為準）" if force else "只補缺，--force 才以範本為準）"))
PYEOF
)"
settings_py() {  # $1=模式；輸出照印，check 模式計入差異數
  local out rc
  [ -n "$PY" ] || return 0
  set +e
  out="$(PYTHONUTF8=1 "$PY" -c "$SETTINGS_PY" "$1" "$REPO_DIR/setup/config/claude-settings.template.json" "$TARGET/settings.json" "$FORCE" "$BACKUP")"
  rc=$?
  set -e
  if [ -n "$out" ]; then
    echo "$out"
    if [ "$1" = check ]; then DIFFS=$((DIFFS + $(printf '%s\n' "$out" | wc -l))); fi
  fi
  [ "$rc" -eq 0 ] || FAILS=$((FAILS + 1))
}
if [ -z "$PY" ]; then
  echo "WARN: 找不到能執行的 python 3，settings.json 未合併、舊 hook 未清理"
elif [ "$CHECK" -eq 1 ]; then
  settings_py check
else
  settings_py merge
fi

# ---------- 4) 跟 plugharbor plugin 同名的 user 層 skill／agent ----------
dup() {  # $1=~/.claude 下相對路徑  $2=plugin
  if [ "$YES" -eq 1 ] && [ "$CHECK" -eq 0 ]; then
    mkdir -p "$BACKUP/$(dirname "$1")"
    mv "$TARGET/$1" "$BACKUP/$1"
    echo "MOVED: $1 → $BACKUP/$1（已由 plugin $2 提供）"
  else
    echo "DUP: $1（plugin $2 有同名的；--yes 會搬進 $TARGET/backups/）"
    [ "$CHECK" -eq 0 ] || DIFFS=$((DIFFS + 1))
  fi
}
for p in $PLUGINS; do
  for d in "$REPO_DIR/plugins/$p/skills"/*/; do
    [ -d "$d" ] || continue
    n="$(basename "$d")"
    if [ -e "$TARGET/skills/$n" ] || [ -L "$TARGET/skills/$n" ]; then dup "skills/$n" "$p"; fi
  done
  for f in "$REPO_DIR/plugins/$p/agents"/*.md; do
    [ -f "$f" ] || continue
    n="$(basename "$f")"
    if [ -e "$TARGET/agents/$n" ] || [ -L "$TARGET/agents/$n" ]; then dup "agents/$n" "$p"; fi
  done
done

# ---------- 5、6) 各 CLI 註冊 plugin；版號相同就不重裝 ----------
REFRESHED=" "
refresh_marketplace() {  # 版號不同、重裝前先更新 marketplace 目錄（每個 CLI 一次）；失敗只警告
  case "$REFRESHED" in *" $1 "*) return 0 ;; esac
  REFRESHED="$REFRESHED$1 "
  case "$1" in
    claude) set -- claude plugin marketplace update plugharbor ;;
    codex) set -- codex plugin marketplace upgrade plugharbor ;;
    *) return 0 ;;
  esac
  echo "RUN:  $*"
  "$@" || echo "WARN: $* 失敗，照舊重裝"
}
# $1=CLI  $2=plugin  $3=已安裝版號  其餘＝安裝指令；LAST_OK=1 表示裝好或已是最新
sync_plugin() {
  local cli="$1" p="$2" cur="$3" want
  shift 3
  want="$(ph_version "$p")"
  LAST_OK=0
  if [ -n "$cur" ] && [ "$cur" = "$want" ]; then
    echo "UP-TO-DATE: $cli $p $want"; LAST_OK=1
  elif [ "$CHECK" -eq 1 ]; then
    if [ -n "$cur" ]; then note_diff "OUTDATED: $cli $p $cur → $want"; else note_diff "MISSING: $cli $p"; fi
  else
    [ -z "$cur" ] || refresh_marketplace "$cli"
    run "$@"
  fi
}

TOOLKIT_OK=0
if command -v claude >/dev/null 2>&1; then
  out="$(claude plugin marketplace list --json 2>/dev/null | tr -d '\r')" || out=""
  if ! printf '%s\n' "$out" | ph_claude_has_marketplace; then
    if [ "$CHECK" -eq 1 ]; then note_diff "MISSING: claude marketplace plugharbor"; else run claude plugin marketplace add "$REPO_DIR"; fi
  fi
  out="$(claude plugin list --json 2>/dev/null | tr -d '\r')" || out=""
  for p in $PLUGINS; do
    cur="$(printf '%s\n' "$out" | ph_claude_ver "$p")"
    if [ -n "$cur" ]; then
      sync_plugin claude "$p" "$cur" claude plugin update "$p@plugharbor" --scope user
    else
      sync_plugin claude "$p" "" claude plugin install "$p@plugharbor" --scope user
    fi
    [ "$p" != toolkit ] || TOOLKIT_OK="$LAST_OK"
  done
else
  echo "SKIP: claude（未安裝）"
fi

# 3) 舊 claude-home hook（guard 等）只在 claude 的 toolkit 裝好後移除；否則只提示，免得 guard 消失卻沒有替代
if [ -n "$PY" ] && [ "$CHECK" -eq 0 ]; then
  if [ "$TOOLKIT_OK" -eq 1 ]; then settings_py clean; else settings_py stale; fi
fi

if command -v codex >/dev/null 2>&1; then
  out="$(codex plugin list 2>/dev/null | tr -d '\r')" || out=""
  if ! printf '%s\n' "$out" | ph_codex_has_marketplace; then
    if [ "$CHECK" -eq 1 ]; then note_diff "MISSING: codex marketplace plugharbor"; else run codex plugin marketplace add "$REPO_DIR"; fi
  fi
  for p in $PLUGINS; do
    sync_plugin codex "$p" "$(printf '%s\n' "$out" | ph_codex_ver "$p")" codex plugin add "$p@plugharbor"
  done
else
  echo "SKIP: codex（未安裝）"
fi

if command -v agy >/dev/null 2>&1; then
  out="$(agy plugin list 2>/dev/null | tr -d '\r')" || out=""
  for p in $PLUGINS; do
    sync_plugin agy "$p" "$(printf '%s\n' "$out" | ph_agy_ver "$p")" agy plugin install "$REPO_DIR/plugins/$p"
  done
else
  echo "SKIP: agy（未安裝）"
fi

if ! command -v pi >/dev/null 2>&1; then
  echo "SKIP: pi（未安裝）"
elif [ -z "$PY" ]; then
  echo "WARN: 找不到能執行的 python，pi 的 packages 未更新"
else
  PI_DIRS=""
  for p in $PLUGINS; do
    if grep -q '"pi"' "$REPO_DIR/plugins/$p/package.json" 2>/dev/null; then
      PI_DIRS="$PI_DIRS
$REPO_DIR/plugins/$p"
    else
      echo "SKIP: pi ${p}（沒有 pi package 設定）"
    fi
  done
  set +e
  PI_OUT="$(printf '%s\n' "$PI_DIRS" | PYTHONUTF8=1 "$PY" -c '
import json, os, shutil, sys
start, check, backup = sys.argv[1], sys.argv[2] == "1", sys.argv[3]
path = os.path.join(start, "settings.json")
try:
    cur = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}
except ValueError as e:
    print(f"FAIL: {path} 不是合法 JSON，未更新：{e}"); sys.exit(1)
pkgs = cur.get("packages", [])
def norm(x): return os.path.normcase(os.path.normpath(x))
have = {norm(os.path.join(start, x)) for x in pkgs if isinstance(x, str) and not x.startswith(("npm:", "git:", "http"))}
added = []
for d in (l.strip() for l in sys.stdin):
    if not d or norm(d) in have:
        continue
    try:
        rel = os.path.relpath(d, start)
    except ValueError:   # Windows 跨磁碟機時沒有相對路徑
        rel = d
    added.append(rel.replace(os.sep, "/"))
for a in added:
    print(("MISSING: pi package " if check else "OK:   pi package ") + a)
if added and not check:
    cur["packages"] = pkgs + added
    if os.path.exists(path):
        os.makedirs(os.path.join(backup, "pi"), exist_ok=True)
        shutil.copy2(path, os.path.join(backup, "pi", "settings.json"))
    os.makedirs(start, exist_ok=True)
    open(path, "w", encoding="utf-8", newline="\n").write(json.dumps(cur, ensure_ascii=False, indent=2) + "\n")
' "$HOME/.pi/agent" "$CHECK" "$BACKUP")"
  rc=$?
  set -e
  if [ -n "$PI_OUT" ]; then
    echo "$PI_OUT"
    if [ "$CHECK" -eq 1 ]; then DIFFS=$((DIFFS + $(printf '%s\n' "$PI_OUT" | wc -l))); fi
  fi
  [ "$rc" -eq 0 ] || FAILS=$((FAILS + 1))
fi

# ---------- herdr：換掉舊的 kerry.sidebar；config.toml 各機器不同，只提示不覆蓋 ----------
if command -v herdr >/dev/null 2>&1; then
  out="$(herdr plugin list 2>/dev/null | tr -d '\r')" || out=""
  # kerry.sidebar 是 plugharbor 之前（claude-home 時代）的舊 herdr plugin id，這裡遷移成 plugharbor.sidebar
  if printf '%s\n' "$out" | grep '^- kerry\.sidebar ' >/dev/null; then
    if [ "$CHECK" -eq 1 ]; then note_diff "STALE: herdr kerry.sidebar（install 會 unlink，改 link plugharbor.sidebar）"; else run herdr plugin unlink kerry.sidebar; fi
  fi
  if printf '%s\n' "$out" | grep '^- plugharbor\.sidebar ' >/dev/null; then
    echo "UP-TO-DATE: herdr plugharbor.sidebar"
  elif [ "$CHECK" -eq 1 ]; then
    note_diff "MISSING: herdr plugharbor.sidebar"
  else
    run herdr plugin link "$SIDEBAR_DIR"
  fi
  HCONF="$HOME/.config/herdr/config.toml"
  if ! cmp -s "$REPO_DIR/setup/herdr/config.toml" "$HCONF"; then
    echo "NOTE: herdr 的 config.toml 不自動覆蓋（new_cwd 等各機器不同），需要的話對照 $REPO_DIR/setup/herdr/config.toml 手動改 $HCONF"
  fi
else
  echo "SKIP: herdr（未安裝）"
fi

# ---------- 7) Codex／pi／agy 的 user 層規則副本 ----------
if [ "$CHECK" -eq 1 ]; then
  :
elif command -v node >/dev/null 2>&1; then
  # adapter 會合併 ~/.codex/hooks.json（含使用者自己的 hook）；內容有變才把原檔留進備份
  CODEX_HOOKS="$HOME/.codex/hooks.json"; CODEX_HOOKS_ORIG=""
  if [ -f "$CODEX_HOOKS" ]; then CODEX_HOOKS_ORIG="$(mktemp)"; cp "$CODEX_HOOKS" "$CODEX_HOOKS_ORIG"; fi
  if node "$REPO_DIR/setup/adapters/sync-user.mjs" --install --quiet --repo "$REPO_DIR"; then
    echo "OK:   adapter（Codex／pi／agy user 層副本）"
  else
    echo "FAIL: adapter（setup/adapters/sync-user.mjs）"; FAILS=$((FAILS + 1))
  fi
  if [ -n "$CODEX_HOOKS_ORIG" ]; then
    cmp -s "$CODEX_HOOKS_ORIG" "$CODEX_HOOKS" || backup_once "$CODEX_HOOKS_ORIG" codex/hooks.json
    rm -f "$CODEX_HOOKS_ORIG"
  fi
else
  echo "SKIP: node（未安裝；Codex／pi／agy 的 user 層規則副本未產生，裝好 node 後重跑）"
fi

echo "---"
if [ "$CHECK" -eq 1 ]; then
  [ "$DIFFS" -eq 0 ] && echo "一致：repo 與本機無差異" || echo "$DIFFS 項有差異；跑 install.sh 補上（內容不同的檔案要 --force，會先備份）"
  exit 0
fi
[ -d "$BACKUP" ] && echo "備份：$BACKUP"
if [ "$FAILS" -gt 0 ]; then echo "完成，但有 $FAILS 個步驟失敗（見上方 FAIL）"; exit 1; fi
echo "完成。"
