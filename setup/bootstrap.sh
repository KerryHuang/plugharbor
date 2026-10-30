#!/usr/bin/env bash
# 新機器一行安裝：clone（或 pull）plugharbor，再跑 setup/install.sh，參數原樣轉過去。
set -euo pipefail
REPO_URL="${PLUGHARBOR_REPO:-https://github.com/KerryHuang/plugharbor.git}"
DEST="${PLUGHARBOR_SRC:-$HOME/plugharbor}"

if [ ! -d "$DEST/.git" ]; then
  git clone "$REPO_URL" "$DEST"
else
  git -C "$DEST" pull --ff-only
fi
bash "$DEST/setup/install.sh" "$@"
