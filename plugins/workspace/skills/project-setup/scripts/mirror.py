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
    git = root / ".git"
    if git.is_dir():
        return git / "info" / "exclude"
    if git.is_file():
        try:
            r = subprocess.run(["git", "rev-parse", "--git-path", "info/exclude"],
                               cwd=root, capture_output=True, text=True, encoding="utf-8")
        except OSError as e:
            raise NotGitRepo(f"無法執行 git：{e}")
        if r.returncode == 0 and r.stdout.strip():
            return root / r.stdout.strip()
    raise NotGitRepo(f"{root} 不是 git repo（沒有可用的 .git）")


def _anchor(p):
    p = p.strip().replace("\\", "/")
    return p if p.startswith("/") else "/" + p


def exclude(project_root, paths):
    """把路徑（錨定在專案根）加進 info/exclude，冪等；回傳這次新增的行。"""
    f = _exclude_file(Path(project_root))
    text = f.read_text(encoding="utf-8") if f.is_file() else ""
    have = {line.strip() for line in text.splitlines()}
    added = []
    for p in paths:
        line = _anchor(p)
        if line != "/" and line not in have:
            have.add(line)
            added.append(line)
    if added:
        f.parent.mkdir(parents=True, exist_ok=True)
        sep = "" if not text or text.endswith("\n") else "\n"
        with open(f, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(sep + "\n".join(added) + "\n")
    return added


def main():
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
