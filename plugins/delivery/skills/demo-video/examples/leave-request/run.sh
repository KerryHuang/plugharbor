#!/bin/bash
# 範例：起本機靜態站 → 跑引擎 → 只關自己起的程序。用法：bash run.sh <工作目錄>
# 工作目錄放 node_modules（先跑 ../../scripts/ensure-tools.sh --dir <工作目錄>），成品在 <工作目錄>/out/
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
ENGINE="$HERE/../../scripts/demo-video.mjs"
WORK="${1:?用法：run.sh <工作目錄>}"
PORT=5190
# 埠被別的程序占用就停：錄到別人的頁面比失敗更糟
if lsof -iTCP:$PORT -sTCP:LISTEN >/dev/null 2>&1; then echo "埠 $PORT 已被占用，先處理再跑"; exit 1; fi
python3 -m http.server $PORT --bind 127.0.0.1 --directory "$HERE" >/dev/null 2>&1 &
SRV=$!
trap 'kill $SRV 2>/dev/null' EXIT
for _ in $(seq 40); do curl -s -m 1 -o /dev/null "http://127.0.0.1:$PORT/index.html" && break; sleep 0.25; done
cd "$WORK"
node "$ENGINE" build "$HERE/video.mjs" --out out --base "http://127.0.0.1:$PORT/index.html"
