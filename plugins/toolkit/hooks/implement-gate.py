#!/usr/bin/env python3
"""PreToolUse hook for the Skill tool：有 lifecycle 設定的 repo，規劃／執行 skill 前先把入口拉回 lifecycle:implement。

superpowers 的 brainstorming → writing-plans → executing-plans／subagent-driven-development 會自動交接，
派工 worker 拿到「照計畫實作」也直接開工，不會經過 lifecycle:implement（驗收對照與回填因此漏掉）。
起因：docs/retrospective/20261123-implement-bypass/report.md（22 個 session 只叫到 2 次）。

攔 writing-plans／executing-plans／subagent-driven-development，三個條件同時成立才 deny：
  1. cwd 往上找得到 git root，且該處有 `.plugharbor/lifecycle.yml`（沒裝 lifecycle 的 repo 沒有這檔，hook 不作用）
  2. 本 session transcript 沒有叫過 lifecycle:implement 的 Skill tool_use
  3. transcript 裡還沒出現過本 hook 的 deny 標記（每 session 只擋一次，使用者不要走 implement 時重叫同一個 skill 即放行）
任何解析失敗一律 fail-open。
"""
import json
import os
import sys

GATED = {
    "superpowers:writing-plans",
    "superpowers:executing-plans",
    "superpowers:subagent-driven-development",
}
IMPLEMENT = {"lifecycle:implement"}
MARKER = "[implement-gate]"
REASON = (
    MARKER + " 這個 repo 有 lifecycle 設定，先叫 lifecycle:implement，它會接手規劃與執行；"
    "使用者明確不要走 implement 時，直接重叫同一個 skill 即可放行。"
)


def has_lifecycle_config(cwd):
    d = os.path.abspath(cwd)
    while True:
        if os.path.exists(os.path.join(d, ".git")):
            return os.path.isfile(os.path.join(d, ".plugharbor", "lifecycle.yml"))
        parent = os.path.dirname(d)
        if parent == d:
            return False
        d = parent


def transcript_state(path):
    """回傳 (叫過 implement, 已擋過一次)；讀不到就當兩者皆是（fail-open）。"""
    called = gated = False
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if MARKER in line:
                    gated = True
                if '"lifecycle:implement"' not in line:
                    continue
                try:
                    content = (json.loads(line).get("message") or {}).get("content")
                except Exception:
                    continue
                for item in content if isinstance(content, list) else []:
                    if (isinstance(item, dict) and item.get("type") == "tool_use" and item.get("name") == "Skill"
                            and (item.get("input") or {}).get("skill") in IMPLEMENT):
                        called = True
    except Exception:
        return True, True
    return called, gated


def main() -> int:
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        payload = json.load(sys.stdin)
        if payload.get("tool_name") != "Skill":
            return 0
        if (payload.get("tool_input") or {}).get("skill") not in GATED:
            return 0
        if not has_lifecycle_config(payload.get("cwd") or os.getcwd()):
            return 0
        transcript = payload.get("transcript_path")
        if not transcript:
            return 0
        called, gated = transcript_state(transcript)
        if called or gated:
            return 0
    except Exception:
        return 0
    json.dump({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": REASON,
        }
    }, sys.stdout, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
