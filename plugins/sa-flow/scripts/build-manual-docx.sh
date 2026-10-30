#!/bin/bash
# 操作手冊 Markdown → Word（.docx）
#   ./build-manual-docx.sh <手冊.md> [輸出.docx]
#
# 樣式由 manual-reference.docx 控制（對齊 manual-print.css 的視覺）：
#   章標題藍字＋下邊框、節標題左色條、步驟標題淺藍底、說明區塊黃底左橘條、
#   表格藍表頭白字、內文 PingFang TC。
#   要調樣式改 make-docx-reference.py 後重新生成範本，不要手改 docx。
set -e
[ -z "$1" ] && { echo "用法: $0 <手冊.md> [輸出.docx]"; exit 1; }
command -v pandoc >/dev/null || { echo "❌ 需要 pandoc，請先跑 ensure-tools.sh"; exit 1; }

SRC=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
SRC_DIR=$(dirname "$SRC")
OUT="${2:-${SRC%.md}.docx}"

# --resource-path 讓 images/ 相對路徑找得到
HERE=$(cd "$(dirname "$0")" && pwd)
REF="$HERE/manual-reference.docx"
# 範本不進版控，不存在就即時生成
[ -f "$REF" ] || python3 "$HERE/make-docx-reference.py" "$REF"

# 前處理：把開頭的 H1 與文件資訊表轉成封面頁（Title/Subtitle + 分頁符）
PREP=$(mktemp /tmp/manual-docx-XXXXXX.md)
trap 'rm -f "$PREP"' EXIT
python3 "$HERE/prep-docx-cover.py" "$SRC" "$PREP"

pandoc "$PREP" \
  --from=markdown+pipe_tables+raw_html+fenced_divs+raw_attribute \
  --to=docx \
  --reference-doc="$REF" \
  --resource-path="$SRC_DIR" \
  -o "$OUT"

ls -lh "$OUT"
