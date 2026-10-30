#!/usr/bin/env bash
# 測試用：在 $1 建 claude／codex／agy／herdr（可再指定 pi）的 stub，參數記到 $STUB_LOG；
# list 類指令的輸出讀 $STUB_STATE/<cli>-list（沒有就回空清單）。另把真的 node／python／git 連進 $2，
# 讓測試的 PATH 只含 stub、$2 與系統目錄，不會碰到真的 CLI。
# 用法：bash stub-cli.sh <stub 目錄> <工具目錄> [cli...]（cli 省略＝claude codex agy herdr）
set -euo pipefail
STUB="$1"; TOOLS="$2"; shift 2
[ "$#" -gt 0 ] || set -- claude codex agy herdr
mkdir -p "$STUB" "$TOOLS"
for c in "$@"; do
  cat > "$STUB/$c" <<'SH'
#!/usr/bin/env bash
name="$(basename "$0")"
echo "$name $*" >> "$STUB_LOG"
# $STUB_STATE/fail 每一行是一條要失敗的完整指令
if [ -f "$STUB_STATE/fail" ] && grep -qxF "$name $*" "$STUB_STATE/fail"; then exit 1; fi
case "$name $*" in
  "claude plugin marketplace list --json") cat "$STUB_STATE/claude-mkt" 2>/dev/null || echo '[]' ;;
  "claude plugin list --json") cat "$STUB_STATE/claude-list" 2>/dev/null || echo '[]' ;;
  "codex plugin list"*) cat "$STUB_STATE/codex-list" 2>/dev/null || true ;;
  "codex mcp list"*) exit 1 ;;
  "agy plugin list"*) cat "$STUB_STATE/agy-list" 2>/dev/null || echo 'Installed plugins:' ;;
  "herdr plugin list"*) cat "$STUB_STATE/herdr-list" 2>/dev/null || echo '0 plugins installed' ;;
esac
exit 0
SH
  chmod +x "$STUB/$c"
done
for t in node python3 python git; do
  p="$(command -v "$t" 2>/dev/null || true)"
  # 只連可執行的實體路徑（Windows 的 python Store stub 跑不起來就略過）
  if [ -n "$p" ] && [ -f "$p" ] && "$p" --version >/dev/null 2>&1; then ln -sf "$p" "$TOOLS/$t"; fi
done
