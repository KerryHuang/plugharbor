#!/usr/bin/env python3
"""agent 暫存生命週期：建立時標記、結束時記帳、開場提議刪除、全區掃描兜底。本身不刪使用者的檔。

起因：2026-11-19 某 workspace 盤點出 agent 留在各專案的暫存約 9.3 GB，沒有任何機制提醒。
設計：docs/superpowers/specs/2026-11-19-agent-scratch-lifecycle-design.md。

暫存單位＝路徑中第一個 `.tmp` 或 `.superpowers` 往下一層的資料夾。狀態在 ~/.claude/scratch-ledger/：
ledger.jsonl（只追加事件：mark、touch、meta、end、keep）、state.json（asked、swept）、sessions/<sid>.seen。

hook（stdin JSON，依 hook_event_name）：
  PostToolUse  Write|Edit|MultiEdit|NotebookEdit|Bash 碰到的單位：新的寫 mark 並提示補用途／期限，舊的寫 touch
  SessionEnd   本 session 碰過的單位寫 end（含大小，0.5 秒內量不完標 partial）
  SessionStart startup 時列出本專案已過期的單位、到期提議全區掃描
CLI：mark <路徑> [--purpose P] [--ttl 1d|7d|handoff]；keep [--root R] [路徑…]；sweep [--json] [--skip] [--root R]…
hook 一律 fail-open。
"""
import argparse
import datetime
import json
import os
import re
import shlex
import shutil
import sys
import time
from pathlib import Path

SCRATCH_NAMES = (".tmp", ".superpowers")
TTL_DAYS = {"1d": 1, "7d": 7}
TTLS = ("1d", "7d", "handoff")
DEFAULT_TTL = "7d"
KEEP_DAYS = 7
STALE_DAYS = 14
LOW_DISK_GB = 20
SWEEP_EVERY_DAYS = 7
MAX_PROPOSE = 4
END_BUDGET = 0.5
INSPECT_LIMIT = 2000
WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
DELIVERABLE_EXT = {".pptx", ".docx", ".xlsx", ".pdf", ".key", ".mp4", ".mov", ".wav", ".flac", ".m4a"}
SCRIPT = os.path.abspath(__file__)


def home():
    return Path(os.environ.get("SCRATCH_LEDGER_HOME") or os.path.expanduser("~/.claude/scratch-ledger"))


def now():
    return datetime.datetime.now().astimezone()


def today():
    return now().date().isoformat()


def parse_ts(s):
    try:
        t = datetime.datetime.fromisoformat(s)
        return t if t.tzinfo else t.astimezone()
    except (TypeError, ValueError):
        return None


# ---------- 單位 ----------

def unit_of(path):
    """第一個 .tmp／.superpowers 往下一層的實體路徑（解開 symlink，帳本鍵值才一致）；`.tmp` 本身與其下的裸檔回 None。"""
    parts = os.path.realpath(path).split(os.sep)
    for i, part in enumerate(parts[:-1]):
        if part in SCRATCH_NAMES:
            unit = os.sep.join(parts[: i + 2])
            if len(parts) > i + 2 or os.path.isdir(unit):
                return unit
            return None
    return None


def bash_units(command, cwd):
    """指令裡提到 .tmp/<名>、.superpowers/<名> 的字樣，以 cwd 解開成單位（依出現順序、不重複）。"""
    out = []
    for tok in re.split(r"[\s'\";|&<>()=`]+", command):
        if not any(f"{n}/" in tok for n in SCRATCH_NAMES):
            continue
        tok = os.path.expanduser(tok)
        unit = unit_of(os.path.normpath(os.path.join(cwd, tok)))
        if unit and unit not in out:
            out.append(unit)
    return out


def under(path, root):
    for p, r in ((path, root), (os.path.realpath(path), os.path.realpath(root))):
        if p.startswith(r.rstrip(os.sep) + os.sep):
            return True
    return False


