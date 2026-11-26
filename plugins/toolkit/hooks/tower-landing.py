#!/usr/bin/env python3
"""PreToolUse(Bash) hook：指令要把東西落到預設分支前，先做塔台 land-check。

觸發：預設分支上的 git commit／merge／rebase；git push 的目標是預設分支（或在預設分支上不帶 refspec）。
結果：0 放行（有警告則附 additionalContext）；10 超出申報範圍、12 落後預設分支 → deny 並寫明解法；
11 與他班實際改動撞檔 → ask，無人值守（航班 mode=unattended 或 AGENT_DISPATCH_UNATTENDED=1）→ deny 要求排隊。
此 worktree 沒有 flying 航班、非 git repo、任何例外 → 靜默 exit 0（fail-open）。
例外：merge／rebase 的目標 ref 或 push 的來源 ref 對到別班 flying 航班的分支時，不論本 worktree 有無航班，
都改用那班航班核對（如主 checkout merge feat/x）。
預設分支上、以本 worktree 航班 merge／rebase「遠端預設分支或不指定 ref」視為同步，不套用「超出範圍」「落後」；
併入其他本地分支則視為落地，並把該分支帶進來的檔也比對申報範圍。指令中的 `git checkout|switch <既有分支>` 會模擬切換後的分支。

指令解析是字串層級的近似，已知限制（不處理）：引號內的 `git commit` 字樣會誤判為指令；
`env`／`sudo`／`bash -c "..."`／`xargs` 包裝、shell 別名、子 shell 離開後 `cd` 的還原；
`git pull`（會 merge）與 `git cherry-pick` 不在觸發範圍。`cd` 是跨片段累積的（含子 shell 內的 cd）。
"""
import json
import os
import re
import shlex
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN / "skills" / "tower" / "scripts"))
SYNC_ONLY = {"--abort", "--continue", "--skip", "--quit"}


def git_calls(command, cwd):
    """從指令字串取出 (子指令, 參數, 工作目錄) 清單；只認以 git 起頭的片段。

    工作目錄跨片段追蹤 `cd <dir>`（含 ~ 展開、相對路徑以目前目錄為基準），`git -C <dir>` 疊加在其上。
    """
    out = []
    where = cwd
    for seg in re.split(r"&&|\|\||;|\||\n", command):
        seg = seg.strip()
        if seg.endswith(")") and "(" not in seg:
            seg = seg.rstrip(")")
        try:
            toks = shlex.split(seg.lstrip("("))
        except ValueError:
            toks = seg.lstrip("(").split()
        while toks and re.fullmatch(r"\w+=\S*", toks[0]):
            toks.pop(0)
        if not toks:
            continue
        if toks[0] == "cd":
            if len(toks) > 1 and toks[1] != "-":
                where = os.path.join(where, os.path.expanduser(toks[1]))
            continue
        if toks[0] != "git":
            continue
        i, here = 1, where
        while i < len(toks) and toks[i].startswith("-"):
            if toks[i] in ("-C", "-c", "--git-dir", "--work-tree") and i + 1 < len(toks):
                if toks[i] == "-C":
                    here = os.path.join(here, os.path.expanduser(toks[i + 1]))
                i += 1
            i += 1
        if i < len(toks):
            out.append((toks[i], toks[i + 1:], here))
    return out


VALUE_OPTS = {
    "merge": {"-m", "-F", "-X", "-s", "--message", "--file", "--strategy", "--strategy-option"},
    "rebase": {"--onto", "-s", "-X", "-x", "--strategy", "--strategy-option", "--exec"},
    "push": {"-o", "--push-option", "--repo", "--receive-pack", "--exec"},
}


def positionals(sub, args):
    """去掉選項與帶值選項的值（`-m sync`、`-X theirs`、`--onto x`）後的位置參數；`-m=x`、`-mx` 本來就是單一 token。"""
    out, skip = [], False
    for a in args:
        if skip:
            skip = False
        elif a in VALUE_OPTS.get(sub, ()):
            skip = True
        elif not a.startswith("-"):
            out.append(a)
    return out


def is_landing(sub, args, branch, default):
    if sub == "commit":
        return branch == default
    if sub in ("merge", "rebase"):
        return branch == default and not SYNC_ONLY & set(args)
    if sub == "push":
        refspecs = positionals(sub, args)[1:]
        if not refspecs:
            return branch == default
        for r in refspecs:
            dst = r.split(":")[-1].lstrip("+")
            dst = dst[len("refs/heads/"):] if dst.startswith("refs/heads/") else dst
            if (branch if dst == "HEAD" else dst) == default:
                return True
    return False


def source_refs(sub, args):
    """merge／rebase 的目標 ref、push 的來源 ref（用來對應到某班航班的分支）。"""
    if sub not in ("merge", "rebase", "push"):
        return []
    pos = positionals(sub, args)
    if sub == "push":
        pos = [r.split(":")[0].lstrip("+") for r in pos[1:]]
    return [r[len("refs/heads/"):] if r.startswith("refs/heads/") else r for r in pos]


def decision(kind, reason):
    return {"hookEventName": "PreToolUse", "permissionDecision": kind, "permissionDecisionReason": reason}


