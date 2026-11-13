#!/usr/bin/env python3
"""檢查外部 skill 是否可直接安裝（無 scripts／執行檔／hooks／MCP、授權寬鬆），可以就複製。

用法：python3 vendor.py <skill_dir> <project_root> --repo R --commit C --path P，印出 JSON。
回傳 installed／pending／skipped 其中之一。
"""
import argparse
import json
import os
import shutil
import stat
import sys
from pathlib import Path

HOOK_MCP_NAMES = {"hooks", "hooks.json", ".mcp.json", "mcp.json"}


def _read(p):
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


REJECT = (
    "gnu general public license", "gnu lesser", "affero", "commons clause",
    "non-commercial", "noncommercial", "advertising materials",
)
SCRIPT_EXTS = {".sh", ".bash", ".zsh", ".py", ".js", ".mjs", ".ts", ".rb", ".pl", ".ps1", ".bat", ".cmd"}
SCRIPT_DIRS = {"scripts", "bin"}
MAX_UP = 6


def _identify(text):
    """依多句關鍵句辨識授權，回傳 SPDX 名稱；比對不上或含禁用字樣回傳 None。"""
    low = " ".join(text.lower().split())
    if any(w in low for w in REJECT):
        return None
    if "apache license" in low and "version 2.0" in low and "terms and conditions" in low:
        return "Apache-2.0"
    provided = "the software is provided" in low and "as is" in low
    if "permission is hereby granted, free of charge" in low and provided:
        return "MIT"
    if "permission to use, copy, modify, and/or distribute this software" in low and provided:
        return "ISC" if "provided that the above copyright notice" in low else "0BSD"
    if "this is free and unencumbered software released into the public domain" in low:
        return "Unlicense"
    if "creative commons" in low and "cc0 1.0" in low:
        return "CC0-1.0"
    if ("redistributions of source code must retain" in low
            and "redistributions in binary form must reproduce" in low
            and "this software is provided by the copyright holders" in low):
        return "BSD-3-Clause" if "neither the name" in low else "BSD-2-Clause"
    return None


def find_license(skill_dir):
    """往上最多 MAX_UP 層（遇 .git 即止）找最近含 LICENSE／COPYING 的一層，檢查該層全部檔案。

    回傳 (授權字串, 說明)；全部允許時授權字串為去重後以 " / " 連接（如 "Apache-2.0 / MIT"）。
    """
    d = skill_dir.resolve()
    for _ in range(MAX_UP + 1):
        files = sorted(
            p for p in d.iterdir()
            if p.is_file() and p.name.upper().startswith(("LICENSE", "COPYING"))
        )
        if files:
            ids = [_identify(_read(p)) for p in files]
            bad = [p.name for p, i in zip(files, ids) if i is None]
            if bad:
                return None, f"license: {', '.join(bad)} 不在允許清單或含禁用條款"
            return " / ".join(dict.fromkeys(ids)), ""
        if (d / ".git").exists() or d.parent == d:
            break
        d = d.parent
    return None, "license: 找不到授權檔"


def pending_reasons(skill_dir, license_msg):
    reasons = []
    for root, dirs, files in os.walk(skill_dir, followlinks=False):
        for name in dirs + files:
            p = Path(root) / name
            rel = p.relative_to(skill_dir).as_posix()
            if p.is_symlink():
                reasons.append(f"symlink: {rel}")
                continue
            if name.lower() in SCRIPT_DIRS and p.is_dir():
                reasons.append(f"scripts: {rel}")
            if name.lower() in HOOK_MCP_NAMES:
                reasons.append(f"hooks/mcp: {rel}")
            if p.is_file() and _is_executable(p):
                reasons.append(f"executable: {rel}")
    if license_msg:
        reasons.append(license_msg)
    return sorted(reasons)


def _is_executable(p):
    if os.stat(p).st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH):
        return True
    if p.suffix.lower() in SCRIPT_EXTS:
        return True
    try:
        with p.open("rb") as f:
            return f.read(2) == b"#!"
    except OSError:
        return False


def vendor(skill_dir, project_root, source):
    skill_dir, project_root = Path(skill_dir), Path(project_root)
    dest = project_root / ".claude" / "skills" / skill_dir.name
    if dest.exists():
        return {"status": "skipped", "reason": "exists"}
    license_id, license_msg = find_license(skill_dir)
    reasons = pending_reasons(skill_dir, license_msg)
    if reasons:
        return {"status": "pending", "reasons": reasons}
    try:
        shutil.copytree(skill_dir, dest, symlinks=True)
    except Exception:
        shutil.rmtree(dest, ignore_errors=True)  # 不留半成品，下次才不會誤判 exists
        raise
    meta = {**{k: source.get(k) for k in ("repo", "commit", "path")}, "license": license_id}
    (dest / ".source.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return {"status": "installed", "dest": str(dest), "license": license_id}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("skill_dir")
    ap.add_argument("project_root")
    ap.add_argument("--repo", required=True)
    ap.add_argument("--commit", required=True)
    ap.add_argument("--path", required=True)
    a = ap.parse_args()
    src = {"repo": a.repo, "commit": a.commit, "path": a.path}
    print(json.dumps(vendor(a.skill_dir, a.project_root, src), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    sys.exit(main())