def inspect(d):
    """深度 3、最多看 INSPECT_LIMIT 項：最晚 mtime、worktree 刪除指令、git repo、成品檔名、是否沒看完。

    mtime 往下看三層，防沒有 hook 的 CLI 或背景程式在深層寫檔卻被當成閒置。
    """
    info = {"latest": os.stat(d).st_mtime, "worktrees": [], "repos": [], "deliverables": [], "truncated": False}
    stack, seen = [(d, 0)], 0
    while stack:
        cur, depth = stack.pop()
        try:
            entries = list(os.scandir(cur))
        except OSError:
            continue
        for e in entries:
            seen += 1
            if seen > INSPECT_LIMIT:
                info["truncated"] = True
                stack.clear()
                break
            try:
                info["latest"] = max(info["latest"], e.stat(follow_symlinks=False).st_mtime)
                if e.name == ".git":
                    if e.is_dir(follow_symlinks=False):
                        info["repos"].append(cur)
                    else:
                        cmd = worktree_remove(cur, e.path)
                        info["worktrees" if cmd else "repos"].append(cmd or cur)
                elif e.is_dir(follow_symlinks=False):
                    if depth < 2:
                        stack.append((e.path, depth + 1))
                elif os.path.splitext(e.name)[1].lower() in DELIVERABLE_EXT and len(info["deliverables"]) < 3:
                    info["deliverables"].append(e.name)
            except OSError:
                pass
    info["latest"] = datetime.datetime.fromtimestamp(info["latest"]).astimezone()
    return info


def worktree_remove(wt, git_file):
    """`.git` 檔指向 <主 repo>/.git/worktrees/<名> 且主 repo 存在 → shell 安全的 remove 指令，否則 None。"""
    line = Path(git_file).read_text(encoding="utf-8", errors="replace").strip()
    if not line.startswith("gitdir:"):
        return None
    gitdir = os.path.normpath(os.path.join(wt, line[len("gitdir:"):].strip()))
    marker = os.sep + os.path.join(".git", "worktrees") + os.sep
    if marker not in gitdir:
        return None
    main = gitdir.split(marker)[0]
    if not os.path.isdir(os.path.join(main, ".git")):
        return None
    return f"git -C {shlex.quote(main)} worktree remove {shlex.quote(wt)}"


def dir_size(path, deadline):
    """遞迴加總檔案大小，不跟 symlink；超過 deadline（time.monotonic）回 (已算到的數, True)。"""
    total, stack = 0, [path]
    while stack:
        if time.monotonic() > deadline:
            return total, True
        try:
            with os.scandir(stack.pop()) as it:
                for e in it:
                    if time.monotonic() > deadline:
                        return total, True
                    try:
                        if e.is_dir(follow_symlinks=False):
                            stack.append(e.path)
                        else:
                            total += e.stat(follow_symlinks=False).st_size
                    except OSError:
                        pass
        except OSError:
            pass
    return total, False


# ---------- 帳本 ----------

def read_events(base):
    f = base / "ledger.jsonl"
    if not f.is_file():
        return []
    events = []
    for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(e, dict) and e.get("dir") and e.get("ev"):
            events.append(e)
    return events


