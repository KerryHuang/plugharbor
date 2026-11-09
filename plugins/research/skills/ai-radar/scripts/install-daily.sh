#!/usr/bin/env bash
# 安裝 ai-radar 每日版的 launchd 排程（macOS，工作日 09:00）。
#   install-daily.sh            寫入 ~/Library/LaunchAgents 並載入
#   install-daily.sh --print    只印出 plist，不寫檔、不載入
#   install-daily.sh --uninstall
# 跑的是「本腳本所在位置」的 daily.py：從 plugharbor 主 checkout 執行，排程就跟著本機 main。
# AI_RADAR_OUT、RADAR_REPO、RADAR_WORKTREE、RADAR_BLOG、RADAR_CLAUDE 有設定時會一併寫進 plist。
set -euo pipefail

LABEL="com.plugharbor.ai-radar-daily"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="$HOME/Library/LaunchAgents/$LABEL.plist"
OUT="${AI_RADAR_OUT:-$HOME/.claude/ai-radar}"

render() {
  local py claude_bin
  py="$(command -v python3)" || { echo "找不到 python3" >&2; exit 1; }
  claude_bin="$(command -v "${RADAR_CLAUDE:-claude}")" || { echo "找不到 claude CLI" >&2; exit 1; }
  "$py" "$DIR/daily.py" plist --python "$py" \
    --path "$(dirname "$claude_bin"):/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin" \
    --log "$OUT/logs/launchd.log"
}

case "${1:-}" in
  --print)
    render ;;
  --uninstall)
    launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
    rm -f "$DEST"
    echo "已移除 $LABEL" ;;
  "")
    [[ "$(uname)" == "Darwin" ]] || { echo "只支援 macOS（launchd）" >&2; exit 1; }
    mkdir -p "$OUT/logs" "$(dirname "$DEST")"
    render > "$DEST"
    plutil -lint "$DEST"
    launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
    launchctl bootstrap "gui/$(id -u)" "$DEST"
    echo "已安裝 $LABEL → $DEST（工作日 09:00；log：$OUT/logs/）" ;;
  *)
    echo "用法：$0 [--print|--uninstall]" >&2; exit 2 ;;
esac
