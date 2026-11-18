# -*- coding: utf-8 -*-
"""找寫文章的專案：Claude Code 記錄過的專案中，有 `.claude/rules/posts.md` 的（blog plugin 讀站台規則的位置）。

用法：python3 find_blog_project.py [--claude-json <路徑>]
輸出 JSON 陣列（絕對路徑，已排序）；找不到是 []。
"""
import argparse
import json
import os
import sys


def find(claude_json):
    try:
        with open(claude_json, encoding="utf-8") as f:
            projects = json.load(f).get("projects", {})
    except (OSError, ValueError):
        return []
    hits = set()
    for p in projects:
        real = os.path.realpath(p)
        if os.path.isfile(os.path.join(real, ".claude", "rules", "posts.md")):
            hits.add(real)
    return sorted(hits)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--claude-json", default=os.path.expanduser("~/.claude.json"))
    args = ap.parse_args()
    json.dump(find(args.claude_json), sys.stdout, ensure_ascii=False)
    print()


if __name__ == "__main__":
    main()