def main():
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stderr = open(os.devnull, "w")
    import tower
    payload = json.load(sys.stdin)
    if payload.get("tool_name") != "Bash":
        return
    cwd = payload.get("cwd") or os.getcwd()
    calls = git_calls((payload.get("tool_input") or {}).get("command") or "", cwd)
    simulated = {}  # worktree 根 → 指令中 checkout／switch 之後的分支
    for sub, args, where in calls:
        if sub not in ("checkout", "switch", "commit", "merge", "rebase", "push"):
            continue
        loc = tower.locate(where)
        if loc is None:
            continue
        root, _gitdir, tdir, branch = loc
        if sub in ("checkout", "switch"):
            target = switch_target(args, tdir.parent)
            if target:
                simulated[root] = target
            continue
        branch = simulated.get(root, branch)
        me = tower.find_flight(tdir, root)
        refs = source_refs(sub, args)
        if me is None and not refs:
            continue
        default = tower.default_branch(root)
        if not is_landing(sub, args, branch, default):
            continue
        # 被併入／推送的分支若有別班 flying 航班（非自己、非預設分支），改用那班核對
        target = next((f for f in tower.load_flights(tdir)
                       if f.get("state") == "flying" and f.get("branch") in refs
                       and f.get("branch") != default and f.get("id") != (me or {}).get("id")), None)
        via_target = target is not None
        if via_target:
            me = target
        elif me is None:
            continue
        res = tower.land_check(tdir, me)
        # 在預設分支上 merge／rebase 只同步遠端預設分支（或沒指定 ref）才算同步；其他本地分支算落地
        sync = (sub in ("merge", "rebase") and branch == default and not via_target
                and set(refs) <= sync_refs(default))
        if sub in ("merge", "rebase") and not sync and not via_target:
            add_incoming_scope(tower, me, root, refs, res)
        out = judge(me, res, default, sync, via_target)
        if out:
            sys.stdout.buffer.write(json.dumps({"hookSpecificOutput": out}, ensure_ascii=False).encode("utf-8"))
        return


def sync_refs(default):
    return {default, f"origin/{default}", f"remotes/origin/{default}", "FETCH_HEAD", "@{u}", "@{upstream}"}


def switch_target(args, common):
    """`git checkout|switch <既有本地分支>` 的分支名；新建分支、檔案路徑、`.`、`--` 都不算。"""
    pos = [a for a in args if not a.startswith("-")]
    if len(pos) != 1 or "--" in args or any(a in ("-b", "-B", "-c", "-C", "--orphan", "-d", "--detach")
                                           for a in args):
        return None
    name = pos[0]
    if (Path(common) / "refs" / "heads" / name).is_file():
        return name
    try:
        packed = (Path(common) / "packed-refs").read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    return name if any(l.endswith(f" refs/heads/{name}") for l in packed) else None


def add_incoming_scope(tower, me, root, refs, res):
    """merge／rebase 要帶進來的檔也要在申報範圍內（工作樹此刻還看不到它們）。"""
    if any(o.get("kind") == "scope" for o in me.get("overrides", [])):
        return
    shared = tower.shared_globs(root)
    extra = sorted(f for f in tower.incoming_changes(root, refs)
                   if not any(tower.match(f, g) for g in shared)
                   and not tower._in_scope(f, me.get("paths", [])))
    if extra:
        res["scope_extra"] = sorted(set(res["scope_extra"]) | set(extra))
        if res["code"] == 0:
            res["code"] = 10


def judge(me, res, default, sync, via_target):
    code = res["code"]
    if sync and code in (10, 12):
        code = 0  # 同步不算「落後」，也不算超出範圍
    warn = "；".join(res["warnings"])
    note = f"（另請留意：{warn}）" if warn else ""
    fid = me["id"]
    if code == 0:
        return {"hookEventName": "PreToolUse", "additionalContext": f"塔台：{warn}"} if warn else None
    if code == 10:
        cli = f'python3 "{PLUGIN / "skills" / "tower" / "scripts" / "tower.py"}"'
        return decision("deny", (
            f"塔台：航班 {fid} 的改動超出申報範圍：{', '.join(res['scope_extra'])}。"
            f"確定要一併落地：先執行 {cli} override --kind scope --reason <原因>{f' --id {fid}' if via_target else ''} 再重試；"
            f"否則先 amend 範圍或把多的檔案拆走。{note}"))
    if code == 12:
        return decision("deny", (
            f"塔台：{default} 已前進，目前分支落後。先 rebase 到最新 {default}"
            f"（git fetch && git rebase origin/{default}）並重跑測試後再重試。{note}"))
    hits = "；".join(f"航班 {c['flight']}（{c['goal']}）改了 {', '.join(c['files'])}" for c in res["collisions"])
    ids = "、".join(c["flight"] for c in res["collisions"])
    unattended = me.get("mode") == "unattended" or os.environ.get("AGENT_DISPATCH_UNATTENDED") == "1"
    if unattended:
        return decision("deny", (
            f"塔台：航班 {fid} 與他班撞檔：{hits}。無人值守不能詢問人，請排隊："
            f"改做別的工作單元，等航班 {ids} landed 後再 rebase 並落地。"
            f"對方是同一主控的平行線（換過 session）就 override --kind collision 放行。{note}"))
    return decision("ask", f"塔台：航班 {fid} 與他班撞檔：{hits}。確認要現在落地嗎？{note}")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
