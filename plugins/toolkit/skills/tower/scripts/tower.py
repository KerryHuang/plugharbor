#!/usr/bin/env python3
"""Session 塔台：本機航班登記表與基本 CLI（只用標準庫）。

登記檔：<git common dir>/tower/flights/<id>.json；事件：tower/log.jsonl。
航班以「worktree 絕對路徑＋分支」對應，同一 worktree 只有一班 flying。
"""
import argparse
import hashlib
import json
import os
import re
import secrets
import socket
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCHEMA = 1
REQUIRED_KEYS = ("id", "branch", "worktree", "state")
LOST_AFTER = timedelta(minutes=30)
ID_RE = re.compile(r"\d{8}-\d{4}-[0-9a-f]{4}")
DEFAULT_SHARED = [
    "docs/feature.md", "docs/roadmap.md", "docs/todo.md",
    "FEATURES.md", "ROADMAP.md", "TODO.md", "**/CHANGELOG.md",
]


def _git(cwd, *args):
    try:
        r = subprocess.run(["git", *args], cwd=cwd, capture_output=True,
                           text=True, encoding="utf-8")
    except (OSError, ValueError):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def host_hash():
    return hashlib.sha256(socket.gethostname().encode("utf-8")).hexdigest()[:8]


def tower_dir(cwd):
    """git common dir 下的 tower/；非 repo 回 None。"""
    common = _git(cwd, "rev-parse", "--git-common-dir")
    if not common:
        return None
    p = Path(common)
    if not p.is_absolute():
        p = Path(cwd) / p
    return p.resolve() / "tower"


def worktree_root(cwd):
    top = _git(cwd, "rev-parse", "--show-toplevel")
    return str(Path(top).resolve()) if top else None


def locate(cwd):
    """純檔案操作定位（不開 git 子程序）：回 (worktree 根, gitdir, tower 目錄, 目前分支)；非 repo 回 None。

    向上找 .git：目錄＝一般 repo；檔案＝worktree／submodule，讀 gitdir: 並以 commondir 找共用 git 目錄。
    """
    p = Path(os.path.realpath(cwd))
    for d in (p, *p.parents):
        dotgit = d / ".git"
        if dotgit.is_dir():
            gitdir = dotgit
            break
        if dotgit.is_file():
            line = dotgit.read_text(encoding="utf-8").strip()
            if not line.startswith("gitdir:"):
                return None
            gitdir = Path(os.path.realpath(d / line[len("gitdir:"):].strip()))
            break
    else:
        return None
    common = gitdir
    try:
        common = Path(os.path.realpath(
            gitdir / (gitdir / "commondir").read_text(encoding="utf-8").strip()))
    except OSError:
        pass
    try:
        head = (gitdir / "HEAD").read_text(encoding="utf-8").strip()
    except OSError:
        head = ""
    branch = head[len("ref: refs/heads/"):] if head.startswith("ref: refs/heads/") else ""
    return str(d), gitdir, common / "tower", branch


def current_branch(cwd):
    return _git(cwd, "rev-parse", "--abbrev-ref", "HEAD") or ""


def _flights_dir(tdir):
    return Path(tdir) / "flights"


