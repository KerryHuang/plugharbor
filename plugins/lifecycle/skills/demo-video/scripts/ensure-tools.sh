#!/bin/bash
# 確認 demo-video 需要的工具都就緒，缺的協助安裝（Node 依賴只裝在指定的工作目錄，不做全域安裝）。
#   ./ensure-tools.sh --dir <工作目錄>          檢查並安裝
#   ./ensure-tools.sh --dir <工作目錄> --check  只檢查不安裝
CHECK_ONLY=0; DIR=""
while [ $# -gt 0 ]; do
  case "$1" in
    --check) CHECK_ONLY=1 ;;
    --dir) DIR="$2"; shift ;;
  esac
  shift
done
MISSING=0
say() { printf "%-24s %s\n" "$1" "$2"; }

# 1) Chrome —— 不下載瀏覽器。與引擎一致：CHROME_PATH 有設就只認它（必須存在），
#    沒設才認系統安裝的 Google Chrome（引擎用 channel: 'chrome'；單獨裝的 Chromium 要設 CHROME_PATH 才能用）
CHROME=""
if [ -n "$CHROME_PATH" ]; then
  [ -e "$CHROME_PATH" ] && CHROME="$CHROME_PATH" || { say "Chrome" "❌ CHROME_PATH 指向的檔案不存在：$CHROME_PATH"; MISSING=1; CHROME="-"; }
else
  for c in "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
    "/opt/google/chrome/chrome" \
    "C:/Program Files/Google/Chrome/Application/chrome.exe" \
    "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"; do
    [ -e "$c" ] && { CHROME="$c"; break; }
  done
fi
if [ "$CHROME" = "-" ]; then :
elif [ -n "$CHROME" ]; then say "Chrome" "✅  ($CHROME)"
else say "Chrome" "❌ 找不到 Google Chrome。請安裝，或把 CHROME_PATH 設成 Chrome／Chromium 執行檔"; MISSING=1; fi

# 2) node / npm
if command -v node >/dev/null && command -v npm >/dev/null; then say "node / npm" "✅"; else say "node / npm" "❌ 缺（請安裝 Node 18 以上）"; MISSING=1; fi

# 3) ffmpeg / ffprobe —— 合成與驗證；不要求 libass／drawtext（字幕走 PNG overlay），但假 TTS 測試要 libmp3lame
if command -v ffmpeg >/dev/null && command -v ffprobe >/dev/null; then
  say "ffmpeg / ffprobe" "✅"
else
  say "ffmpeg / ffprobe" "❌ 缺"
  if [ $CHECK_ONLY -eq 0 ] && command -v brew >/dev/null; then
    echo "   → brew install ffmpeg"; brew install ffmpeg && say "ffmpeg / ffprobe" "✅ 已安裝" || MISSING=1
  else MISSING=1; fi
fi

# 4) uvx —— 預設語音 edge-tts 經 uvx 取用，不另外安裝
if command -v uvx >/dev/null; then say "uvx (edge-tts)" "✅"; else say "uvx (edge-tts)" "❌ 缺（安裝 uv；或在影片腳本用 tts 換掉語音來源）"; MISSING=1; fi

# 5) playwright-core —— 只裝在工作目錄
if [ -z "$DIR" ]; then
  say "playwright-core" "⚠ 沒給 --dir，略過"
elif [ -d "$DIR/node_modules/playwright-core" ]; then
  say "playwright-core" "✅  ($DIR)"
else
  say "playwright-core" "❌ $DIR 沒有"
  if [ $CHECK_ONLY -eq 0 ]; then
    mkdir -p "$DIR"
    echo "   → (cd $DIR && npm install playwright-core)"
    # 不用 npm init -y：它拿資料夾名稱當 package name，中文或大寫開頭、點開頭的名稱會失敗
    [ -f "$DIR/package.json" ] || printf '{\n  "name": "demo-video-work",\n  "private": true\n}\n' > "$DIR/package.json"
    (cd "$DIR" && npm install --silent playwright-core) \
      && say "playwright-core" "✅ 已安裝" || MISSING=1
  else MISSING=1; fi
fi

echo
if [ $MISSING -eq 0 ]; then echo "✅ 工具就緒，可以使用 demo-video"; else echo "⚠ 有工具無法自動安裝，請依上面提示手動處理後重跑"; exit 1; fi
