#!/bin/bash
# 確認 operation-manual 需要的工具都就緒，缺的協助安裝。
# 換一台機器第一次用這支 skill 前先跑這個。
#   ./ensure-tools.sh          檢查並安裝
#   ./ensure-tools.sh --check  只檢查不安裝
CHECK_ONLY=0
[ "$1" = "--check" ] && CHECK_ONLY=1
MISSING=0
PY=$(command -v python3)

say() { printf "%-28s %s\n" "$1" "$2"; }

# 裝 python 套件到 $PY：虛擬環境不准 --user；有 uv 用 uv pip，否則 pip。
py_install() {
  if "$PY" -c "import sys; sys.exit(sys.prefix == sys.base_prefix)" 2>/dev/null; then
    if command -v uv >/dev/null; then
      echo "   → uv pip install --python $PY $*"; uv pip install --quiet --python "$PY" "$@"
    else
      echo "   → $PY -m pip install $*"; "$PY" -m pip install --quiet "$@"
    fi
  else
    echo "   → $PY -m pip install --user $*"; "$PY" -m pip install --user --quiet "$@"
  fi
}

# 1) Chrome —— 手冊 PDF 列印與 Marp 都要用。偵測邏輯與 browser-docs 的 find-chrome.sh 同源，
#    這裡只做存在檢查；找不到時設 CHROME_PATH（有裝 browser-docs 可參考 browser-docs:live-drive 的環境說明）。
CHROME=""
for c in "$CHROME_PATH" \
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  "$(command -v google-chrome)" "$(command -v chromium)" "$(command -v chrome)" \
  "C:/Program Files/Google/Chrome/Application/chrome.exe" \
  "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"; do
  [ -n "$c" ] && [ -e "$c" ] && { CHROME="$c"; break; }
done
if [ -n "$CHROME" ]; then
  say "Chrome" "✅  ($CHROME)"
else
  say "Chrome" "❌ 找不到。請安裝 Google Chrome，或設 CHROME_PATH"; MISSING=1
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

# 4) python 套件 —— markdown：build-manual-pdf.py；PyMuPDF：手冊頁碼、簡報溢出檢查；
#    Pillow：scripts/annotate.py 疊框用
if [ -z "$PY" ]; then
  say "python3" "❌ 缺"; MISSING=1
else
  say "python3" "✅  ($PY)"
  for spec in "markdown:markdown" "fitz:pymupdf" "PIL:pillow"; do
    mod=${spec%%:*}; pkg=${spec##*:}
    if "$PY" -c "import $mod" 2>/dev/null; then
      say "python + $pkg" "✅"
    else
      say "python + $pkg" "❌ 缺"
      if [ $CHECK_ONLY -eq 0 ]; then
        py_install "$pkg" && say "python + $pkg" "✅ 已安裝" || MISSING=1
      else MISSING=1; fi
    fi
  done
fi

echo
if [ $MISSING -eq 0 ]; then
  echo "✅ 工具就緒，可以使用 operation-manual"
else
  echo "⚠ 有工具無法自動安裝，請依上面提示手動處理後重跑"
  exit 1
fi
