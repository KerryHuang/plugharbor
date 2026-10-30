#!/bin/bash
# Claude Code statusline — 精簡兩行版（跨平台：macOS / Linux / Git Bash）
input=$(cat)

# === JSON 解析（純 bash，不依賴 jq）===
get_json_string() {
  echo "$input" | grep -o "\"$1\"[[:space:]]*:[[:space:]]*\"[^\"]*\"" | head -1 | sed "s/\"$1\"[[:space:]]*:[[:space:]]*\"//" | sed 's/"$//'
}
get_json_number() {
  echo "$input" | grep -o "\"$1\"[[:space:]]*:[[:space:]]*[0-9.]*" | head -1 | sed "s/\"$1\"[[:space:]]*:[[:space:]]*//"
}
get_section_number() {
  local s="$1" k="$2"
  echo "$input" | grep -o "\"$s\"[^}]*}" | head -1 \
    | grep -o "\"$k\"[[:space:]]*:[[:space:]]*[0-9.]*" | head -1 \
    | sed "s/\"$k\"[[:space:]]*:[[:space:]]*//"
}

MODEL=$(get_json_string "display_name")
CONTEXT=$(get_json_number "used_percentage")
CTX_INT=${CONTEXT%.*}
[ -z "$CTX_INT" ] && CTX_INT=0
# 實際 context tokens：1M 視窗下百分比會低估（200K 才 20%），改以絕對值上色
CTX_TOKENS=$(get_json_number "total_input_tokens")
CTX_K=$(( ${CTX_TOKENS:-0} / 1000 ))
# 進度條以自動 compact 點為滿格（settings 的 autoCompactWindow；沒設用視窗大小）
COMPACT_AT=$(grep -o '"autoCompactWindow"[[:space:]]*:[[:space:]]*[0-9]*' "$HOME/.claude/settings.json" 2>/dev/null | grep -o '[0-9]*$')
[ -z "$COMPACT_AT" ] && COMPACT_AT=$(get_json_number "context_window_size")
[ -z "$COMPACT_AT" ] || [ "$COMPACT_AT" -le 0 ] && COMPACT_AT=200000
CTX_BAR_PCT=$(( ${CTX_TOKENS:-0} * 100 / COMPACT_AT ))

FIVE_H_PCT=$(get_section_number "five_hour" "used_percentage")
FIVE_H_RESET=$(get_section_number "five_hour" "resets_at")
WEEK_PCT=$(get_section_number "seven_day" "used_percentage")
WEEK_RESET=$(get_section_number "seven_day" "resets_at")

