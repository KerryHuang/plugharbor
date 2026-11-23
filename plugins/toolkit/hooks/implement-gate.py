#!/usr/bin/env python3
"""PreToolUse hook for the Skill tool：有 lifecycle 設定的 repo，規劃／執行 skill 前先把入口拉回 lifecycle:implement。

superpowers 的 brainstorming → writing-plans → executing-plans／subagent-driven-development 會自動交接，
派工 worker 拿到「照計畫實作」也直接開工，不會經過 lifecycle:implement（驗收對照與回填因此漏掉）。
起因：docs/retrospective/20261123-implement-bypass/report.md（22 個 session 只叫到 2 次）。

攔 writing-plans／executing-plans／subagent-driven-development，三個條件同時成立才 deny：
  1. cwd 往上找得到 git root，且該處有 `.plugharbor/lifecycle.yml`（沒裝 lifecycle 的 repo 沒有這檔，hook 不作用）
  2. 本 session transcript 沒有叫過 lifecycle:implement 的 Skill tool_use
  3. 本 session 還沒擋過（`~/.claude/implement-gate/<session_id>` 狀態檔；每 session 只擋一次，使用者不要走 implement 時重叫同一個 skill 即放行）
任何解析失敗、狀態檔寫不進去、session_id 缺漏，一律 fail-open。
"""
import json
import os
import re
import sys

GATED = {
    "superpowers:writing-plans",
    "superpowers:executing-plans",
    "superpowers:subagent-driven-development",
}
IMPLEMENT = {"lifecycle:implement"}
STATE_DIR = os.environ.get("IMPLEMENT_GATE_STATE_DIR") or os.path.join(os.path.expanduser("~/.claude"), "implement-gate")
REASON = (
    "[implement-gate] 這個 repo 有 lifecycle 設定，先叫 lifecycle:implement，它會接手規劃與執行；"
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


def implement_called(path):
    """transcript 裡叫過 lifecycle:implement 就回 True；讀不到、或含該字串的行解析不了，都當叫過（fail-open）。"""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if "lifecycle:implement" not in line:
                    continue
                try:
                    content = (json.loads(line).get("message") or {}).get("content")
                except Exception:
                    return True
                for item in content if isinstance(content, list) else []:
                    if (isinstance(item, dict) and item.get("type") == "tool_use" and item.get("name") == "Skill"
                            and (item.get("input") or {}).get("skill") in IMPLEMENT):
                        return True
    except Exception:
        return True
    return False


def first_gate(session_id):
    """本 session 第一次擋就建狀態檔並回 True；已擋過、id 不合法或寫不進去回 False（放行）。"""
    if not isinstance(session_id, str) or not re.fullmatch(r"[\w-]+", session_id):
        return False
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        fd = os.open(os.path.join(STATE_DIR, session_id), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(fd)
        return True
    except Exception:
        return False


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
        if implement_called(transcript) or not first_gate(payload.get("session_id")):
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