def append(ev):
    base = home()
    base.mkdir(parents=True, exist_ok=True)
    ev = {"ts": now().isoformat(timespec="seconds"), **ev}
    with open(base / "ledger.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps(ev, ensure_ascii=False) + "\n")


def fold(events):
    """依 dir 摺疊事件：created、purpose、ttl、last（最後活動）、open（還沒 end 的 session）、end_reason、size、keep_until。"""
    recs = {}
    for e in events:
        r = recs.setdefault(e["dir"], {"created": None, "purpose": None, "ttl": None, "last": None,
                                       "open": set(), "end_reason": None, "size": 0, "keep_until": ""})
        ev, sid, ts = e["ev"], e.get("session"), parse_ts(e.get("ts"))
        if ev in ("mark", "touch") and sid:
            r["open"].add(sid)
            if ev == "mark":
                r["created"] = r["created"] or e.get("created")
        elif ev == "meta":
            r["purpose"] = e.get("purpose") or r["purpose"]
            r["ttl"] = e.get("ttl") or r["ttl"]
        elif ev == "end":
            r["open"].discard(sid)
            r["end_reason"] = e.get("reason")
            r["size"] = e.get("size") or 0
        elif ev == "keep":
            r["keep_until"] = max(r["keep_until"], e.get("until") or "")
            continue
        if ts and (r["last"] is None or ts > r["last"]):
            r["last"] = ts
    return recs


def load_state():
    try:
        return json.loads((home() / "state.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def update_state(key, value, sub=None):
    """重讀再改一個欄位再寫，不拿舊快照蓋掉並行 session 剛寫的欄位；sub 給定時改 state[key][sub]。"""
    state = load_state()
    if sub is None:
        state[key] = value
    else:
        state.setdefault(key, {})[sub] = value
    save_state(state)


def save_state(state):
    base = home()
    base.mkdir(parents=True, exist_ok=True)
    tmp = base / f"state.json.{os.getpid()}"
    tmp.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, base / "state.json")


def seen_file(sid):
    return home() / "sessions" / (re.sub(r"[^\w.-]", "_", sid) + ".seen")


# ---------- 判斷 ----------

def is_handoff(d, r):
    return r["ttl"] == "handoff" or r["end_reason"] == "clear" or os.path.isfile(os.path.join(d, "handoff.md"))


def idle_days(d, r, at):
    last = inspect(d)["latest"]
    if r and r["last"] and r["last"] > last:
        last = r["last"]
    return (at - last).total_seconds() / 86400


def expired(d, r, at):
    """開場候選條件 1、3、4（存在與交接檔另判）。"""
    if r["open"] or r["keep_until"] > at.date().isoformat():
        return False
    return idle_days(d, r, at) > TTL_DAYS.get(r["ttl"] or DEFAULT_TTL, 7)


def describe(item):
    info = inspect(item["dir"])
    bits = [human(item["size"]), f"閒置 {int(item['idle'])} 天", "用途：" + (item.get("purpose") or "未填")]
    if item.get("kind") and item["kind"] != "expired":
        bits.append(KIND_LABEL[item["kind"]])
    if info["worktrees"]:
        bits.append("⚠️ 含 git worktree，先 " + "；".join(f"`{w}`" for w in info["worktrees"]))
    if info["repos"]:
        bits.append("⚠️ 含 git repo（可能有沒 push 的 commit，或外面有它的 worktree），先確認再刪")
    if info["deliverables"]:
        bits.append("⚠️ 含成品檔 " + "、".join(info["deliverables"]) + "，先確認已搬走")
    if info["truncated"]:
        bits.append(f"⚠️ 超過 {INSPECT_LIMIT} 項沒看完，警示可能不全")
    return f"- `{item['dir']}`：" + "、".join(bits)


KIND_LABEL = {"unmarked": "沒標記", "abandoned": "session 沒正常結束", "handoff": "交接檔", "expired": "已過期"}


def human(n):
    for unit, size in (("GB", 1 << 30), ("MB", 1 << 20), ("KB", 1 << 10)):
        if n >= size:
            return f"{n / size:.1f} {unit}"
    return f"{n} B"


ASK_RULES = (
    "用一題 AskUserQuestion（`multiSelect: true`）問要刪哪些：label 用資料夾名，沒有警示的 label 結尾標「（推薦）」"
    "（全都有警示就標第一個），description 寫大小、閒置天數、用途與警示；只有 1 個時改單選「刪除／保留 7 天」。"
    "勾的刪：一般資料夾用單獨一條 `rm -rf \"<絕對路徑>\"`（路徑加雙引號）；有 worktree 的先跑上面的 `git worktree remove`，"
    "有未提交改動就停下報告。沒有 AskUserQuestion 可用（非互動執行）就整段略過，不要改用文字問。")


def propose_text(cands, root):
    shown, rest = cands[:MAX_PROPOSE], cands[MAX_PROPOSE:]
    lines = [f"[toolkit] 這個專案有 {len(cands)} 個 agent 暫存已過期（期限從最後使用起算；刪不刪由使用者決定）："]
    lines += [describe(c) for c in shown]
    lines.append(
        "處理完使用者第一個請求、回合收尾前，" + ASK_RULES +
        f"沒勾的與使用者略過的跑 `python3 {shlex.quote(SCRIPT)} keep --root {shlex.quote(root)} \"<路徑>\"…`（7 天內不再列）；"
        "全刪了也要跑一次不帶路徑的 keep，記下今天已問過。")
    if rest:
        lines.append(f"其餘 {len(rest)} 個（共 {human(sum(c['size'] for c in rest))}）下次再問。")
    return "\n".join(lines)


def free_gb():
    env = os.environ.get("SCRATCH_LEDGER_FREE_GB")  # 測試用
    if env:
        return float(env)
    return shutil.disk_usage(os.path.expanduser("~")).free / 1e9


def sweep_reason(state, at):
    swept = parse_ts(state.get("swept"))
    gb = free_gb()
    if gb < LOW_DISK_GB and (swept is None or swept.date() != at.date()):
        return f"家目錄所在磁碟只剩 {gb:.0f} GB"
    if swept is None:
        return "還沒跑過全區暫存掃描"
    days = (at - swept).days
    return f"距上次全區暫存掃描已 {days} 天" if days >= SWEEP_EVERY_DAYS else ""


# ---------- hook ----------

def on_post_tool(p):
    sid, tool, ti = p.get("session_id"), p.get("tool_name"), p.get("tool_input") or {}
    cwd = p.get("cwd") or os.getcwd()
    if tool in WRITE_TOOLS:
        path = ti.get("file_path") or ti.get("notebook_path")
        units = [unit_of(os.path.join(cwd, path))] if path else []
    elif tool == "Bash":
        units = bash_units(ti.get("command") or "", cwd)
    else:
        return None
    units = [u for u in units if u and os.path.isdir(u)]
    if not units:
        return None
    sf = seen_file(sid)
    seen = set(sf.read_text(encoding="utf-8").splitlines()) if sf.is_file() else set()
    new = [u for u in units if u not in seen]
    if not new:
        return None
    sf.parent.mkdir(parents=True, exist_ok=True)
    with open(sf, "a", encoding="utf-8") as fh:
        fh.write("".join(u + "\n" for u in new))
    recs = fold(read_events(home()))
    marked = []
    for u in new:
        if u in recs:
            append({"ev": "touch", "dir": u, "session": sid})
            continue
        st = os.stat(u)
        created = datetime.datetime.fromtimestamp(getattr(st, "st_birthtime", st.st_mtime)).astimezone()
        append({"ev": "mark", "dir": u, "session": sid, "created": created.isoformat(timespec="seconds")})
        marked.append(u)
    if not marked:
        return None
    return ("[toolkit] 新暫存已記到本 session：" + "、".join(f"`{u}`" for u in marked) +
            "。期限預設 7 天（從最後使用起算）。你依任務自己判斷、不必問使用者，用一行補上用途與期限："
            f"`python3 {shlex.quote(SCRIPT)} mark \"<資料夾>\" --purpose \"<一句話>\" --ttl 7d`"
            "（`--ttl` 擇一填 1d、7d、handoff；交接檔用 handoff）。")


def on_session_end(p):
    sid = p.get("session_id")
    deadline = time.monotonic() + END_BUDGET
    for d, r in fold(read_events(home())).items():
        if sid in r["open"] and os.path.isdir(d):
            size, partial = dir_size(d, deadline)
            append({"ev": "end", "dir": d, "session": sid, "reason": p.get("reason") or "", "size": size,
                    "partial": partial})
    try:
        seen_file(sid).unlink()
    except FileNotFoundError:
        pass
    return None


def candidates(root, recs, at):
    out = []
    for d, r in recs.items():
        if not under(d, root) or not os.path.isdir(d) or is_handoff(d, r) or not expired(d, r, at):
            continue
        out.append({"dir": d, "size": r["size"], "idle": idle_days(d, r, at), "purpose": r["purpose"]})
    return sorted(out, key=lambda c: -c["size"])


def on_session_start(p):
    if p.get("source", "startup") != "startup" or os.environ.get("AGENT_DISPATCH_UNATTENDED") == "1":
        return None
    root = os.path.abspath(os.environ.get("CLAUDE_PROJECT_DIR") or p.get("cwd") or os.getcwd())
    at, state, parts = now(), load_state(), []
    if (state.get("asked") or {}).get(root) != at.date().isoformat():
        cands = candidates(root, fold(read_events(home())), at)
        if cands:
            parts.append(propose_text(cands, root))
    reason = sweep_reason(state, at)
    if reason:
        parts.append(
            f"[toolkit] {reason}：處理完使用者第一個請求（與上面的暫存提議）後，用一題 AskUserQuestion 問要不要跑全區暫存掃描"
            "（掃各專案的 .tmp／.superpowers，可能要數十秒，只讀不刪）。同意就跑 "
            f"`python3 {shlex.quote(SCRIPT)} sweep`，照輸出依大小問前 4 個，" + ASK_RULES +
            f"沒勾的跑 `python3 {shlex.quote(SCRIPT)} keep \"<路徑>\"…`。"
            f"婉拒就跑 `python3 {shlex.quote(SCRIPT)} sweep --skip`（7 天後再提）。")
    return "\n\n".join(parts) or None


HANDLERS = {"PostToolUse": on_post_tool, "SessionEnd": on_session_end, "SessionStart": on_session_start}


def run_hook():
    try:
        p = json.loads(sys.stdin.buffer.read().decode("utf-8") or "{}")
        handler = HANDLERS.get(p.get("hook_event_name"))
        if not handler or not p.get("session_id"):
            return 0
        msg = handler(p)
        if msg:
            out = {"hookSpecificOutput": {"hookEventName": p["hook_event_name"], "additionalContext": msg}}
            sys.stdout.buffer.write(json.dumps(out, ensure_ascii=False).encode("utf-8"))
    except Exception as e:  # fail-open，原因留在 stderr 供 debug
        sys.stderr.buffer.write(f"scratch-ledger skipped: {e!r}\n".encode("utf-8"))
    return 0


# ---------- CLI ----------

def cmd_mark(a):
    if a.ttl and a.ttl not in TTLS:
        print(f"--ttl 只收 {'、'.join(TTLS)}", file=sys.stderr)
        return 2
    u = unit_of(a.path)
    if not u or not os.path.isdir(u):
        print(f"不是暫存單位（.tmp／.superpowers 下一層的資料夾）：{a.path}", file=sys.stderr)
        return 2
    append({"ev": "meta", "dir": u, "purpose": a.purpose, "ttl": a.ttl})
    print(f"已記：{u}（期限 {a.ttl or DEFAULT_TTL}）")
    return 0


def cmd_keep(a):
    until = (now().date() + datetime.timedelta(days=KEEP_DAYS)).isoformat()
    units = []
    for path in a.paths:
        u = unit_of(path)
        if not u:
            print(f"不是暫存單位：{path}", file=sys.stderr)
            return 2
        units.append(u)
    for u in units:
        append({"ev": "keep", "dir": u, "until": until})
    if a.root:
        update_state("asked", today(), sub=os.path.abspath(a.root))
    print(f"保留 {len(units)} 個到 {until}")
    return 0


def sweep_roots(recs, extra):
    if extra:
        return [os.path.abspath(r) for r in extra]
    roots = set()
    try:
        roots.update(json.loads((home() / "config.json").read_text(encoding="utf-8")).get("roots") or [])
    except (OSError, ValueError):
        pass
    for d in recs:
        project = d.split(os.sep + ".tmp" + os.sep)[0].split(os.sep + ".superpowers" + os.sep)[0]
        roots.add(os.path.dirname(project))
    roots.add(os.path.dirname(os.path.abspath(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())))
    return sorted(os.path.expanduser(r) for r in roots)


def subdirs(path):
    """path 底下的資料夾（不含 symlink）；沒權限或不存在回空（別人的家目錄、壞掉的掛載點）。"""
    try:
        with os.scandir(path) as it:
            return [e.path for e in it if e.is_dir(follow_symlinks=False)]
    except OSError:
        return []


def sweep(roots, recs, at):
    units = {d for d in recs if os.path.isdir(d)}
    for root in roots:
        for project in [root, *subdirs(root)]:
            for name in SCRATCH_NAMES:
                units.update(os.path.realpath(u) for u in subdirs(os.path.join(project, name)))
    out = []
    for d in sorted(units):
        r = recs.get(d)
        if r and r["keep_until"] > at.date().isoformat():
            continue
        idle = idle_days(d, r, at)
        ttl = TTL_DAYS.get((r or {}).get("ttl") or DEFAULT_TTL, 7)
        if r is None:
            kind = "unmarked" if idle >= STALE_DAYS else None
        elif is_handoff(d, r):
            kind = "handoff" if idle >= STALE_DAYS else None
        elif r["open"]:
            kind = "abandoned" if idle > ttl else None
        else:
            kind = "expired" if idle > ttl else None
        if kind:
            out.append({"dir": d, "kind": kind, "idle": idle, "purpose": (r or {}).get("purpose"),
                        "size": dir_size(d, float("inf"))[0]})
    return sorted(out, key=lambda c: -c["size"])


def prune():
    """丟掉資料夾已不存在的紀錄。寫入前才重讀，縮小與並行 append 的競態窗口（只剩毫秒級）。"""
    events = read_events(home())
    keep = [e for e in events if os.path.isdir(e["dir"])]
    if len(keep) == len(events):
        return
    base = home()
    tmp = base / f"ledger.jsonl.{os.getpid()}"
    tmp.write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in keep), encoding="utf-8")
    os.replace(tmp, base / "ledger.jsonl")