def _atomic_write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def load_flights(tdir):
    """讀所有航班；損毀檔略過並寫 stderr。"""
    out = []
    d = _flights_dir(tdir)
    if not d.is_dir():
        return out
    for p in sorted(d.glob("*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (ValueError, OSError) as e:
            print(f"tower: 略過損毀航班檔 {p.name}: {e}", file=sys.stderr)
            continue
        if not isinstance(data, dict):
            print(f"tower: 略過損毀航班檔 {p.name}: 不是 JSON 物件", file=sys.stderr)
            continue
        missing = [k for k in REQUIRED_KEYS if k not in data]
        if missing:
            print(f"tower: 略過航班檔 {p.name}: 缺欄位 {','.join(missing)}",
                  file=sys.stderr)
            continue
        out.append(data)
    return out


def save_flight(tdir, f):
    _atomic_write(_flights_dir(tdir) / f"{f['id']}.json",
                  json.dumps(f, ensure_ascii=False, indent=2) + "\n")


def find_flight(tdir, worktree):
    for f in load_flights(tdir):
        if f.get("state") == "flying" and f.get("worktree") == worktree:
            return f
    return None


def log_event(tdir, kind, **fields):
    p = Path(tdir) / "log.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    rec = {"at": now_iso(), "kind": kind, **fields}
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def new_id():
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M-") + secrets.token_hex(2)


def shared_globs(repo_root):
    """預設共用跑道＋專案 .plugharbor/tower.yml 的 shared: 清單。"""
    globs = list(DEFAULT_SHARED)
    try:
        lines = (Path(repo_root) / ".plugharbor" / "tower.yml").read_text(
            encoding="utf-8").splitlines()
    except OSError:
        return globs
    in_shared = False
    for line in lines:
        if re.match(r"^shared\s*:", line):
            in_shared = True
        elif in_shared:
            m = re.match(r"^\s*-\s+(.+?)\s*$", line)
            if m:
                globs.append(m.group(1).strip("\"'"))
            elif line.strip() and not line.lstrip().startswith("#"):
                in_shared = False
    return globs


def _glob_re(glob):
    out, i = [], 0
    while i < len(glob):
        if glob.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif glob.startswith("**", i):
            out.append(".*")
            i += 2
        elif glob[i] == "*":
            out.append("[^/]*")
            i += 1
        else:
            out.append(re.escape(glob[i]))
            i += 1
    return "".join(out)


def match(path, glob):
    if "*" not in glob:
        d = glob.rstrip("/")
        return path == d or path.startswith(d + "/")
    return re.fullmatch(_glob_re(glob), path) is not None


def is_lost(f, now):
    try:
        beat = datetime.fromisoformat(f["beat"])
    except (KeyError, ValueError, TypeError):
        return True
    if beat.tzinfo is None:
        beat = beat.replace(tzinfo=timezone.utc)
    if not os.path.isdir(f.get("worktree") or ""):
        return True
    return now - beat > LOST_AFTER and not f.get("proxy")  # 代管航班（subagent 不送心跳）只看 worktree 還在不在


def _path_hits(a, b):
    return a == b or match(b, a) or match(a, b)


def overlaps(me, others, shared):
    out = []
    mine = list(me.get("paths", [])) + list(me.get("touched", []))
    for o in others:
        detail = []
        for k in ("segment", "feature", "ticket"):
            v = (me.get("work") or {}).get(k)
            if v and v == (o.get("work") or {}).get(k):
                detail.append(f"{k}:{v}")
        if detail:
            out.append({"flight": o["id"], "goal": o.get("goal", ""),
                        "kind": "work", "detail": detail})
            continue
        theirs = list(o.get("paths", [])) + list(o.get("touched", []))
        hits = []
        for t in theirs:
            if any(match(t, g) for g in shared):
                continue
            if any(not any(match(m, g) for g in shared) and _path_hits(m, t)
                   for m in mine) and t not in hits:
                hits.append(t)
        if hits:
            out.append({"flight": o["id"], "goal": o.get("goal", ""),
                        "kind": "path", "detail": hits})
    return out


def _live_others(tdir, flight):
    now = datetime.now(timezone.utc)
    return [f for f in load_flights(tdir)
            if f.get("state") == "flying" and f.get("id") != flight["id"]
            and f.get("worktree") != flight.get("worktree") and not is_lost(f, now)]


def compute_overlaps(tdir, flight):
    return overlaps(flight, _live_others(tdir, flight),
                    shared_globs(flight.get("worktree") or "."))


def feature_warnings(tdir, flight):
    feat = (flight.get("work") or {}).get("feature")
    if not feat:
        return []
    try:
        lines = (Path(flight["worktree"]) / "docs" / "feature.md").read_text(
            encoding="utf-8").splitlines()
    except OSError:
        return []
    if any((o.get("work") or {}).get("feature") == feat
           for o in _live_others(tdir, flight)):
        return []
    for line in lines:
        if feat in line and re.match(r"\s*- \[ \]", line) and "🚧" in line:
            return [f"feature.md 中「{feat}」已是 🚧 但沒有活航班，"
                    "可能別台機器或舊 session 在做"]
    return []


def default_branch(repo):
    ref = _git(repo, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    if ref and ref.startswith("origin/"):
        return ref[len("origin/"):]
    for name in ("main", "master"):
        if _git(repo, "rev-parse", "--verify", "--quiet", f"refs/heads/{name}"):
            return name
    return "main"


def _base_ref(wt, branch):
    """本機 origin/<預設> 與 <預設> 中較新者（不聯網）。"""
    refs = [r for r in (f"origin/{branch}", branch)
            if _git(wt, "rev-parse", "--verify", "--quiet", f"{r}^{{commit}}")]
    if not refs:
        return None
    best = refs[0]
    for r in refs[1:]:
        if _git(wt, "merge-base", "--is-ancestor", best, r) is not None:
            best = r
    return best


def _diff_base(wt, branch):
    """改動比對基準：在預設分支上用 origin/<預設>，否則用 _base_ref。"""
    if current_branch(wt) == branch:
        remote = f"origin/{branch}"
        if _git(wt, "rev-parse", "--verify", "--quiet", f"{remote}^{{commit}}"):
            return remote
    return _base_ref(wt, branch)


def _is_ancestor(wt, a, b):
    # fail-open：git 無法執行時視為已包含，不因塔台異常擋住落地
    try:
        r = subprocess.run(["git", "merge-base", "--is-ancestor", a, b], cwd=wt,
                           capture_output=True)
    except (OSError, ValueError):
        return True
    return r.returncode != 1


def actual_changes(worktree, base_branch):
    """相對 merge-base 的實際改動：已 commit、工作樹、暫存、未追蹤。"""
    wt = str(worktree)
    if not os.path.isdir(wt):
        return set()
    base = _git(wt, "merge-base", "HEAD", base_branch) if base_branch else None
    out = set()
    for args in (("diff", "--name-only", base or "HEAD"),
                 ("diff", "--name-only"),
                 ("diff", "--name-only", "--cached"),
                 ("ls-files", "--others", "--exclude-standard")):
        text = _git(wt, *args)
        if text:
            out.update(x for x in text.splitlines() if x)
    return out


def _in_scope(path, paths):
    return any(path == p or match(path, p) or match(p, path) for p in paths)


def land_check(tdir, me):
    wt = me.get("worktree") or "."
    res = {"code": 0, "scope_extra": [], "collisions": [], "behind": False,
           "warnings": []}
    try:
        branch = default_branch(wt)
        base = _base_ref(wt, branch)
        shared = shared_globs(wt)
        mine = {f for f in actual_changes(wt, _diff_base(wt, branch)) if not any(match(f, g) for g in shared)}
        extra = sorted(f for f in mine if not _in_scope(f, me.get("paths", [])))
        if any(o.get("kind") == "scope" for o in me.get("overrides", [])):
            extra = []
        res["scope_extra"] = extra
        res["behind"] = bool(base) and not _is_ancestor(wt, base, "HEAD")
        now = datetime.now(timezone.utc)
        for o in load_flights(tdir):
            if (o.get("state") != "flying" or o.get("id") == me.get("id")
                    or o.get("worktree") == me.get("worktree")):
                continue  # 同 worktree 的另一班（takeoff 無鎖造成）不算他班
            if is_lost(o, now):
                hit = sorted(set(o.get("touched", [])) & mine)
                if not hit and os.path.isdir(o["worktree"]):
                    ob = _diff_base(o["worktree"], branch)
                    hit = sorted(actual_changes(o["worktree"], ob) & mine)
                if hit:
                    res["warnings"].append(
                        f"失聯航班 {o['id']} 也碰過：{', '.join(hit)}")
                continue
            ob = _diff_base(o["worktree"], branch)
            theirs = actual_changes(o["worktree"], ob)
            hit = sorted(mine & theirs)
            if hit:
                res["collisions"].append(
                    {"flight": o["id"], "goal": o.get("goal", ""), "files": hit})
        res["warnings"] += feature_warnings(tdir, me)
        res["warnings"] += _feature_unchecked(me)
    except Exception as e:  # fail-safe：塔台不可因異常狀態擋住落地
        res["warnings"].append(f"land-check 內部錯誤（已略過）：{e}")
    res["code"] = (11 if res["collisions"] else 12 if res["behind"]
                   else 10 if res["scope_extra"] else 0)
    return res


def _feature_unchecked(flight):
    feat = (flight.get("work") or {}).get("feature")
    if not feat:
        return []
    try:
        lines = (Path(flight["worktree"]) / "docs" / "feature.md").read_text(
            encoding="utf-8").splitlines()
    except OSError:
        return []
    for line in lines:
        if feat in line and re.match(r"\s*- \[ \]", line):
            return [f"feature.md 中「{feat}」還沒勾成 [x]，落地前記得更新"]
    return []


def _rel(cwd, root, name):
    p = Path(name)
    if not p.is_absolute():
        p = Path(cwd) / p
    try:
        return p.resolve().relative_to(root).as_posix()
    except ValueError:
        return p.as_posix()


def _posix(paths):
    return [p.replace("\\", "/") for p in paths]


def _still_flying(tdir, f):
    """寫入前重讀：航班檔已被 release 或不是 flying 就不寫，避免復活或改回 flying。"""
    try:
        cur = json.loads((_flights_dir(tdir) / f"{f['id']}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cur = None
    if isinstance(cur, dict) and cur.get("state") == "flying":
        return True
    print(f"tower: 航班 {f['id']} 已不在飛（released 或非 flying），未寫入", file=sys.stderr)
    return False


def incoming_changes(wt, refs):
    """merge／rebase 要帶進來的檔：各 ref 相對 HEAD merge-base 的改動（非 ref 的字串略過）。"""
    out = set()
    for ref in refs:
        base = _git(wt, "merge-base", "HEAD", ref)
        text = _git(wt, "diff", "--name-only", base, ref) if base else None
        if text:
            out.update(x for x in text.splitlines() if x)
    return out


# ---- CLI ----

def _context(args):
    cwd = os.getcwd()
    tdir = tower_dir(cwd)
    if tdir is None:
        print("tower: 不在 git repo 內", file=sys.stderr)
        sys.exit(1)
    return cwd, tdir, worktree_root(cwd)


def _target(args, tdir, root):
    fid = getattr(args, "id", None)
    if fid:
        if not ID_RE.fullmatch(fid):
            print(f"tower: --id 格式不符 {fid!r}", file=sys.stderr)
            sys.exit(2)
        p = _flights_dir(tdir) / f"{fid}.json"
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError
            return data
        except (OSError, ValueError):
            print(f"tower: 找不到航班 {fid}", file=sys.stderr)
            sys.exit(1)
    f = find_flight(tdir, root)
    if f is None:
        print("tower: 此 worktree 沒有 flying 航班", file=sys.stderr)
        sys.exit(1)
    return f


def cmd_takeoff(args):
    cwd, tdir, root = _context(args)
    existing = find_flight(tdir, root)
    if existing:
        print(f"tower: 此 worktree 已有航班 {existing['id']}（{existing['goal']}）",
              file=sys.stderr)
        print(existing["id"])
        return 2
    t = now_iso()
    f = {
        "id": new_id(), "schema": SCHEMA, "goal": args.goal,
        "work": {"segment": args.segment, "feature": args.feature, "ticket": args.ticket},
        "paths": _posix(args.paths), "touched": [],
        "branch": current_branch(cwd), "worktree": root,
        "session": args.session or os.environ.get("CLAUDE_SESSION_ID", ""),
        "cli": args.cli, "host": host_hash(),
        "mode": args.mode, "started": t, "beat": t,
        "overrides": [], "state": "flying", "proxy": bool(args.proxy),
    }
    save_flight(tdir, f)
    log_event(tdir, "takeoff", id=f["id"], goal=f["goal"])
    print(json.dumps({"id": f["id"], "overlaps": compute_overlaps(tdir, f),
                      "warnings": feature_warnings(tdir, f)}, ensure_ascii=False))
    return 0


def cmd_amend(args):
    _, tdir, root = _context(args)
    f = _target(args, tdir, root)
    if args.goal:
        f["goal"] = args.goal
    if args.paths:
        f["paths"] = _posix(args.paths)
    f["beat"] = now_iso()
    if not _still_flying(tdir, f):
        return 1
    save_flight(tdir, f)
    log_event(tdir, "amend", id=f["id"])
    return 0


def cmd_beat(args):
    cwd, tdir, root = _context(args)
    f = _target(args, tdir, root)
    for name in args.touched or []:
        rel = _rel(cwd, Path(root), name.replace("\\", "/"))
        if rel not in f["touched"]:
            f["touched"].append(rel)
    f["beat"] = now_iso()
    if not _still_flying(tdir, f):
        return 1
    save_flight(tdir, f)
    print(json.dumps({"overlaps": compute_overlaps(tdir, f)}, ensure_ascii=False))
    return 0


def cmd_radar(args):
    _, tdir, _root = _context(args)
    flights = load_flights(tdir)
    now = datetime.now(timezone.utc)
    for f in flights:
        if f.get("state") == "flying" and is_lost(f, now):
            f["state"] = "lost"
    if args.json:
        print(json.dumps(flights, ensure_ascii=False, indent=2))
    else:
        for f in flights:
            tag = f"{f['state']}{'*' if f.get('proxy') else ''}"
            print(f"{f['id']}  {tag:<7} {f['branch']}  {f['goal']}")
    return 0


def cmd_override(args):
    _, tdir, root = _context(args)
    f = _target(args, tdir, root)
    f["overrides"].append({"at": now_iso(), "kind": args.kind, "reason": args.reason})
    if not _still_flying(tdir, f):
        return 1
    save_flight(tdir, f)
    log_event(tdir, "override", id=f["id"], reason=args.reason)
    return 0


def cmd_landed(args):
    _, tdir, root = _context(args)
    f = _target(args, tdir, root)
    f["state"] = "landed"
    save_flight(tdir, f)
    log_event(tdir, "landed", id=f["id"])
    return 0


def cmd_land_check(args):
    _, tdir, root = _context(args)
    f = _target(args, tdir, root)
    res = land_check(tdir, f)
    print(json.dumps(res, ensure_ascii=False))
    return res["code"]


def cmd_release(args):
    _, tdir, root = _context(args)
    f = _target(args, tdir, root)
    try:
        (_flights_dir(tdir) / f"{f['id']}.json").unlink()
    except FileNotFoundError:
        pass
    log_event(tdir, "release", id=f["id"])
    return 0


def build_parser():
    ap = argparse.ArgumentParser(prog="tower.py")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add(name, fn, with_id=True):
        p = sub.add_parser(name)
        if with_id:
            p.add_argument("--id")
        p.set_defaults(fn=fn)
        return p

    p = add("takeoff", cmd_takeoff, with_id=False)
    p.add_argument("--goal", required=True)
    p.add_argument("--paths", action="extend", nargs="+", required=True)
    p.add_argument("--segment")
    p.add_argument("--feature")
    p.add_argument("--ticket")
    p.add_argument("--mode", default="")
    p.add_argument("--session")
    p.add_argument("--cli", default="claude")
    p.add_argument("--proxy", action="store_true")
    p = add("amend", cmd_amend)
    p.add_argument("--goal")
    p.add_argument("--paths", action="extend", nargs="+")
    p = add("beat", cmd_beat)
    p.add_argument("--touched", nargs="+")
    p = add("radar", cmd_radar, with_id=False)
    p.add_argument("--json", action="store_true")
    p = add("override", cmd_override)
    p.add_argument("--kind", required=True)
    p.add_argument("--reason", required=True)
    add("landed", cmd_landed)
    add("land-check", cmd_land_check)
    add("release", cmd_release)
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
