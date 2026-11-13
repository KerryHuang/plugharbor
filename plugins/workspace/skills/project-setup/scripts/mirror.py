#!/usr/bin/env python3
"""把 .claude/skills/* 鏡像到 .agents/skills/*（相對路徑 symlink，建不了就複製），並可寫 .git/info/exclude。

用法：python3 mirror.py <root> [--exclude PATH ...]，印出 JSON。
不覆寫既有的 .agents/skills/*；同名一律略過並列入 skipped。
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

MARKER = ".mirror-source"


class NotGitRepo(ValueError):
    pass


def _digest(src):
    """來源目錄的內容摘要（相對路徑＋檔案內容；symlink 記目標，不跟隨）。"""
    h = hashlib.sha256()
    for dirpath, dirs, files in os.walk(src):
        dirs.sort()
        for f in sorted(files):
            p = Path(dirpath) / f
            h.update(str(p.relative_to(src)).replace(os.sep, "/").encode("utf-8") + b"\0")
            if p.is_symlink():
                h.update(b"L" + os.readlink(p).encode("utf-8", "replace"))
            else:
                h.update(p.read_bytes())
    return h.hexdigest()


def _write_marker(dest, digest):
    (dest / MARKER).write_text(digest + "\n", encoding="utf-8")


def _copy(src, dest):
    """複製（不跟隨 symlink）並寫標記；失敗時清掉半成品後往外丟。"""
    try:
        shutil.copytree(src, dest, symlinks=True)
        _write_marker(dest, _digest(src))
    except BaseException:
        shutil.rmtree(dest, ignore_errors=True)
        raise


def _already_copied(src, dest):
    try:
        return (dest / MARKER).read_text(encoding="utf-8").strip() == _digest(src)
    except OSError:
        return False


def _inside(root, path):
    """path 解開 symlink 後是否仍在 root（解開後）之內。"""
    r, p = os.path.realpath(root), os.path.realpath(path)
    return p == r or p.startswith(r.rstrip(os.sep) + os.sep)


def mirror(project_root):
    root = Path(project_root)
    skills = root / ".claude" / "skills"
    out = {"linked": [], "copied": [], "skipped": []}
    if not skills.is_dir():
        return out
    for src in sorted(skills.iterdir()):
        if not (src.is_dir() and (src / "SKILL.md").is_file()):
            continue
        name = src.name
        dest = root / ".agents" / "skills" / name
        target = os.path.join("..", "..", ".claude", "skills", name)
        if not _inside(root, dest.parent):  # .agents／.agents/skills 是指向專案外的 symlink
            out["skipped"].append(name)
            continue
        if dest.is_symlink():
            if os.readlink(dest) != target:
                out["skipped"].append(name)
            continue
        if dest.exists():
            if not (dest.is_dir() and _already_copied(src, dest)):
                out["skipped"].append(name)
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.symlink(target, dest, target_is_directory=True)
            out["linked"].append(name)
            continue
        except (OSError, NotImplementedError):
            pass
        try:
            _copy(src, dest)
            out["copied"].append(name)
        except OSError:
            out["skipped"].append(name)
    return out


def _exclude_file(root):
    """回傳 (info/exclude 路徑, root 相對 repo 頂層的前綴如 "sub/"；頂層本身為 "")。"""
    git = root / ".git"
    if git.is_dir():
        return git / "info" / "exclude", ""
    try:
        r = subprocess.run(["git", "rev-parse", "--git-path", "info/exclude", "--show-prefix"],
                           cwd=root, capture_output=True, text=True, encoding="utf-8")
    except OSError as e:
        raise NotGitRepo(f"無法執行 git：{e}")
    lines = r.stdout.split("\n")
    if r.returncode == 0 and lines[0].strip():
        return root / lines[0].strip(), (lines[1].strip() if len(lines) > 1 else "")
    raise NotGitRepo(f"{root} 不是 git repo（沒有可用的 .git）")


def _norm(p):
    """去掉 ./ 開頭、/ 開頭與結尾的 /（symlink 對 git 是檔案，`/x/` 比對不到；`/x` 檔案目錄皆可）。"""
    p = p.strip().replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    return p.strip("/")


def exclude(project_root, paths):
    """把路徑（相對專案根）以錨定 repo 頂層的形式加進 info/exclude，冪等；回傳這次新增的行。"""
    f, prefix = _exclude_file(Path(project_root))
    text = f.read_text(encoding="utf-8") if f.is_file() else ""
    # 既有行（含無錨定、結尾 /）與頂層路徑等價視為已存在
    have = {"/" + _norm(s) for s in (line.strip() for line in text.splitlines())
            if s and not s.startswith(("#", "!"))}
    added = []
    for p in paths:
        core = _norm(p)
        line = "/" + prefix + core
        if core and line not in have:
            have.add(line)
            added.append(line)
    if added:
        f.parent.mkdir(parents=True, exist_ok=True)
        sep = "" if not text or text.endswith("\n") else "\n"
        with open(f, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(sep + "\n".join(added) + "\n")
    return added


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--exclude", nargs="*", default=None, metavar="PATH")
    a = ap.parse_args()
    result = {"mirror": mirror(a.root)}
    code = 0
    if a.exclude:
        try:
            result["exclude"] = exclude(a.root, a.exclude)
        except NotGitRepo as e:
            result["error"] = str(e)
            code = 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
