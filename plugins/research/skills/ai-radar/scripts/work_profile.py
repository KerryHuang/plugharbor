#!/usr/bin/env python3
"""統計近 N 天 Claude Code transcript 用到的 skill、CLI、副檔名、MCP server，輸出 work-profile.md。

純標準庫、不呼叫模型。ai-radar 每日版（daily.py）每週自動重跑一次；也可手動：
    python3 work_profile.py [--projects ~/.claude/projects] [--days 30] [--out ~/.claude/ai-radar/work-profile.md]
"""
import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

FILE_TOOLS = {"Read", "Edit", "Write", "NotebookEdit"}
# 不算 CLI 的 shell 關鍵字與 builtin
SHELL_WORDS = {
    "cd", "echo", "printf", "export", "set", "unset", "source", ".", "true", "false", "test", "[", "[[",
    "if", "then", "else", "elif", "fi", "for", "while", "until", "do", "done", "case", "esac", "in",
    "function", "return", "exit", "local", "read", "shift", "eval", "wait", "trap", "pwd", "sleep",
    "break", "continue", "declare", "typeset", "alias", "type", "command", "builtin", "exec", "{", "}",
    # python -c／node -e 多行字串裡常見的開頭字，不是 CLI
    "import", "from", "print", "def", "class", "const", "let", "var",
}
PREFIX_WORDS = {"sudo", "env", "time", "nohup", "command", "exec", "!"}
SEGMENT_SPLIT = re.compile(r"&&|\|\||[;|&\n]|\$\(|`|\(")
HEREDOC = re.compile(r"<<-?\s*['\"]?([A-Za-z_][A-Za-z0-9_]*)['\"]?")
CLI_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9._+-]*$")
ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
COMMAND_TAG = re.compile(r"<command-name>/?([^<\s]+)</command-name>")


def strip_heredocs(command: str) -> str:
    """刪掉 heredoc 內文（裡面是資料或別的語言，不是 shell 指令）。"""
    out, delim = [], None
    for line in command.splitlines():
        if delim:
            if line.strip() == delim:
                delim = None
            continue
        out.append(line)
        m = HEREDOC.search(line)
        if m:
            delim = m.group(1)
    return "\n".join(out)


def cli_names(command: str):
    for seg in SEGMENT_SPLIT.split(strip_heredocs(command)):
        words = seg.split()
        while words and (words[0] in PREFIX_WORDS or ASSIGN.match(words[0])):
            words.pop(0)
        if not words:
            continue
        name = words[0]
        if "/" in name:  # 絕對路徑的系統工具取 basename；相對路徑多半是專案腳本，不算
            if not name.startswith("/"):
                continue
            name = name.rsplit("/", 1)[1]
        if name in SHELL_WORDS or not CLI_NAME.match(name):
            continue
        yield name


def parse_ts(value):
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def scan(projects: Path, cutoff: datetime):
    stats = {"skills": Counter(), "cli": Counter(), "ext": Counter(), "mcp": Counter()}
    sessions, seen = set(), set()

    def first_time(key):  # resume 會把歷史複製進新 transcript，依 uuid／tool_use id 去重
        if key is None:
            return True
        if key in seen:
            return False
        seen.add(key)
        return True

    for f in projects.rglob("*.jsonl"):
        try:
            if datetime.fromtimestamp(f.stat().st_mtime, timezone.utc) < cutoff:
                continue
            lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line in lines:
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(rec, dict):
                continue
            ts = parse_ts(rec.get("timestamp"))
            if ts is None or ts < cutoff:
                continue
            content = (rec.get("message") or {}).get("content") if isinstance(rec.get("message"), dict) else None
            counted = False
            if rec.get("type") == "user" and first_time(rec.get("uuid")):
                texts = [content] if isinstance(content, str) else [
                    b.get("text", "") for b in content or [] if isinstance(b, dict) and b.get("type") == "text"]
                for text in texts:
                    for name in COMMAND_TAG.findall(text or ""):
                        stats["skills"][name] += 1
                        counted = True
            if rec.get("type") == "assistant" and isinstance(content, list):
                for b in content:
                    if not isinstance(b, dict) or b.get("type") != "tool_use" or not first_time(b.get("id")):
                        continue
                    counted = True
                    name, inp = b.get("name", ""), b.get("input") or {}
                    if name == "Skill" and inp.get("skill"):
                        stats["skills"][inp["skill"]] += 1
                    elif name == "Bash" and isinstance(inp.get("command"), str):
                        stats["cli"].update(set(cli_names(inp["command"])))  # 一條指令內重複只算一次
                    elif name in FILE_TOOLS:
                        path = inp.get("file_path") or inp.get("notebook_path") or ""
                        suffix = Path(path).suffix.lower()
                        if suffix:
                            stats["ext"][suffix] += 1
                    elif name.startswith("mcp__"):
                        stats["mcp"][name.split("__")[1]] += 1
            if counted:
                sessions.add(rec.get("sessionId") or f.stem)
    return stats, len(sessions)


def render(stats, sessions: int, days: int, now: datetime, top: int) -> str:
    def table(title, header, counter, limit):
        rows = counter.most_common(limit)
        lines = [f"## {title}", "", f"| {header} | 次數 |", "|---|---|"]
        lines += [f"| `{k}` | {v} |" for k, v in rows] or ["| （無） | 0 |"]
        return "\n".join(lines) + "\n"

    head = (f"# 工作模式（work profile）\n\n"
            f"> 產生：{now.date().isoformat()} ｜ 回溯 {days} 天 ｜ {sessions} 個 session ｜ "
            f"由 `research` plugin 的 `work_profile.py` 產生，不要手改\n\n"
            f"ai-radar 每日版只看這裡列到的工具的官方 changelog。\n\n")
    return head + "\n".join([
        table("Skill（含 slash command）", "skill", stats["skills"], top),
        table("CLI", "指令", stats["cli"], top),
        table("MCP server", "server", stats["mcp"], top),
        table("副檔名（Read／Edit／Write）", "副檔名", stats["ext"], top),
    ])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--projects", default=str(Path.home() / ".claude" / "projects"))
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--out", default=str(Path.home() / ".claude" / "ai-radar" / "work-profile.md"))
    ap.add_argument("--top", type=int, default=30)
    ap.add_argument("--now", help="測試用：ISO 時間，預設現在")
    a = ap.parse_args(argv)
    now = parse_ts(a.now) if a.now else datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    stats, sessions = scan(Path(a.projects).expanduser(), now - timedelta(days=a.days))
    out = Path(a.out).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(stats, sessions, a.days, now, a.top), encoding="utf-8")
    print(f"wrote {out}（{sessions} sessions）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
