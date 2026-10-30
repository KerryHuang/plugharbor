#!/usr/bin/env bash
# 只移除 plugharbor 放進去的東西：install.sh 的檔案對照表（內容與 repo 一致才刪）、adapter manifest 列的副本、
# 各 CLI 已註冊的 plugharbor plugin。使用者改過的檔案、settings.json 的其他內容、備份都不動。
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
. "$REPO_DIR/setup/lib.sh"
TARGET="$HOME/.claude"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP="$TARGET/backups/plugharbor-uninstall-$STAMP"
PLUGINS="$(ph_all_plugins)"
FAILS=0
run() {
  echo "RUN:  $*"
  if "$@"; then :; else echo "FAIL: $*"; FAILS=$((FAILS + 1)); fi
}

remove_if_same() {  # $1=repo 來源  $2=目標相對路徑
  local src="$1" dst="$TARGET/$2"
  if [ -f "$dst" ] && cmp -s "$src" "$dst"; then
    rm "$dst"; echo "移除: $2"
  elif [ -f "$dst" ]; then
    echo "保留: $2（內容與 repo 不同，可能被使用者修改）"
  fi
}

remove_dir_items() {  # $1=repo 來源目錄  $2=目標相對目錄
  local src="$1" rel="$2" f
  [ -d "$src" ] || return 0
  while IFS= read -r f; do
    remove_if_same "$src/$f" "$rel/$f"
  done < <(cd "$src" && find . -type f ! -name '*.pyc' ! -path './__pycache__/*' | sed 's|^\./||')
  while IFS= read -r f; do
    rmdir "$TARGET/$rel/$f" 2>/dev/null || true
  done < <(cd "$src" && find . -mindepth 1 -depth -type d | sed 's|^\./||')
  rmdir "$TARGET/$rel" 2>/dev/null || true
}

echo "移除 plugharbor ← ${HOME}（備份與使用者改過的檔案不動）"

# ---------- 各 CLI 的 plugin ----------
if command -v claude >/dev/null 2>&1; then
  out="$(claude plugin list --json 2>/dev/null | tr -d '\r')" || out=""
  for p in $PLUGINS; do
    [ -z "$(printf '%s\n' "$out" | ph_claude_ver "$p")" ] || run claude plugin uninstall "$p@plugharbor" --scope user
  done
  out="$(claude plugin marketplace list --json 2>/dev/null | tr -d '\r')" || out=""
  if printf '%s\n' "$out" | ph_claude_has_marketplace; then run claude plugin marketplace remove plugharbor; fi
fi
if command -v codex >/dev/null 2>&1; then
  out="$(codex plugin list 2>/dev/null | tr -d '\r')" || out=""
  for p in $PLUGINS; do
    [ -z "$(printf '%s\n' "$out" | ph_codex_ver "$p")" ] || run codex plugin remove "$p@plugharbor"
  done
  if printf '%s\n' "$out" | ph_codex_has_marketplace; then run codex plugin marketplace remove plugharbor; fi
fi
if command -v agy >/dev/null 2>&1; then
  out="$(agy plugin list 2>/dev/null | tr -d '\r')" || out=""
  for p in $PLUGINS; do
    [ -z "$(printf '%s\n' "$out" | ph_agy_ver "$p")" ] || run agy plugin uninstall "$p"
  done
fi
if command -v herdr >/dev/null 2>&1; then
  out="$(herdr plugin list 2>/dev/null | tr -d '\r')" || out=""
  if printf '%s\n' "$out" | grep -q '^- plugharbor\.sidebar '; then run herdr plugin unlink plugharbor.sidebar; fi
fi

# ---------- ~/.claude 的檔案 ----------
while IFS='|' read -r from to kind; do
  [ -n "$from" ] || continue
  if [ "$kind" = "dir" ]; then remove_dir_items "$REPO_DIR/$from" "$to"; else remove_if_same "$REPO_DIR/$from" "$to"; fi
done <<< "$PH_ENTRIES"
rmdir "$TARGET/hooks" 2>/dev/null || true

if [ -z "$PY" ]; then
  echo "WARN: 找不到能執行的 python，settings.json 的 herdr-parent-tag hook、adapter 副本、pi packages 未清理"
  [ "$FAILS" -eq 0 ] || exit 1
  exit 0
fi

# ---------- settings.json：hook 檔已移除就拿掉指向它的條目（PreToolUse 跑到不存在的腳本會擋下 Bash） ----------
if [ ! -e "$TARGET/hooks/herdr-parent-tag.py" ] && [ -f "$TARGET/settings.json" ]; then
  PYTHONUTF8=1 "$PY" - "$TARGET/settings.json" "$BACKUP" <<'PYEOF' || FAILS=$((FAILS + 1))
import json, os, re, shutil, sys
path, backup = sys.argv[1], sys.argv[2]
HOME = os.path.expanduser("~")
OURS = re.compile(r"(?:~|\$HOME|\$\{HOME\}|" + re.escape(HOME) + r"|" + re.escape(HOME.replace("\\", "/")) + r")"
                  r"[/\\]+\.claude[/\\]+hooks[/\\]+herdr-parent-tag\.py(?![\w.])")
