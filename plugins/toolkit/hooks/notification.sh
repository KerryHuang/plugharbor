#!/usr/bin/env bash
# Cross-platform notification hook for Claude Code（Stop hook：完工桌面通知＋音效）
# macOS: afplay + osascript / Linux: paplay|aplay + notify-send / Windows(Git Bash): PowerShell toast
# 契約：純通知用途，任何失敗都不得影響主流程——永遠 exit 0。

# 在 herdr pane 裡由 herdr 自己的 toast 接手（herdr config 的 [ui.toast]）：
# 它只在 blocked／done 通知、略過目前看著的 tab、狀態維持過 delay 才響；這裡每輪 Stop 都響會重複又太吵。
[[ "$HERDR_ENV" == "1" ]] && exit 0

# 不在 herdr 裡也比照同一套：只通知「等你回應」與「真正完成」。
# hook 輸入是 stdin 的 JSON；用 grep 比對，不依賴 jq（Windows Git Bash 不一定有）。
# 字串值裡的引號會被轉義成 \"，所以 "key" 的樣式不會誤中訊息內文。
INPUT=""
[[ -t 0 ]] || INPUT="$(cat)"
# Codex／agy 也經 codex/notify.mjs 走這支，標題標出來源（Codex Stop 帶 turn_id，agy Stop 帶 terminationReason）
if grep -qE '"terminationReason"' <<<"$INPUT"; then TITLE="agy 🤖"
elif grep -qE '"turn_id"' <<<"$INPUT"; then TITLE="Codex 🤖"; fi
if [[ "$1" == "notify" ]]; then
  # 閒置 60 秒提醒（idle_prompt）、背景 agent 完成、登入成功、額度、plugin 訊息都不算「等你回應」
  grep -qE '"notification_type"[[:space:]]*:[[:space:]]*"(permission_prompt|elicitation_dialog|elicitation_url_dialog|agent_needs_input)"' <<<"$INPUT" || exit 0
else
  # Stop hook 讓它繼續做、或背景還有任務在跑（之後會被喚醒接著做）＝還沒真正完成
  grep -qE '"stop_hook_active"[[:space:]]*:[[:space:]]*true' <<<"$INPUT" && exit 0
  grep -qE '"status"[[:space:]]*:[[:space:]]*"(running|pending)"' <<<"$INPUT" && exit 0
  # agy（經 codex/notify.mjs 轉來）：只認正常結束且背景任務全部結束；取消、錯誤、額度用盡都不算完成
  if grep -qE '"terminationReason"' <<<"$INPUT"; then
    grep -qE '"terminationReason"[[:space:]]*:[[:space:]]*"NO_TOOL_CALL"' <<<"$INPUT" || exit 0
    grep -qE '"fullyIdle"[[:space:]]*:[[:space:]]*true' <<<"$INPUT" || exit 0
  fi
fi

TITLE="${TITLE:-Claude Code 🤖}"
# 注意：訊息文案禁用單引號（'）——會提前閉合 PowerShell 字面導致腳本破壞
# $1: 空／stop＝完工通知（Stop hook）；notify＝等你回應（Notification hook）
if [[ "$1" == "notify" ]]; then
  MESSAGES=(
    "等你一句話才能繼續 🙋"
    "有東西要你確認一下 ✋"
    "卡住了，需要你點頭 🚦"
    "叩叩～輪到你回應了 🔔"
  )
else
  MESSAGES=(
    "做好了！來驗收一下吧 ✅"
    "嘿～你的 code 好了喔 🛠️"
    "報告老闆，任務完成！🫡"
    "叮咚～有新進度等你看 📬"
    "搞定了，換你上場 🎯"
    "Code 寫好了，請過目 👀"
    "完工！來 review 一下？🔍"
    "我這邊 OK 了，輪到你了 🏓"
  )
fi
MESSAGE="${MESSAGES[RANDOM % ${#MESSAGES[@]}]}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# wav 是 ffmpeg 轉出的快取，不寫進 plugin 目錄（更新時會被覆蓋），改放 ~/.claude
SOUND_FILE_WAV="$HOME/.claude/notification-sound.wav"
SOUND_FILE_AIFF="$SCRIPT_DIR/notification-sound.aiff"

