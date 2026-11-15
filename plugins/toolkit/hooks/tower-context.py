#!/usr/bin/env python3
"""SessionStart hook：repo 內有在飛的塔台航班就輸出一行摘要（≤120 字），沒有就無輸出。fail-open。"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "tower" / "scripts"))
MAX_LEN = 120


def main():
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stderr = open(os.devnull, "w")
    import tower
    payload = json.load(sys.stdin)
    loc = tower.locate(payload.get("cwd") or os.getcwd())
    if loc is None:
        return
    now = tower.datetime.now(tower.timezone.utc)
    flying = [f for f in tower.load_flights(loc[2])
              if f.get("state") == "flying" and not tower.is_lost(f, now)]
    if not flying:
        return
    head = f"塔台：{len(flying)} 班在飛（"
    tail = "），動工前先 takeoff 登記"
    goals = "、".join(str(f.get("goal", "")) for f in flying)
    room = MAX_LEN - len(head) - len(tail)
    if len(goals) > room:
        goals = goals[:room - 1] + "…"
    out = json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart",
                                             "additionalContext": head + goals + tail}},
                     ensure_ascii=False)
    sys.stdout.buffer.write(out.encode("utf-8"))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