# === Git 資訊 ===
GIT_BRANCH=""
REPO_NAME=""
IS_WORKTREE=false
if git rev-parse --git-dir > /dev/null 2>&1; then
  GIT_BRANCH=$(git branch --show-current 2>/dev/null)
  MAIN_PATH=$(git worktree list --porcelain 2>/dev/null | head -1 | sed -n 's/^worktree //p')
  if [ -n "$MAIN_PATH" ]; then
    REPO_NAME=$(basename "$MAIN_PATH")
  else
    REPO_NAME=$(basename "$(git rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null)
  fi
  GIT_DIR=$(git rev-parse --git-dir 2>/dev/null)
  echo "$GIT_DIR" | grep -q "worktrees" && IS_WORKTREE=true
fi

# === 256-color 前景 palette ===
C_DIM='\e[38;5;240m'
C_MODEL='\e[38;5;255m'
C_REPO='\e[38;5;110m'
C_BRANCH='\e[38;5;78m'
C_WT='\e[38;5;208m'
C_GREEN='\e[38;5;78m'
C_YELLOW='\e[38;5;220m'
C_RED='\e[38;5;167m'
C_RESET='\e[0m'

pct_color() {
  local p="${1:-0}"
  if [ "$p" -le 50 ]; then echo "$C_GREEN"
  elif [ "$p" -le 80 ]; then echo "$C_YELLOW"
  else echo "$C_RED"
  fi
}

# === 進度條（6 格，精簡）===
BAR_CELLS=6
make_bar() {
  local p="${1%.*}"
  [ -z "$p" ] && p=0
  [ "$p" -gt 100 ] && p=100
  local f=$(( p * BAR_CELLS / 100 ))
  [ "$f" -gt "$BAR_CELLS" ] && f=$BAR_CELLS
  local e=$(( BAR_CELLS - f ))
  local color bar="" empty="" i
  color=${2:-$(pct_color "$p")}
  i=0; while [ $i -lt $f ]; do bar="${bar}█"; i=$((i+1)); done
  i=0; while [ $i -lt $e ]; do empty="${empty}░"; i=$((i+1)); done
  printf '%b%s%b%s%b' "$color" "$bar" "$C_DIM" "$empty" "$C_RESET"
}

# 跨平台 epoch 格式化：macOS 用 date -r，GNU 用 date -d
fmt_epoch() {
  local ts="${1%.*}" fmt="$2"
  date -r "$ts" +"$fmt" 2>/dev/null || date -d "@$ts" +"$fmt" 2>/dev/null || printf '?'
}
format_reset() {
  local ts="$1" fmt="$2" now r
  [ -z "$ts" ] && { printf '?'; return; }
  now=$(date +%s)
  r=$(( ${ts%.*} - now ))
  if [ "$r" -le 0 ]; then printf '已重置'; else fmt_epoch "$ts" "$fmt"; fi
}

# === 第 1 行：repo / branch · model ===
if [ "$IS_WORKTREE" = true ]; then
  I_REPO='🌳'; C_REPO_USE="$C_WT"; C_BRANCH_USE="$C_WT"
else
  I_REPO='📦'; C_REPO_USE="$C_REPO"; C_BRANCH_USE="$C_BRANCH"
fi

if [ -n "$REPO_NAME" ] || [ -n "$GIT_BRANCH" ]; then
  printf '%b%s %s%b' "$C_REPO_USE" "$I_REPO" "$REPO_NAME" "$C_RESET"
  [ -n "$GIT_BRANCH" ] && printf '%b/%b%b🌿 %s%b' "$C_DIM" "$C_RESET" "$C_BRANCH_USE" "$GIT_BRANCH" "$C_RESET"
  printf '%b · %b' "$C_DIM" "$C_RESET"
fi
printf '%b🤖 %s%b\n' "$C_MODEL" "$MODEL" "$C_RESET"

# === 第 2 行：context · session · week ===
if [ "$CTX_K" -ge 250 ]; then C_CTX="$C_RED"
elif [ "$CTX_K" -ge 150 ]; then C_CTX="$C_YELLOW"
else C_CTX="$C_GREEN"
fi
printf '%b🧠%b %s %b%d%% %dK%b' "$C_DIM" "$C_RESET" "$(make_bar "$CTX_BAR_PCT" "$C_CTX")" "$C_CTX" "$CTX_BAR_PCT" "$CTX_K" "$C_RESET"

if [ -n "$FIVE_H_PCT" ]; then
  p5=${FIVE_H_PCT%.*}
  printf '%b  ⏳%b %s %b%d%%%b %b%s%b' \
    "$C_DIM" "$C_RESET" "$(make_bar "$p5")" "$(pct_color "$p5")" "$p5" "$C_RESET" \
    "$C_DIM" "$(format_reset "$FIVE_H_RESET" '%H:%M')" "$C_RESET"
fi

if [ -n "$WEEK_PCT" ]; then
  pw=${WEEK_PCT%.*}
  printf '%b  📅%b %s %b%d%%%b %b%s%b' \
    "$C_DIM" "$C_RESET" "$(make_bar "$pw")" "$(pct_color "$pw")" "$pw" "$C_RESET" \
    "$C_DIM" "$(format_reset "$WEEK_RESET" '%m/%d')" "$C_RESET"
fi
