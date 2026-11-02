#!/bin/bash
# 跨平台找 Chrome。source 進來後呼叫 find_chrome，成功時把路徑印到 stdout 並回 0。
#
#   . "$(dirname "$0")/find-chrome.sh"
#   CHROME=$(find_chrome) || { echo "找不到 Chrome"; exit 1; }
#
# 為什麼要有這支：ensure-tools.sh 與 build-deck.sh 原本各自寫死
# `/Applications/Google Chrome.app`，同事在 Windows 跑就誤報缺 Chrome
# （實際裝在 `/c/Program Files/Google/Chrome/Application/chrome.exe`）。
# 同一個 bug 出現在兩支腳本，所以抽出來一處維護。

find_chrome() {
  # 1) 呼叫端已指定就直接用
  if [ -n "$CHROME_PATH" ] && [ -x "$CHROME_PATH" ]; then
    echo "$CHROME_PATH"; return 0
  fi

  # 2) PATH 上的常見執行檔名（Linux、以及有掛 PATH 的 Windows／WSL）
  local c
  for c in google-chrome google-chrome-stable chromium chromium-browser chrome msedge; do
    if command -v "$c" >/dev/null 2>&1; then
      command -v "$c"; return 0
    fi
  done

  # 3) 各平台的預設安裝位置
  local p
  for p in \
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
    "/Applications/Chromium.app/Contents/MacOS/Chromium" \
    "$HOME/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
    "/c/Program Files/Google/Chrome/Application/chrome.exe" \
    "/c/Program Files (x86)/Google/Chrome/Application/chrome.exe" \
    "$LOCALAPPDATA/Google/Chrome/Application/chrome.exe" \
    "/mnt/c/Program Files/Google/Chrome/Application/chrome.exe" \
    "/usr/bin/google-chrome" \
    "/opt/google/chrome/chrome" \
  ; do
    [ -n "$p" ] && [ -x "$p" ] && { echo "$p"; return 0; }
  done

  return 1
}
