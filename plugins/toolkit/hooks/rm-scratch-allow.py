#!/usr/bin/env python3
"""PermissionRequest hook（Bash）：rm 的目標全在暫存區就自動核准，免得無人值守卡在確認畫面。

起因：user 層 settings 的 ask 規則（rm -rf * 等）在 auto mode 也一定跳確認，PreToolUse 回 allow 蓋不過
ask 規則；PermissionRequest 在確認框將出現時觸發，回 allow 可放行（2026-11-13 以 claude -p 實測）。
暫存區：Claude 的 session scratchpad（<tmp>/claude-<數字>/<專案>/<session>/ 以下）、路徑中名為 .tmp 或
.superpowers 的目錄（含本身）以下。
只在整條指令都是 rm 與唯讀指令（echo、cd、ls、grep、head、tail、cat、wc、不帶 -i 的 sed、
git status／log／diff／rev-parse／show／branch --show-current），且沒有 $、反引號、轉向、萬用字元時判斷；
目標先解開 .. 與上層 symlink，帶尾斜線的 symlink 不放行。其餘不輸出＝照常跳確認。fail-open。
"""
import glob
import json
import os
import re
import shlex
import sys
import tempfile

HARMLESS = {"echo", "cd", "ls", "pwd", "true", "grep", "head", "tail", "cat", "wc"}
GIT_READONLY = {"status", "log", "diff", "rev-parse", "show"}
TEMP_DIRS = {".tmp", ".superpowers"}
UNSAFE = re.compile(r"[$`<>*?\[\]{}~\\]")


def scratch_roots():
    env = os.environ.get("CLAUDE_SCRATCH_BASE")  # 測試用
    bases = [env] if env else ["/tmp", tempfile.gettempdir()]
    return sorted({os.path.realpath(p) for b in bases for p in glob.glob(os.path.join(b, "claude-*"))
                   if re.fullmatch(r"claude-\d+", os.path.basename(p))})


def resolve(path, cwd):
    """解開 .. 與上層 symlink；目標本身是 symlink 時保留連結本身（rm 只刪連結）。"""
    trailing = path.endswith("/")
    full = os.path.normpath(os.path.join(cwd, path))
    if trailing and os.path.islink(full):
        return None
    return os.path.join(os.path.realpath(os.path.dirname(full)), os.path.basename(full))


def in_scratch(target, roots):
    parts = target.split(os.sep)
    if any(p in TEMP_DIRS for p in parts[:-1]) or parts[-1] in TEMP_DIRS:
        return True
    for root in roots:
        rel = os.path.relpath(target, root)
        if not rel.startswith("..") and len(rel.split(os.sep)) >= 3:
            return True
    return False


def segments(command):
    lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|")
    lexer.whitespace = " \t"
    lexer.whitespace_split = True
    seg = []
    for tok in lexer:
        if tok and set(tok) <= set(";&|\n"):
            if seg:
                yield seg
            seg = []
        elif "\n" in tok:
            for piece in tok.split("\n"):
                if piece:
                    seg.append(piece)
                if seg:
                    yield seg
                seg = []
        else:
            seg.append(tok)
    if seg:
        yield seg


def decide(command, cwd):
    if UNSAFE.search(command):
        return False
    roots = scratch_roots()
    saw_rm = False
    for seg in segments(command):
        name, args = seg[0], seg[1:]
        if name == "cd":
            if len(args) != 1:
                return False
            cwd = os.path.normpath(os.path.join(cwd, args[0]))
        elif name == "rm":
            targets = [a for a in args if not a.startswith("-")]
            if not targets:
                return False
            for t in targets:
                target = resolve(t, cwd)
                if target is None or not in_scratch(target, roots):
                    return False
            saw_rm = True
        elif name == "git":
            if not args or not (args[0] in GIT_READONLY or args == ["branch", "--show-current"]):
                return False
        elif name == "sed":
            if any(a.startswith("-i") or a == "--in-place" for a in args):
                return False
        elif name not in HARMLESS:
            return False
    return saw_rm


def main():
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return
    if payload.get("tool_name") != "Bash":
        return
    command = (payload.get("tool_input") or {}).get("command") or ""
    cwd = payload.get("cwd") or os.getcwd()
    if decide(command, cwd):
        out = {"hookSpecificOutput": {"hookEventName": "PermissionRequest", "decision": {"behavior": "allow"}}}
        sys.stdout.buffer.write(json.dumps(out).encode("utf-8"))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # fail-open＝不表態，照常跳確認
        print(f"[rm-scratch-allow] {e}", file=sys.stderr)
    sys.exit(0)
