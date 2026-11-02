#!/usr/bin/env python3
"""量一個工作單位花了多少：哪些 session 動過該目錄、各自幾輪、多少 token（retrospective Step 1C）。

「動過」＝session（含其 subagent）任一工具呼叫的參數裡出現該單位目錄字串（如 `docs/demo/report`）。
單位目錄由 `--units-glob` 決定（預設 `docs/*/*`，每個 `*` 代表一層目錄名）。
輪數只算使用者親手送出的訊息：不含工具結果、背景任務通知、isMeta 注入。
token＝input＋cache 建立＋cache 讀取＋output，同一 message.id 的串流重複列只算一次，subagent 併入母 session。
同一 session 還動過別的單位 → 標「多單位」，並依「工具呼叫碰到各單位的次數」按比例分攤輪數與 token
（share）；合計列加總的是分攤後數字。分攤是近似：讀檔多、寫檔少的單位會被高估。

限制：只讀**本機 Claude Code** transcript（預設 ~/.claude/projects）。Codex、pi 的 transcript 格式不同，
在別台機器跑的輪次也量不到——回報時要寫「僅本機 Claude Code」，不可當成全部成本。

用法：chain_cost.py <單位路徑，如 docs/demo/report> [--units-glob 'docs/*/*'] [--projects-dir <transcript 根目錄>]
"""
import argparse
import glob
import json
import os
import re
import sys
from collections import Counter
from dataclasses import dataclass, field

# Windows 預設 cp950：印中文會亂碼。
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

DEFAULT_GLOB = "docs/*/*"
NOT_HUMAN = ("<task-notification", "<local-command-stdout", "<system-reminder")
USAGE_KEYS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens")


@dataclass
class SessionCost:
    session: str
    first: str = ""
    last: str = ""
    human_turns: int = 0
    assistant_msgs: int = 0
    tokens: int = 0
    multi_unit: bool = False
    share: float = 0.0
    _ids: set = field(default_factory=set, repr=False)
    _features: Counter = field(default_factory=Counter, repr=False)

    @property
    def human_turns_share(self):
        return self.human_turns * self.share

    @property
    def tokens_share(self):
        return self.tokens * self.share


def units_regex(glob):
    """`work/*` → 比對 `work/<名稱>/` 的正規式；每個 `*` 吃一層目錄名。"""
    parts = (re.escape(p) for p in glob.strip("/").split("*"))
    return re.compile(r"[^/\"\\]+".join(parts) + r"/")


def _is_human(entry):
    if entry.get("type") != "user" or entry.get("isMeta"):
        return False
    content = entry.get("message", {}).get("content")
    if isinstance(content, str):
        return not content.lstrip().startswith(NOT_HUMAN)
    if isinstance(content, list):
        return any(b.get("type") == "text" for b in content) and not any(
            b.get("type") == "tool_result" for b in content)
    return False


def _scan(path, cost, count_human, unit_re):
    """讀一份 transcript 累加到 cost；每次工具呼叫碰到的鏈各記一次到 _features。"""
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue  # 寫到一半的最後一列
            day = (entry.get("timestamp") or "")[:10]
            if day:
                cost.first = min(cost.first or day, day)
                cost.last = max(cost.last, day)
            if count_human and _is_human(entry):
                cost.human_turns += 1
            if entry.get("type") != "assistant":
                continue
            msg = entry.get("message", {})
            for block in msg.get("content") or []:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    blob = json.dumps(block.get("input", {}), ensure_ascii=False)
                    cost._features.update({m.group(0).rstrip("/") for m in unit_re.finditer(blob)})
            mid = msg.get("id")
            if mid and mid not in cost._ids:
                cost._ids.add(mid)
                if count_human:
                    cost.assistant_msgs += 1
                usage = msg.get("usage") or {}
                cost.tokens += sum(int(usage.get(k) or 0) for k in USAGE_KEYS)


def collect(feature, root=None, units_glob=DEFAULT_GLOB):
    root = root or os.path.expanduser("~/.claude/projects")
    unit_re = units_regex(units_glob)
    feature = feature.strip("/")
    rows = []
    for main in sorted(glob.glob(os.path.join(root, "*", "*.jsonl"))):
        sid = os.path.basename(main)[:-len(".jsonl")]
        cost = SessionCost(session=sid)
        _scan(main, cost, count_human=True, unit_re=unit_re)
        for sub in glob.glob(os.path.join(os.path.dirname(main), sid, "subagents", "*.jsonl")):
            _scan(sub, cost, count_human=False, unit_re=unit_re)
        if feature in cost._features:
            cost.multi_unit = len(cost._features) > 1
            cost.share = cost._features[feature] / sum(cost._features.values())
            rows.append(cost)
    if not rows:
        raise LookupError(f"{root} 下沒有任何 session 動過 {feature}/")
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("feature", help="單位路徑，需符合 --units-glob，如 docs/demo/report")
    ap.add_argument("--units-glob", default=DEFAULT_GLOB, help="單位目錄樣式，預設 %(default)s")
    ap.add_argument("--projects-dir", help="transcript 根目錄，預設 ~/.claude/projects")
    args = ap.parse_args()
    try:
        rows = collect(args.feature, args.projects_dir, args.units_glob)
    except LookupError as e:
        print(e, file=sys.stderr)
        sys.exit(1)
    rows.sort(key=lambda r: r.first)
    print("| session | 起訖 | 使用者輪數 | token(M) | 本單位占比 | 分攤輪數 | 分攤 token(M) |")
    print("|---|---|---|---|---|---|---|")
    for r in rows:
        print(f"| {r.session[:8]} | {r.first}～{r.last} | {r.human_turns} | {r.tokens / 1e6:.1f} "
              f"| {r.share:.0%} | {r.human_turns_share:.1f} | {r.tokens_share / 1e6:.1f} |")
    print(f"| **合計（僅本機 Claude Code）** | | {sum(r.human_turns for r in rows)} | {sum(r.tokens for r in rows) / 1e6:.1f} "
          f"| {sum(r.multi_unit for r in rows)} 個多單位 | {sum(r.human_turns_share for r in rows):.1f} "
          f"| {sum(r.tokens_share for r in rows) / 1e6:.1f} |")


if __name__ == "__main__":
    main()
