#!/usr/bin/env python3
"""PreToolUse hook：把寫成文字的紅線升級成程式攔截。

分三層讀 guard，同名檔由後讀的覆寫：
  1. `$CLAUDE_PLUGIN_ROOT/guards/*.md`（plugin 內建）
  2. `~/.claude/guards/*.md`（user）
  3. `<專案>/.claude/guards/*.md`（專案）
每個檔一條 guard：

    ---
    tool: Bash                 # 逗號分隔：Bash、Write、Edit、MultiEdit
    pattern: <regex>           # 比對 Bash 的 command、Write 的 content、Edit 的 new_string
    action: deny               # deny 擋下；ask 跳確認
    evidence: <為什麼有這條：哪次事故或哪條規則>
    ---
    <修法：被攔時給 agent 看的說明>

命中多條時 deny 優先。沒有 evidence 的 guard 不載入——沒有事故佐證的紅線不加。
壞掉的 guard（缺欄位、regex 錯）略過並記到 stderr；解析不到 stdin 時 fail-open。
概念借自 wayne930242/anchorloop@dc06a89 的 pi/ttsr.ts 與 solid-loop Mechanism，實作為本機自寫。
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

FIELDS = {"Bash": "command", "Write": "content", "Edit": "new_string"}


def _parse(path: Path) -> dict | None:
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    if not text.startswith("---\n"):
        return None
    head, _, body = text[4:].partition("\n---\n")
    g = {"name": path.stem, "message": body.strip()}
    for line in head.splitlines():
        key, sep, val = line.partition(":")
        if sep:
            val = val.strip()
            if len(val) >= 2 and val[0] == val[-1] and val[0] in "'\"":
                val = val[1:-1]
            g[key.strip()] = val
    if not all(g.get(k) for k in ("tool", "pattern", "action", "evidence", "message")):
        return None
    if g["action"] not in ("deny", "ask"):
        return None
    g["tools"] = {t.strip() for t in g["tool"].split(",")}
    g["regex"] = re.compile(g["pattern"], re.M)
    return g


def load_guards(project_dir: str, plugin_root: str | None = None) -> list[dict]:
    dirs = []
    if plugin_root:
        dirs.append(Path(plugin_root) / "guards")
    dirs.append(Path.home() / ".claude" / "guards")
    if project_dir:
        dirs.append(Path(project_dir) / ".claude" / "guards")
    by_name: dict[str, dict] = {}
    for d in dirs:
        for path in sorted(d.glob("*.md")) if d.is_dir() else []:
            try:
                g = _parse(path)
            except (OSError, re.error) as e:
                print(f"guard: {path} 略過：{e}", file=sys.stderr)
                continue
            if g:
                by_name[g["name"]] = g  # 後讀的層覆寫同名檔
            else:
                print(f"guard: {path} 格式不完整，略過", file=sys.stderr)
    return list(by_name.values())


def target_text(tool: str, inp: dict) -> str:
    if tool == "MultiEdit":
        return "\n".join(str(e.get("new_string") or "") for e in inp.get("edits") or [])
    return str(inp.get(FIELDS.get(tool, ""), "") or "")


def decide(payload: dict, guards: list[dict]) -> dict | None:
    tool = payload.get("tool_name") or ""
    text = target_text(tool, payload.get("tool_input") or {})
    hits = [g for g in guards if tool in g["tools"] and text and g["regex"].search(text)]
    if not hits:
        return None
    hits.sort(key=lambda g: g["action"] != "deny")
    g = hits[0]
    return {
        "hookEventName": "PreToolUse",
        "permissionDecision": g["action"],
        "permissionDecisionReason": f"guard {g['name']}：{g['message']}（依據：{g['evidence']}）",
    }


def main() -> int:
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    project = os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or ""
    out = decide(payload, load_guards(project, os.environ.get("CLAUDE_PLUGIN_ROOT")))
    if out:
        json.dump({"hookSpecificOutput": out}, sys.stdout, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