try:
    cur = json.load(open(path, encoding="utf-8"))
except ValueError as e:
    print(f"FAIL: settings.json 不是合法 JSON，未清理：{e}"); sys.exit(1)
hooks = cur.get("hooks") if isinstance(cur.get("hooks"), dict) else {}
mine = lambda h: isinstance(h, dict) and bool(OURS.search(h.get("command") or ""))
touched = False
for event in list(hooks):
    groups = hooks[event] if isinstance(hooks[event], list) else []
    new, here = [], False
    for g in groups:
        hs = g.get("hooks", []) if isinstance(g, dict) else []
        left = [h for h in hs if not mine(h)]
        if len(left) == len(hs):
            new.append(g)
        else:
            here = True
            if left:
                new.append(dict(g, hooks=left))
    touched = touched or here
    if here:
        if new:
            hooks[event] = new
        else:
            del hooks[event]
if touched:
    os.makedirs(backup, exist_ok=True)
    shutil.copy2(path, os.path.join(backup, "settings.json"))
    open(path, "w", encoding="utf-8", newline="\n").write(json.dumps(cur, ensure_ascii=False, indent=2) + "\n")
    print(f"移除: settings.json 的 herdr-parent-tag hook（原檔備份在 {backup}/settings.json）")
PYEOF
fi

# ---------- adapter 副本（~/.codex/plugharbor-manifest.json）與 Codex hooks.json 的條目 ----------
PYTHONUTF8=1 "$PY" - "$HOME" "$BACKUP" <<'PYEOF' || FAILS=$((FAILS + 1))
import hashlib, json, os, shutil, sys
home, backup = sys.argv[1], sys.argv[2]
mpath = os.path.join(home, ".codex", "plugharbor-manifest.json")
if os.path.exists(mpath):
    state = json.load(open(mpath, encoding="utf-8"))
    for rel, digest in (state.get("files") or {}).items():
        target = os.path.join(home, *rel.split("/"))
        if not os.path.isfile(target):
            continue
        if hashlib.sha256(open(target, "rb").read()).hexdigest() != digest:
            print(f"保留: {rel}（內容已被修改）"); continue
        os.remove(target); print(f"移除: {rel}")
        d = os.path.dirname(target)
        while os.path.normpath(d) != os.path.normpath(home) and d.startswith(home):
            try: os.rmdir(d)
            except OSError: break
            d = os.path.dirname(d)
    os.remove(mpath); print("移除: .codex/plugharbor-manifest.json")
hpath = os.path.join(home, ".codex", "hooks.json")
if os.path.exists(hpath):
    data = json.load(open(hpath, encoding="utf-8"))
    groups_by_event = data.get("hooks") or {}
    mine = lambda g: any(("support/plugharbor/" in (h.get("command") or "").replace("\\", "/")) for h in g.get("hooks", []))
    touched = False
    for event in list(groups_by_event):
        keep = [g for g in groups_by_event[event] if not mine(g)]
        if len(keep) != len(groups_by_event[event]):
            touched = True
            if keep: groups_by_event[event] = keep
            else: del groups_by_event[event]
    if touched:
        os.makedirs(os.path.join(backup, "codex"), exist_ok=True)
        shutil.copy2(hpath, os.path.join(backup, "codex", "hooks.json"))
        open(hpath, "w", encoding="utf-8", newline="\n").write(json.dumps(data, indent=2) + "\n")
        print(f"移除: .codex/hooks.json 的 plugharbor 條目（原檔備份在 {backup}/codex/hooks.json）")
PYEOF

# ---------- pi packages 裡指向 plugharbor plugin 的項目 ----------
PI_SETTINGS="$HOME/.pi/agent/settings.json"
if [ -f "$PI_SETTINGS" ]; then
  for p in $PLUGINS; do echo "$REPO_DIR/plugins/$p"; done | PYTHONUTF8=1 "$PY" -c '
import json, os, shutil, sys
path, backup = sys.argv[1], sys.argv[2]; start = os.path.dirname(path)
cur = json.load(open(path, encoding="utf-8"))
def norm(x): return os.path.normcase(os.path.normpath(x))
ours = {norm(l.strip()) for l in sys.stdin if l.strip()}
pkgs = cur.get("packages", [])
keep = [x for x in pkgs if not (isinstance(x, str) and norm(os.path.join(start, x)) in ours)]
if len(keep) != len(pkgs):
    os.makedirs(os.path.join(backup, "pi"), exist_ok=True)
    shutil.copy2(path, os.path.join(backup, "pi", "settings.json"))
    cur["packages"] = keep
    open(path, "w", encoding="utf-8", newline="\n").write(json.dumps(cur, ensure_ascii=False, indent=2) + "\n")
    print(f"移除: ~/.pi/agent/settings.json 的 {len(pkgs) - len(keep)} 個 plugharbor package")
' "$PI_SETTINGS" "$BACKUP" || FAILS=$((FAILS + 1))
fi

if [ "$FAILS" -gt 0 ]; then echo "完成，但有 $FAILS 個步驟失敗（見上方 FAIL）"; exit 1; fi
echo "完成。settings.json 的 statusLine 與其他設定保留；Codex hook 有變動時請在 Codex 執行 /hooks。"
