#!/usr/bin/env python3
"""盤點專案目錄：是否為空、git 模式、技術線索、建議 plugin、既有 AI 設定。

用法：python3 detect.py <root>，印出 JSON。
"""
import json
import subprocess
import sys
from pathlib import Path

SIGNAL_PLUGINS = {
    "dotnet": "backend",
    "vue": "frontend",
    "react": "frontend",
    "sql": "database",
    "avalonia": "desktop",
}
SKIP_DIRS = {"node_modules", ".git", "bin", "obj"}
MAX_DEPTH = 3
AI_PATHS = ["AGENTS.md", "CLAUDE.md", ".claude", ".agents"]


def _read(p):
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _scan(root):
    """走訪最多 MAX_DEPTH 層，回傳檔案清單。"""
    out = []

    def walk(d, depth):
        try:
            entries = sorted(d.iterdir())
        except OSError:
            return
        for e in entries:
            if e.is_dir():
                if e.name not in SKIP_DIRS and depth < MAX_DEPTH:
                    walk(e, depth + 1)
            else:
                out.append(e)

    walk(root, 1)
    return out


def _signals(files):
    sig = set()
    for f in files:
        name, suffix = f.name, f.suffix.lower()
        if suffix in (".csproj", ".sln", ".fsproj"):
            sig.add("dotnet")
            if suffix == ".csproj" and "avalonia" in _read(f).lower():
                sig.add("avalonia")
        elif suffix == ".sql":
            sig.add("sql")
        elif suffix == ".py" or name in ("pyproject.toml", "requirements.txt"):
            sig.add("python")
        elif name == "package.json":
            sig.add("node")
            try:
                pkg = json.loads(_read(f))
            except ValueError:
                pkg = {}
            deps = {}
            if isinstance(pkg, dict):
                for k in ("dependencies", "devDependencies"):
                    if isinstance(pkg.get(k), dict):
                        deps.update(pkg[k])
            for lib in ("vue", "react"):
                if lib in deps:
                    sig.add(lib)
    return sorted(sig)


def _git_tracks_ai_config(root):
    try:
        p = subprocess.run(["git", "ls-files", *AI_PATHS], cwd=root,
                           capture_output=True, text=True, encoding="utf-8")
    except OSError:
        return False
    return p.returncode == 0 and bool(p.stdout.strip())


def _git_toplevel(root):
    """root 所在 work tree 的頂層路徑；不在 repo 內或沒有 git 回傳 None。"""
    try:
        p = subprocess.run(["git", "-C", str(root), "rev-parse", "--show-toplevel"],
                           capture_output=True, text=True, encoding="utf-8")
    except OSError:
        return None
    out = p.stdout.strip()
    return out if p.returncode == 0 and out else None


def _skill_names(d):
    if not d.is_dir():
        return []
    return sorted(c.name for c in d.iterdir() if c.is_dir())


def inventory(root):
    root = Path(root)
    git_toplevel = _git_toplevel(root)
    has_git = git_toplevel is not None
    top = [e for e in root.iterdir() if e.name != ".git"]
    is_empty = not top
    files = _scan(root)
    signals = _signals(files)

    # 只有「自己就是 repo 頂層且空」或完全不在 repo 內才 init；子目錄絕不在別人的 repo 裡再 init
    own_top = has_git and Path(git_toplevel).resolve() == root.resolve()
    if not has_git or (is_empty and own_top):
        git_mode = "init"
    else:
        git_mode = "shared" if _git_tracks_ai_config(root) else "local"

    claude_md = root / "CLAUDE.md"
    if not claude_md.is_file():
        claude_state = "none"
    elif _read(claude_md).strip() == "@AGENTS.md":
        claude_state = "at-agents"
    else:
        claude_state = "custom"

    return {
        "is_empty": is_empty,
        "has_git": has_git,
        "git_toplevel": git_toplevel,
        "git_mode": git_mode,
        "signals": signals,
        "suggested_plugins": sorted({SIGNAL_PLUGINS[s] for s in signals if s in SIGNAL_PLUGINS}),
        "existing": {
            "agents_md": "present" if (root / "AGENTS.md").is_file() else "none",
            "claude_md": claude_state,
            "claude_skills": _skill_names(root / ".claude" / "skills"),
            "agents_skills": _skill_names(root / ".agents" / "skills"),
            "pi_settings": (root / ".pi" / "settings.json").is_file(),
        },
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("用法：detect.py <root>")
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(inventory(Path(sys.argv[1])), ensure_ascii=False, indent=2))