def cmd_sweep(a):
    at = now()
    if a.skip:
        update_state("swept", at.isoformat(timespec="seconds"))
        print("已記下：7 天後再提議全區掃描")
        return 0
    recs = fold(read_events(home()))
    items = sweep(sweep_roots(recs, a.root), recs, at)
    prune()
    update_state("swept", at.isoformat(timespec="seconds"))
    if a.json:
        print(json.dumps([{**i, "idle": int(i["idle"])} for i in items], ensure_ascii=False))
        return 0
    if not items:
        print("沒有要清的暫存。")
        return 0
    print(f"共 {len(items)} 個、{human(sum(i['size'] for i in items))}（依大小排序）：")
    for i in items:
        print(describe(i))
    return 0


def main(argv):
    ap = argparse.ArgumentParser(prog="scratch-ledger.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("mark")
    m.add_argument("path")
    m.add_argument("--purpose")
    m.add_argument("--ttl")
    k = sub.add_parser("keep")
    k.add_argument("--root")
    k.add_argument("paths", nargs="*")
    s = sub.add_parser("sweep")
    s.add_argument("--json", action="store_true")
    s.add_argument("--skip", action="store_true")
    s.add_argument("--root", action="append")
    a = ap.parse_args(argv)
    return {"mark": cmd_mark, "keep": cmd_keep, "sweep": cmd_sweep}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]) if len(sys.argv) > 1 else run_hook())
