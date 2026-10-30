#!/bin/bash
# 確認 operation-manual 需要的工具都就緒，缺的協助安裝。
# 換一台機器第一次用這支 skill 前先跑這個。
#   ./ensure-tools.sh          檢查並安裝
#   ./ensure-tools.sh --check  只檢查不安裝
CHECK_ONLY=0
[ "$1" = "--check" ] && CHECK_ONLY=1
MISSING=0

say() { printf "%-28s %s\n" "$1" "$2"; }

# 1) Chrome —— 手冊 PDF 列印與 Marp 都要用（跨平台偵測，見 find-chrome.sh）
. "$(dirname "$0")/find-chrome.sh"
if CHROME=$(find_chrome); then
  say "Chrome" "✅  ($CHROME)"
else
  say "Chrome" "❌ 請自行安裝 Google Chrome（PDF 列印與 Marp 都需要）"; MISSING=1
fi

# 2) node / npx —— Marp 簡報
if command -v npx >/dev/null; then
  say "node / npx" "✅"
else
  say "node / npx" "❌ 缺"
  if [ $CHECK_ONLY -eq 0 ] && command -v brew >/dev/null; then
    echo "   → brew install node"; brew install node && say "node / npx" "✅ 已安裝"
  else MISSING=1; fi
fi

# 3) pandoc —— Word 輸出
if command -v pandoc >/dev/null; then
  say "pandoc" "✅"
else
  say "pandoc" "❌ 缺（Word 輸出需要）"
  if [ $CHECK_ONLY -eq 0 ] && command -v brew >/dev/null; then
    echo "   → brew install pandoc"; brew install pandoc && say "pandoc" "✅ 已安裝"
  else MISSING=1; fi
fi

# 4) python + markdown —— build-manual-pdf.py
PY=""
for c in "$(command -v mkdocs)" ; do
  [ -n "$c" ] && PY=$(head -1 "$c" | sed 's/^#!//')
done
[ -z "$PY" ] && PY=$(command -v python3)
if [ -n "$PY" ] && "$PY" -c "import markdown" 2>/dev/null; then
  say "python + markdown" "✅  ($PY)"
  echo "$PY" > "$(dirname "$0")/.python-path"
else
  say "python + markdown" "❌ 缺"
  if [ $CHECK_ONLY -eq 0 ] && [ -n "$PY" ]; then
    echo "   → $PY -m pip install --user markdown"
    "$PY" -m pip install --user --quiet markdown && say "python + markdown" "✅ 已安裝" \
      && echo "$PY" > "$(dirname "$0")/.python-path"
  else MISSING=1; fi
fi

# 5) PyMuPDF —— build-manual-pdf.py 蓋頁碼、check-deck-overflow.py 都要用
if [ -n "$PY" ] && "$PY" -c "import fitz" 2>/dev/null; then
  say "PyMuPDF" "✅  ($PY)"
else
  say "PyMuPDF" "❌ 缺（手冊 PDF 頁碼需要）"
  if [ $CHECK_ONLY -eq 0 ] && [ -n "$PY" ]; then
    echo "   → $PY -m pip install --user pymupdf"
    "$PY" -m pip install --user --quiet pymupdf && say "PyMuPDF" "✅ 已安裝"
  else MISSING=1; fi
fi

echo
if [ $MISSING -eq 0 ]; then
  echo "✅ 工具就緒，可以使用 operation-manual"
else
  echo "⚠ 有工具無法自動安裝，請依上面提示手動處理後重跑"
  exit 1
fi
