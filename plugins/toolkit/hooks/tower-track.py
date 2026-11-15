#!/usr/bin/env python3
"""塔台心跳與改動追蹤（PreToolUse／UserPromptSubmit／PostToolUse 共用，依 stdin 的 hook_event_name 分流）。

- PreToolUse／UserPromptSubmit：只更新此 worktree 航班的 beat（純檔案操作，不開 git 子程序）。
- PostToolUse（Edit|Write|MultiEdit）：把 tool_input.file_path 記進 touched；該檔首次記錄且與他班
  （活的）航班重疊時，輸出一行 additionalContext 提醒。
fail-open：任何例外、非 git repo、此 worktree 沒有航班，一律 exit 0 無輸出。
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "tower" / "scripts"))


def main():
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stderr = open(os.devnull, "w")
    import tower
    payload = json.load(sys.stdin)
    cwd = payload.get("cwd") or os.getcwd()
    loc = tower.locate(cwd)
    if loc is None:
        return
    root, _gitdir, tdir, _branch = loc
    flight = tower.find_flight(tdir, root)
    if flight is None:
        return
    msg = rel = None
    if payload.get("hook_event_name") == "PostToolUse":
        msg, rel = touch(tower, payload, cwd, root, tdir, flight)
    # 寫入前重讀：航班已被 release／landed 就不寫，免得復活或改回 flying
    try:
        fresh = json.loads((Path(tdir) / "flights" / f"{flight['id']}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    if not isinstance(fresh, dict) or fresh.get("state") != "flying":
        return
    if rel and rel not in fresh.setdefault("touched", []):
        fresh["touched"].append(rel)
    fresh["beat"] = tower.now_iso()
    tower.save_flight(tdir, fresh)
    if msg:
        out = json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse",
                                                 "additionalContext": msg}}, ensure_ascii=False)
        sys.stdout.buffer.write(out.encode("utf-8"))


def touch(tower, payload, cwd, root, tdir, flight):
    path = (payload.get("tool_input") or {}).get("file_path")
    if not path:
        return None, None
    full = os.path.realpath(os.path.join(cwd, path))
    try:
        rel = Path(full).relative_to(root).as_posix()
    except ValueError:
        return None, None
    if rel in flight.get("touched", []):
        return None, None
    probe = {"paths": [], "touched": [rel], "work": {}}
    hits = tower.overlaps(probe, tower._live_others(tdir, flight), tower.shared_globs(root))
    if not hits:
        return None, rel
    who = "、".join(f"{h['flight']}（{h['goal']}）" for h in hits)
    return f"塔台：{rel} 也在航班 {who} 的範圍內，小心撞改；用 tower radar 看詳情。", rel


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
