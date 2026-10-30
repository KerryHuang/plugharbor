#!/usr/bin/env python3
"""feedback-review 的佇列工具：讀佇列、撈前後文、歸檔、定位帳本。

  feedback_queue.py pending [--since D]           未處理佇列（JSON 陣列）
  feedback_queue.py archived [--since D]          archive（Check 上一輪用）
  feedback_queue.py context <id> [--turns N]      依佇列 id 回頭撈該 session 糾正前 N 輪的對話片段
  feedback_queue.py archive <id>... [--disposition 文字]
                                                  搬到 archive.jsonl（加 reviewed_at）並更新 last-review
  feedback_queue.py stamp                         只更新 last-review（佇列沒東西要處理時用）
  feedback_queue.py friction --tried T --found F [--led-by L]
                                                  agent 自記摩擦（被規則帶偏或缺規則），寫進同一個佇列
  feedback_queue.py ledger [--cwd DIR | --user]   帳本路徑：專案＝<git 根>/.claude/feedback-ledger.md
                                                  （不在 repo 時同 --user）；--user＝~/.claude/feedback-loop/ledger.md

--since 給日期（YYYY-MM-DD）表示「該日之後」（不含當日），給完整 ISO 時間表示「該時刻起」。
解析失敗的壞列會拿到 bad-<hash> 形式的 id，可以照常 archive。
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

CLAUDE = Path(os.path.expanduser("~/.claude"))
FEEDBACK = CLAUDE / "feedback-loop"
QUEUE = FEEDBACK / "queue.jsonl"
PROCESSING = FEEDBACK / "queue.processing.jsonl"
ARCHIVE = FEEDBACK / "archive.jsonl"
LAST = FEEDBACK / "last-review"


def _read(path):
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
            if not isinstance(rec, dict):
                raise ValueError
        except ValueError:
            rec = {"id": "bad-" + hashlib.sha1(line.encode("utf-8")).hexdigest()[:8], "raw": line}
        out.append(rec)
    return out


def _append(path, recs):
    if not recs:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in recs))


def _now():
    return datetime.now().astimezone()


def _dt(s):
    dt = datetime.fromisoformat(str(s).strip())
    return dt if dt.tzinfo else dt.astimezone()


def _since(recs, since):
    if not since:
        return recs
    # 只給日期＝改動日之後（不含當日，避免把改動前的同日糾正算進去）
    cut = _dt(since) + timedelta(days=1) if len(since.strip()) == 10 else _dt(since)
    out = []
    for r in recs:
        try:
            if _dt(r.get("ts")) >= cut:
                out.append(r)
        except (ValueError, TypeError):
            pass
    return out


def cmd_friction(a):
    now = _now()
    rec = {
        "id": now.strftime("%Y%m%d%H%M%S") + "-" + os.urandom(3).hex(),
        "ts": now.isoformat(timespec="seconds"),
        "source": "agent",
        "cwd": os.getcwd(),
        "matched": ["friction"],
        "excerpt": f"試了：{a.tried}｜發現：{a.found}" + (f"｜帶偏的：{a.led_by}" if a.led_by else ""),
        "tried": a.tried,
        "found": a.found,
        "led_by": a.led_by or "",
    }
    _append(QUEUE, [rec])
    return rec


def cmd_pending(a):
    return _since(_read(PROCESSING) + _read(QUEUE), a.since)


def cmd_archived(a):
    return _since(_read(ARCHIVE), a.since)


def _text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    return ""


def cmd_context(a):
    rec = next((r for r in _read(PROCESSING) + _read(QUEUE) + _read(ARCHIVE) if r.get("id") == a.id), None)
    if not rec:
        sys.exit(f"找不到佇列 id：{a.id}")
    sid = rec.get("session_id") or ""
    files = list((CLAUDE / "projects").glob(f"*/{sid}.jsonl")) if sid else []
    if not files:
        return {"id": a.id, "error": "transcript 不在（可能已清除）", "excerpt": rec.get("excerpt")}
    head = (rec.get("excerpt") or "")[:60]
    turns, found = [], False
    with open(files[0], encoding="utf-8", errors="replace") as fh:
        for line in fh:   # 逐行串流，只保留最近 N 輪，不整檔載入
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if not isinstance(r, dict) or r.get("type") not in ("user", "assistant"):
                continue
            text = _text((r.get("message") or {}).get("content")).strip()
            if not text:
                continue
            turns.append(f"[{r['type']}] {text[:600]}")
            turns = turns[-(a.turns * 2 + 1):]
            if r["type"] == "user" and head and text.startswith(head):
                found = True
                break
    if not found:
        return {"id": a.id, "error": "transcript 裡找不到這句糾正", "excerpt": rec.get("excerpt")}
    return {"id": a.id, "transcript": str(files[0]), "turns": turns}


def _claim():
    """把 queue.jsonl 改名成 processing 再處理：hook 之後的 append 會落到新的 queue.jsonl，
    不會被我們的改寫吃掉。Windows 上 hook 正開著檔時改名會失敗，短暫重試。"""
    if not QUEUE.exists():
        return
    for _ in range(20):
        try:
            if PROCESSING.exists():   # 上次中斷留下的，先併進來
                _append(PROCESSING, _read(QUEUE))
                QUEUE.unlink()
            else:
                QUEUE.replace(PROCESSING)
            return
        except PermissionError:
            time.sleep(0.1)
    sys.exit("佇列檔被占用，稍後再試")


def cmd_archive(a):
    ids = set(a.ids)
    missing = ids - {r.get("id") for r in _read(PROCESSING) + _read(QUEUE)}
    if missing:
        sys.exit(f"佇列裡沒有這些 id：{sorted(missing)}")
    _claim()
    recs = _read(PROCESSING)
    done = [r for r in recs if r.get("id") in ids]
    keep = [r for r in recs if r.get("id") not in ids]
    now = _now().isoformat(timespec="seconds")
    for r in done:
        r["reviewed_at"] = now
        if a.disposition:
            r["disposition"] = a.disposition
    _append(ARCHIVE, done)
    _append(QUEUE, keep)   # 與 hook 一樣用 append，和並行寫入共存
    PROCESSING.unlink(missing_ok=True)
    LAST.write_text(now, encoding="utf-8")
    return {"archived": len(done), "remaining": len(_read(QUEUE)), "last_review": now}


def cmd_stamp(_):
    now = _now().isoformat(timespec="seconds")
    FEEDBACK.mkdir(parents=True, exist_ok=True)
    LAST.write_text(now, encoding="utf-8")
    return {"last_review": now}


def cmd_ledger(a):
    top = ""
    if not a.user:
        try:
            root = subprocess.run(["git", "-C", a.cwd, "rev-parse", "--show-toplevel"],
                                  capture_output=True, text=True, encoding="utf-8", timeout=10)
            top = root.stdout.strip() if root.returncode == 0 else ""
        except (OSError, subprocess.SubprocessError):
            top = ""
    path = Path(top) / ".claude" / "feedback-ledger.md" if top else FEEDBACK / "ledger.md"
    return {"ledger": str(path), "exists": path.is_file(), "project_root": top or None}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("pending"); s.add_argument("--since")
    s = sub.add_parser("archived"); s.add_argument("--since")
    s = sub.add_parser("context"); s.add_argument("id"); s.add_argument("--turns", type=int, default=3)
    s = sub.add_parser("archive"); s.add_argument("ids", nargs="+")
    s.add_argument("--disposition", help="處置摘要，如「已改 user 層」「雜訊」")
    sub.add_parser("stamp")
    s = sub.add_parser("friction"); s.add_argument("--tried", required=True); s.add_argument("--found", required=True)
    s.add_argument("--led-by", help="帶偏的規則／文件／記憶；沒有條文講到就省略")
    s = sub.add_parser("ledger"); s.add_argument("--cwd", default=os.getcwd()); s.add_argument("--user", action="store_true")
    a = p.parse_args()
    result = globals()["cmd_" + a.cmd](a)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
