#!/usr/bin/env bash
# bootstrap.sh 驗證：用暫存的假 repo 代替 GitHub，確認 clone、pull --ff-only、參數轉給 install.sh。
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
fail() { echo "FAIL: $1"; exit 1; }

for s in "$REPO_DIR"/setup/*.sh "$REPO_DIR"/setup/tests/*.sh "$REPO_DIR"/setup/tests/lib/*.sh; do
  bash -n "$s" || fail "語法錯誤: $s"
done

# 假 repo：install.sh 只把收到的參數寫到 $ARGS_LOG
UP="$TMP/upstream"; mkdir -p "$UP/setup"
cat > "$UP/setup/install.sh" <<'SH'
#!/usr/bin/env bash
echo "v1 $*" >> "$ARGS_LOG"
SH
git -C "$UP" init -q
git -C "$UP" add setup/install.sh
git -C "$UP" -c user.name=t -c user.email=t@t commit -qm init
export ARGS_LOG="$TMP/args.log"
H="$TMP/home"; mkdir -p "$H"

HOME="$H" PLUGHARBOR_REPO="$UP" bash "$REPO_DIR/setup/bootstrap.sh" --check >/dev/null || fail "第一次 bootstrap exit 非 0"
[ -d "$H/plugharbor/.git" ] || fail "預設應 clone 到 \$HOME/plugharbor"
grep -qx 'v1 --check' "$ARGS_LOG" || fail "參數未轉給 install.sh：$(cat "$ARGS_LOG")"

# 上游更新後重跑：走 pull --ff-only
sed 's/v1/v2/' "$UP/setup/install.sh" > "$TMP/i" && cp "$TMP/i" "$UP/setup/install.sh"
git -C "$UP" -c user.name=t -c user.email=t@t commit -qam v2
HOME="$H" PLUGHARBOR_REPO="$UP" bash "$REPO_DIR/setup/bootstrap.sh" --yes >/dev/null || fail "第二次 bootstrap（pull）exit 非 0"
grep -qx 'v2 --yes' "$ARGS_LOG" || fail "第二次未 pull 到新版：$(cat "$ARGS_LOG")"

# PLUGHARBOR_SRC 指定位置
HOME="$H" PLUGHARBOR_REPO="$UP" PLUGHARBOR_SRC="$TMP/src" bash "$REPO_DIR/setup/bootstrap.sh" >/dev/null || fail "PLUGHARBOR_SRC bootstrap exit 非 0"
[ -d "$TMP/src/.git" ] || fail "PLUGHARBOR_SRC 未生效"

echo "PASS: bootstrap.sh"
