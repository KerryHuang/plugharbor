#!/usr/bin/env python3
"""SessionStart hook：retrospective 指標帳本有條目到期，就提議跑 toolkit:retrospective。

設定讀專案 `.plugharbor/toolkit.yml` 的 retrospective.path／units_glob；帳本是 <path>/metrics.yml，
格式見 skills/retrospective/references/metrics-ledger.md（每筆 `- id:` 起頭、due 為單行 `{...}`）。
只看 status: open，到期判斷：
  date：今天已到該日
  new_chains：符合 units_glob 的目錄，以 git 首次 commit 日期晚於 since 計，數量達標
已驗過（checks 最後一筆不早於最新證據）就不再提醒，有新證據才再提。
以 regex 解析，不依賴 PyYAML。沒設定、沒帳本、不是 git repo、解析失敗一律靜默 exit 0。
"""
import datetime
import fnmatch
import json
import os
import pathlib
import re
import subprocess
import sys

DEFAULT_GLOB = "docs/*/*"
ENTRY_SPLIT = re.compile(r"^\s*- id:", re.M)
PAIR_RE = re.compile(r"(\w+):\s*[\"']?([^\"',}]+?)[\"']?\s*(?=,|})")
DATE_RE = re.compile(r"date:\s*[\"']?(\d{4}-\d{2}-\d{2})")


def read_settings(root):
    f = root / ".plugharbor" / "toolkit.yml"
    if not f.is_file():
        return {}
    found, inside = {}, False
    for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
        if re.match(r"^retrospective:\s*(#.*)?$", line):
            inside = True
            continue
        if inside and line.strip() and not line[0].isspace():
            break
        m = re.match(r"^\s+(path|units_glob):\s*[\"']?([^\"'#]+?)[\"']?\s*(#.*)?$", line) if inside else None
        if m:
            found[m.group(1)] = m.group(2)
    return found


def field(body, key):
    m = re.search(r"^%s:\s*[\"']?([^\"'\s#]+)" % key, body, re.M)
    return m.group(1) if m else ""


def open_entries(text):
    """回傳 status: open 條目的 (id, metric, due, 最後一筆 check 日期)；格式不符的跳過。"""
    out = []
    for block in ENTRY_SPLIT.split(text)[1:]:
        entry_id = block.split("\n", 1)[0].strip()
        body = "\n".join(line.strip() for line in block.splitlines()[1:])
        due = re.search(r"^due:\s*(\{.*\})", body, re.M)
        if field(body, "status") != "open" or not due:
            continue
        metric = re.search(r"^metric:\s*(.+)$", body, re.M)
        checks = body.split("\nchecks:", 1)[1] if "\nchecks:" in body else ""
        last = max(DATE_RE.findall(checks), default="")
        out.append((entry_id, metric.group(1).strip() if metric else "", dict(PAIR_RE.findall(due.group(1))), last))
    return out


def unit_dates(root, glob, cache):
    """{單位目錄: git 首次 commit 日期}；git 失敗回 None。"""
    if glob in cache:
        return cache[glob]
    parts = glob.strip("/").split("/")
    prefix = "/".join(p for p in parts[: next((i for i, p in enumerate(parts) if any(c in p for c in "*?[")), len(parts))])
    try:
        p = subprocess.run(
            ["git", "-c", "core.quotepath=false", "log", "--diff-filter=A", "--name-only",
             "--format=@@%ad", "--date=short", "--", prefix or "."],
            cwd=root, capture_output=True, text=True, encoding="utf-8", timeout=8)
    except (OSError, subprocess.SubprocessError):
        cache[glob] = None
        return None
    if p.returncode != 0:
        cache[glob] = None
        return None
    dates, current = {}, ""
    for line in p.stdout.splitlines():
        if line.startswith("@@"):
            current = line[2:]
            continue
        segs = line.split("/")
        if current and len(segs) > len(parts):
            unit = "/".join(segs[: len(parts)])
            if fnmatch.fnmatchcase(unit, glob.strip("/")) and current < dates.get(unit, "9999"):
                dates[unit] = current
    cache[glob] = dates
    return dates


def due_reason(due, today, last, root, default_glob, cache):
    if "date" in due:
        return f"日期 {due['date']} 已到" if today >= due["date"] > last else ""
    if due.get("new_chains", "").isdigit() and "since" in due:
        dates = unit_dates(root, due.get("units_glob", default_glob), cache)
        if dates is None:
            return ""
        newer = [d for d in dates.values() if d > due["since"]]
        need = int(due["new_chains"])
        if len(newer) < need or max(newer, default="") <= last:
            return ""
        return f"{due['since']} 後新增工作單位 {len(newer)}/{need} 個"
    return ""


def main():
    try:
        payload = json.loads(sys.stdin.buffer.read().decode("utf-8"))
        if payload.get("source") in ("compact", "resume", "clear"):
            return 0
        root = pathlib.Path(os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or ".")
        settings = read_settings(root)
        if "path" not in settings:
            return 0
        ledger = root / settings["path"] / "metrics.yml"
        if not ledger.is_file():
            return 0
        today = datetime.date.today().isoformat()
        cache, hits = {}, []
        for entry_id, metric, due, last in open_entries(ledger.read_text(encoding="utf-8")):
            reason = due_reason(due, today, last, root, settings.get("units_glob", DEFAULT_GLOB), cache)
            if reason:
                hits.append(f"- {entry_id}（{metric}）：{reason}")
        if not hits:
            return 0
        msg = (f"[toolkit] retrospective 指標帳本（{settings['path']}/metrics.yml）有 {len(hits)} 條待驗指標已到期：\n"
               + "\n".join(hits)
               + "\n在回應使用者第一個請求時，用一句話提議跑 `toolkit:retrospective` 驗收（它的 Step 0 會逐條判定並記進 checks）；"
                 "使用者婉拒就本 session 不再提，不要自行開跑。")
        out = json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": msg}},
                         ensure_ascii=False)
        sys.stdout.buffer.write(out.encode("utf-8"))
    except Exception as e:  # fail-open，原因留在 stderr 供 debug
        sys.stderr.buffer.write(f"retro-due-reminder skipped: {e!r}\n".encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
