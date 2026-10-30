#!/bin/bash
# 簡報 Markdown（Marp）→ PDF ＋ PPTX
#   ./build-deck.sh <簡報.md> <輸出目錄>
#
# 輸出目錄是**必填**。交付檔一律落 .tmp/，不進版控——
# 舊版預設「產出與來源同目錄」會把 PDF／PPTX 直接產在 docs 裡，
# 呼叫端得手動搬移，漏搬就進了版控。
#
# PPTX 每頁是一張圖，文字不可編輯（Marp 的限制，已確認可接受）。
set -e

[ -z "$1" ] || [ -z "$2" ] && {
  echo "用法: $0 <簡報.md> <輸出目錄>"
  echo "  輸出目錄必填，請指定 .tmp/ 下的路徑，不要指向版控目錄。"
  exit 1
}

SRC=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
[ -f "$SRC" ] || { echo "找不到來源檔: $SRC"; exit 1; }

mkdir -p "$2"
OUTDIR=$(cd "$2" && pwd)
NAME=$(basename "${SRC%.md}")
BASE="$OUTDIR/$NAME"

. "$(dirname "$0")/find-chrome.sh"
CHROME_PATH=$(find_chrome) || {
  echo "找不到 Chrome（Marp 產 PDF／PPTX 需要）。裝好後重跑，或用 CHROME_PATH 指定路徑。"
  exit 1
}
export CHROME_PATH
npx --yes @marp-team/marp-cli@latest "$SRC" --pdf  --allow-local-files -o "$BASE.pdf"
npx --yes @marp-team/marp-cli@latest "$SRC" --pptx --allow-local-files -o "$BASE.pptx"
ls -lh "$BASE.pdf" "$BASE.pptx"

# 溢出檢查：md 看不出版面，說明框被擠出投影片只有 PDF 看得到
PY=$(cat "$(dirname "$0")/.python-path" 2>/dev/null || echo python3)
"$PY" "$(dirname "$0")/check-deck-overflow.py" "$BASE.pdf" \
  || echo "⚠ 簡報溢出或無法檢查——交付前要處理，見上方訊息"

# 來源目錄若殘留同名產出（舊版行為或前次執行留下的），出聲提醒
for ext in pdf pptx; do
  STRAY="${SRC%.md}.$ext"
  [ -f "$STRAY" ] && echo "⚠ 來源目錄仍有 $STRAY —— 若該目錄納版控，請移除。"
done
exit 0
