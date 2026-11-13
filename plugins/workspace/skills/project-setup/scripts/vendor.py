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


def _identify(text):
    """依關鍵句辨識授權，回傳 SPDX 名稱；比對不上回傳 None。"""
    low = " ".join(text.lower().split())
    if "apache license" in low and "version 2.0" in low:
        return "Apache-2.0"
    if "permission is hereby granted, free of charge" in low:
        return "MIT"
    if "permission to use, copy, modify, and/or distribute this software" in low:
        return "ISC" if "provided that the above copyright notice" in low else "0BSD"
    if "this is free and unencumbered software released into the public domain" in low:
        return "Unlicense"
    if "creative commons" in low and "cc0 1.0" in low:
        return "CC0-1.0"
    if "redistribution and use in source and binary forms" in low:
        return "BSD-3-Clause" if "neither the name" in low else "BSD-2-Clause"
    return None


def find_license(skill_dir):
    """從 skill 目錄往上找最近含 LICENSE／COPYING 的一層，到含 .git 的目錄為止。"""
    d = skill_dir.resolve()
    while True:
        files = sorted(
            p for p in d.iterdir()
            if p.is_file() and p.name.upper().startswith(("LICENSE", "COPYING"))
        ) if d.is_dir() else []
        if files:
            return _identify(_read(files[0]))
        if (d / ".git").exists() or d.parent == d:
            return None
        d = d.parent


def pending_reasons(skill_dir, license_id):
    reasons = []
    for p in sorted(skill_dir.rglob("*")):
        rel = p.relative_to(skill_dir).as_posix()
        if p.is_dir() and p.name == "scripts":
            reasons.append(f"scripts: {rel}")
        if p.name in HOOK_MCP_NAMES:
            reasons.append(f"hooks/mcp: {rel}")
        if p.is_file() and os.stat(p).st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH):
            reasons.append(f"executable: {rel}")
    if license_id is None:
        reasons.append("license: 找不到或不在允許清單（MIT、Apache-2.0、BSD、ISC、0BSD、Unlicense、CC0-1.0）")
    return reasons


def vendor(skill_dir, project_root, source):
    skill_dir, project_root = Path(skill_dir), Path(project_root)
    dest = project_root / ".claude" / "skills" / skill_dir.name
    if dest.exists():
        return {"status": "skipped", "reason": "exists"}
    license_id = find_license(skill_dir)
    reasons = pending_reasons(skill_dir, license_id)
    if reasons:
        return {"status": "pending", "reasons": reasons}
    shutil.copytree(skill_dir, dest)
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
