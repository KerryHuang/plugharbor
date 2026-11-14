#!/usr/bin/env python3
"""雙軌對帳：repo 的功能清單與 todo（為準）對 GitHub Issues（與看板）。

用法：
  python3 reconcile.py --repo <owner/repo> [--feature docs/feature.md] [--todo docs/todo.md]
                       [--exclude-label test] [--log <jsonl>]
                       [--issues-json F] [--parents-json F] [--board-json F]
  --issues-json／--parents-json／--board-json 給了就不打 gh（測試或離線用）。
  parent 預設取 issue 的原生 parent 欄位，--parents-json 可覆寫（內文慣例的 repo 用）；沒設 ticket.project 且沒給 --board-json 時不比對看板。
退出碼：0 差異 0；1 有差異；3 查詢可能截斷（結果不可用）。
比對規則見 ticket-ops 的 SKILL.md「對帳」與 plugin 根的 references/feature-checklist.md「同步票」。
"""
import argparse
import datetime
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

LIMIT = 1000
STAGES = ("backlog", "todo", "in-progress", "in-review", "done", "canceled")
CLOSED = ("done", "canceled")


def load_checklist():
    p = Path(__file__).resolve().parents[3] / "scripts" / "feature_checklist.py"
    spec = importlib.util.spec_from_file_location("feature_checklist", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def labels_of(i):
    return {x["name"] for x in i.get("labels", [])}


def gh_stage(i):
    if i["state"] != "OPEN":
        return "done" if i.get("stateReason") == "COMPLETED" else "canceled"
    st = [x[6:] for x in labels_of(i) if x.startswith("stage:")]
    return st[0] if st else None


def parents_from_issues(issues):
    """gh issue list --json …,parent 的原生 parent 欄位 → {票號: 父票號或 None}；沒有任何一筆帶 parent 欄位回 None。"""
    if not any("parent" in i for i in issues):
        return None
    return {i["number"]: (i.get("parent") or {}).get("number") for i in issues}


def same_stage(expected, actual):
    return actual == expected or (expected == "in-progress" and actual == "in-review")


def reconcile(items, todos, issues, board=None, parents=None, options=None, exclude_label="test"):
    by_num = {i["number"]: i for i in issues}
    diffs = []

    def diff(kind, ref, detail):
        diffs.append({"kind": kind, "ref": ref, "detail": detail})

    counts = {"feature": {s: [0, 0] for s in STAGES if s != "in-review"},
              "parent": {"open": [0, 0], "closed": [0, 0]}, "todo": {"open": [0, 0], "closed": [0, 0]}}
    referenced = set()

    def check_ref(n, name):
        if n not in by_num:
            diff("missing_issue", f"#{n}", f"{name}：票不存在（號碼可能是 PR 或打錯）")
            return None
        return by_num[n]

    # feature 子票
    for it in items:
        name = it["name"]
        if it["stage"] == "unclassified":
            diff("unclassified", name, "沒帶 🚧／📋／💡，先補標記")
            continue
        counts["feature"][it["stage"]][0] += 1
        if it["ticket"] is None:
            diff("missing_ticket", name, "清單項目沒有行尾 #n")
            continue
        referenced.add(it["ticket"])
        i = check_ref(it["ticket"], name)
        if i is None:
            continue
        act = gh_stage(i)
        if act in counts["feature"] or act == "in-review":
            counts["feature"]["in-progress" if act == "in-review" else act][1] += 1
        if not same_stage(it["stage"], act):
            diff("stage", f"#{it['ticket']}", f"{name}：清單 {it['stage']}、票 {act}")
        if parents is not None and parents.get(it["ticket"]) != it["section_ticket"]:
            diff("parent", f"#{it['ticket']}",
                 f"{name}：所在節的票 #{it['section_ticket']}、票的 parent #{parents.get(it['ticket'])}")

    # 父票：節內有未關子票就該開著
    sections = {}
    for it in items:
        if it["stage"] != "unclassified":
            sections.setdefault((it["section"], it["section_ticket"]), []).append(it["stage"])
    for (sec, n), stages in sections.items():
        if all(s == "canceled" for s in stages) and n is None:
            continue  # 集中放「不做」的節不開父票
        if n is None:
            diff("missing_ticket", sec or "(無節)", "節標題沒有行尾 #n")
            continue
        referenced.add(n)
        want = "closed" if all(s in CLOSED for s in stages) else "open"
        counts["parent"][want][0] += 1
        i = check_ref(n, f"節「{sec}」")
        if i is None:
            continue
        got = "open" if i["state"] == "OPEN" else "closed"
        counts["parent"][got][1] += 1
        if got != want:
            diff("stage", f"#{n}", f"節「{sec}」的父票應為 {want}、實際 {got}")

    # todo 票
    for t in todos:
        counts["todo"]["open"][0] += 1
        if t["ticket"] is None:
            diff("missing_ticket", t["text"], "todo 行沒有行尾 #n")
            continue
        referenced.add(t["ticket"])
        i = check_ref(t["ticket"], t["text"])
        if i is None:
            continue
        counts["todo"]["open" if i["state"] == "OPEN" else "closed"][1] += 1
        if i["state"] != "OPEN":
            diff("stage", f"#{t['ticket']}", f"{t['text']}：todo 還在、票已關")
        if "todo" not in labels_of(i):
            diff("stage", f"#{t['ticket']}", f"{t['text']}：票缺 todo label")

    # 沒被引用的票
    excluded = {"test": 0, "todo_closed": 0, "triage": 0, "closed_unreferenced": 0}
    for i in issues:
        n, labs = i["number"], labels_of(i)
        if i.get("title", "").startswith("[測試]") or exclude_label in labs:
            excluded["test"] += 1
            continue
        if n in referenced:
            continue
        if i["state"] != "OPEN":
            excluded["todo_closed" if "todo" in labs else "closed_unreferenced"] += 1
            if "todo" in labs:
                counts["todo"]["closed"][1] += 1
        elif "triage" in labs or gh_stage(i) is None:
            excluded["triage"] += 1
        else:
            diff("orphan", f"#{n}", f"{i.get('title', '')}：開著、有 stage label，卻沒被清單或 todo 引用")

    # 看板
    if board is not None and options:
        for n in sorted(referenced):
            if n not in by_num:
                continue
            want = options.get(gh_stage(by_num[n]) or "")
            if board.get(n) != want:
                diff("board", f"#{n}", f"看板 Status {board.get(n)!r}、依 label／開關應為 {want!r}")

    return {"counts": counts, "diffs": diffs, "excluded": excluded, "diff_total": len(diffs)}


def gh_json(args):
    r = subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8")
    if r.returncode:
        raise SystemExit(f"gh {' '.join(args)} 失敗：{r.stderr.strip()}")
    return json.loads(r.stdout)


def load_project_cfg():
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
        from config import load_config  # noqa: E402
        return (load_config(Path.cwd(), "ticket.states").get("ticket") or {}).get("project")
    except Exception as e:  # 沒設定就不比對看板，但要說出來
        print(f"讀不到 ticket.project（{e}），不比對看板", file=sys.stderr)
        return None


def fetch_board(proj):
    data = gh_json(["project", "item-list", str(proj["number"]), "--owner", proj["owner"],
                    "--format", "json", "--limit", str(LIMIT)])
    field = proj.get("field", "Status")
    key = field[:1].lower() + field[1:]
    return {it["content"]["number"]: it.get(key) for it in data.get("items", [])
            if it.get("content", {}).get("number")}


def render(r, repo, notes):
    out = [f"# 對帳 {repo}（{datetime.date.today().isoformat()}）", ""]
    for group, rows in r["counts"].items():
        out.append(f"{group}：" + "、".join(f"{k} {a}/{b}" for k, (a, b) in rows.items()) + "（repo/GitHub）")
    out.append("不計入：" + "、".join(f"{k} {v}" for k, v in r["excluded"].items()))
    out += notes + [""]
    out += [f"- [{d['kind']}] {d['ref']} {d['detail']}" for d in r["diffs"]] or ["（無逐項差異）"]
    out += ["", f"差異 {r['diff_total']}"]
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", required=True)
    ap.add_argument("--feature", type=Path, default=Path("docs/feature.md"))
    ap.add_argument("--todo", type=Path, default=Path("docs/todo.md"))
    ap.add_argument("--exclude-label", default="test")
    ap.add_argument("--log", type=Path)
    ap.add_argument("--issues-json", type=Path)
    ap.add_argument("--parents-json", type=Path)
    ap.add_argument("--board-json", type=Path)
    a = ap.parse_args(argv)
    read = lambda p: json.loads(p.read_text(encoding="utf-8"))  # noqa: E731
    fc = load_checklist()
    items = fc.tickets(a.feature.read_text(encoding="utf-8"))
    todos = fc.todo_items(a.todo.read_text(encoding="utf-8")) if a.todo.is_file() else []
    issues = read(a.issues_json) if a.issues_json else gh_json(
        ["issue", "list", "--repo", a.repo, "--state", "all", "--limit", str(LIMIT),
         "--json", "number,state,stateReason,labels,title,parent"])
    notes = []
    if len(issues) >= LIMIT:
        print(f"query 完整性：可能截斷（取得 {len(issues)} 筆，已達上限），不對帳")
        return 3
    parents = ({int(k): v for k, v in read(a.parents_json).items()} if a.parents_json
               else parents_from_issues(issues))
    if parents is None:
        notes.append("未比對 parent（issue 沒有 parent 欄位，也沒給 --parents-json）")
    proj = None if a.board_json else load_project_cfg()
    board = {int(k): v for k, v in read(a.board_json).items()} if a.board_json else (
        fetch_board(proj) if proj else None)
    r = reconcile(items, todos, issues, board=board, parents=parents,
                  options=(proj or {}).get("options"), exclude_label=a.exclude_label)
    print(render(r, a.repo, notes))
    if a.log:
        with a.log.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"date": datetime.date.today().isoformat(), "repo": a.repo,
                                "counts": r["counts"], "diff_total": r["diff_total"]}, ensure_ascii=False) + "\n")
    return 1 if r["diff_total"] else 0


if __name__ == "__main__":
    sys.exit(main())