# 背景執行且脫離行程群組（防 Stop hook 返回後被整組回收）；無 setsid 退回 & + disown
run_detached() {
  if command -v setsid >/dev/null 2>&1; then
    setsid "$@" >/dev/null 2>&1 &
  else
    "$@" >/dev/null 2>&1 &
    disown 2>/dev/null || true
  fi
}

if [[ "$OSTYPE" == "darwin"* ]]; then
  if [[ -f "$SOUND_FILE_AIFF" ]]; then
    afplay "$SOUND_FILE_AIFF" >/dev/null 2>&1 &
  elif [[ -f "$SOUND_FILE_WAV" ]]; then
    afplay "$SOUND_FILE_WAV" >/dev/null 2>&1 &
  elif [[ -f /System/Library/Sounds/Glass.aiff ]]; then
    # 未自備音效檔時，退回 macOS 內建系統音
    afplay /System/Library/Sounds/Glass.aiff >/dev/null 2>&1 &
  fi
  osascript -e "display notification \"$MESSAGE\" with title \"$TITLE\"" 2>/dev/null || true

elif command -v powershell.exe >/dev/null 2>&1; then
  # Windows（Git Bash/Cygwin/WSL 皆以 powershell.exe 存在與否判斷，不靠 OSTYPE）
  # SoundPlayer 只吃 .wav：缺檔時先試 ffmpeg 從 .aiff 一次性轉出，之後都用轉好的檔
  if [[ ! -f "$SOUND_FILE_WAV" && -f "$SOUND_FILE_AIFF" ]] && command -v ffmpeg >/dev/null 2>&1; then
    mkdir -p "$HOME/.claude" 2>/dev/null
    ffmpeg -loglevel quiet -y -i "$SOUND_FILE_AIFF" "$SOUND_FILE_WAV" >/dev/null 2>&1 || true
  fi
  WIN_SOUND_PATH=""
  if [[ -f "$SOUND_FILE_WAV" ]]; then
    WIN_SOUND_PATH=$(cygpath -w "$SOUND_FILE_WAV" 2>/dev/null || wslpath -w "$SOUND_FILE_WAV" 2>/dev/null || echo "")
  fi
  # 全部包 try/catch；優先以 UTF-16LE EncodedCommand 執行（避開字串內插破壞與 emoji 編碼問題）
  PS_SCRIPT="
try {
  Add-Type -AssemblyName System.Windows.Forms -ErrorAction SilentlyContinue
  [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
  [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom, ContentType = WindowsRuntime] | Out-Null
  \$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
  \$content = '<toast><visual><binding template=\"ToastText02\"><text id=\"1\">' + [System.Security.SecurityElement]::Escape('$TITLE') + '</text><text id=\"2\">' + [System.Security.SecurityElement]::Escape('$MESSAGE') + '</text></binding></visual></toast>'
  \$xml.LoadXml(\$content)
  \$toast = [Windows.UI.Notifications.ToastNotification]::new(\$xml)
  [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Claude Code').Show(\$toast)
} catch {}
try {
  if ('$WIN_SOUND_PATH' -ne '' -and (Test-Path '$WIN_SOUND_PATH')) {
    (New-Object System.Media.SoundPlayer('$WIN_SOUND_PATH')).PlaySync()
  } else {
    [System.Media.SystemSounds]::Notification.Play()
    Start-Sleep -Milliseconds 600
  }
} catch {}
"
  if ENCODED=$(printf '%s' "$PS_SCRIPT" | iconv -f UTF-8 -t UTF-16LE 2>/dev/null | base64 -w0 2>/dev/null) && [[ -n "$ENCODED" ]]; then
    run_detached powershell.exe -NoProfile -NonInteractive -EncodedCommand "$ENCODED"
  else
    # 缺 iconv/base64 時退回明碼 -Command（emoji 可能亂碼，但至少有通知與音效）
    run_detached powershell.exe -NoProfile -NonInteractive -Command "$PS_SCRIPT"
  fi

elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
  if [[ -f "$SOUND_FILE_WAV" ]]; then
    if command -v paplay >/dev/null 2>&1; then
      paplay "$SOUND_FILE_WAV" >/dev/null 2>&1 &
    elif command -v aplay >/dev/null 2>&1; then
      aplay -q "$SOUND_FILE_WAV" >/dev/null 2>&1 &
    fi
  fi
  if command -v notify-send >/dev/null 2>&1; then
    notify-send "$TITLE" "$MESSAGE" 2>/dev/null || true
  fi
fi

exit 0
