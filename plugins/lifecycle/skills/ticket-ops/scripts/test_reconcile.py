#!/usr/bin/env python3
"""reconcile 的測試。直接執行：python3 test_reconcile.py"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reconcile as rc  # noqa: E402

FEATURE = """# 清單

## 模組 A #1

- [x] 甲 #3
- [ ] 🚧 乙 #4

## 模組 B #2

- [ ] 📋 丙 #5
- [ ] 💡 丁 #6

## 不做

- [-] 戊 #7
"""
TODO = "# 待辦\n\n- 修 X #8\n"


def issue(n, state="OPEN", stage=None, reason=None, labels=(), title=None):
    names = list(labels) + ([f"stage:{stage}"] if stage else [])
    return {"number": n, "state": state, "stateReason": reason, "title": title or f"票 {n}",
            "labels": [{"name": x} for x in names]}


def base_issues():
    return [issue(1, stage="in-progress"), issue(2, stage="todo"),
            issue(3, "CLOSED", reason="COMPLETED"), issue(4, stage="in-progress"),
            issue(5, stage="todo"), issue(6, stage="backlog"),
            issue(7, "CLOSED", reason="NOT_PLANNED"), issue(8, stage="todo", labels=["todo"])]


PARENTS = {3: 1, 4: 1, 5: 2, 6: 2}


def run(issues, feature=FEATURE, todo=TODO, parents=PARENTS, board=None, options=None):
    fc = rc.load_checklist()
    return rc.reconcile(fc.tickets(feature), fc.todo_items(todo), issues, board=board,
                        parents=parents, options=options)


def kinds(r):
    return sorted(d["kind"] for d in r["diffs"])


class Reconcile(unittest.TestCase):
    def test_all_match_zero_diff(self):
        r = run(base_issues())
        self.assertEqual(r["diffs"], [])
        self.assertEqual(r["diff_total"], 0)
        self.assertEqual(r["counts"]["feature"]["done"], [1, 1])
        self.assertEqual(r["counts"]["parent"]["open"], [2, 2])
        self.assertEqual(r["counts"]["todo"]["open"], [1, 1])

    def test_stage_mismatch(self):
        iss = base_issues()
        iss[3] = issue(4, stage="todo")
        self.assertEqual(kinds(run(iss)), ["stage"])

    def test_doing_matches_in_review(self):
        iss = base_issues()
        iss[3] = issue(4, stage="in-review")
        self.assertEqual(run(iss)["diffs"], [])

    def test_missing_ticket(self):
        r = run(base_issues(), feature=FEATURE.replace("- [ ] 💡 丁 #6", "- [ ] 💡 丁"))
        self.assertEqual(kinds(r), ["missing_ticket", "orphan"])  # #6 開著有 stage 卻沒人引用

    def test_ref_to_missing_issue(self):
        r = run(base_issues(), feature=FEATURE + "\n## 模組 C #2\n\n- [ ] 📋 己 #99\n", parents=None)
        self.assertIn("missing_issue", kinds(r))

    def test_orphan_and_exclusions(self):
        iss = base_issues() + [
            issue(20, stage="todo"),                                   # 孤兒
            issue(21, stage="todo", title="[測試] e2e"),               # 測試票
            issue(22, "CLOSED", reason="COMPLETED", labels=["todo"]),  # 已關 todo 票
            issue(23, labels=["triage"]),                              # triage 中
            issue(24, "CLOSED", reason="NOT_PLANNED"),                 # 清單已刪、已關
        ]
        r = run(iss)
        self.assertEqual(kinds(r), ["orphan"])
        self.assertEqual(r["excluded"], {"test": 1, "todo_closed": 1, "triage": 1, "closed_unreferenced": 1})

    def test_exclude_label(self):
        iss = base_issues() + [issue(30, stage="todo", labels=["test"])]
        self.assertEqual(run(iss)["diffs"], [])

    def test_parent_mismatch(self):
        r = run(base_issues(), parents={**PARENTS, 5: 1})
        self.assertEqual(kinds(r), ["parent"])

    def test_parent_state_follows_children(self):
        iss = base_issues()
        iss[0] = issue(1, "CLOSED", reason="COMPLETED")  # 模組 A 還有 🚧 乙，父票不該關
        self.assertEqual(kinds(run(iss)), ["stage"])

    def test_unclassified(self):
        r = run(base_issues() + [issue(9, stage="todo")], parents=None,
                feature=FEATURE + "\n## 模組 C #2\n\n- [ ] 沒標記 #9\n")
        self.assertIn("unclassified", kinds(r))

    def test_board_mismatch(self):
        opts = {"backlog": "Backlog", "todo": "Todo", "in-progress": "In Progress", "in-review": "In Review",
                "done": "Done", "canceled": "Canceled"}
        board = {1: "In Progress", 2: "Todo", 3: "Done", 4: "In Progress", 5: "Todo", 6: "Backlog",
                 7: "Done", 8: "Todo"}
        r = run(base_issues(), board=board, options=opts)
        self.assertEqual([d["ref"] for d in r["diffs"]], ["#7"])
        self.assertEqual(kinds(r), ["board"])


class Cli(unittest.TestCase):
    def cli(self, d, issues, *extra):
        f = Path(d) / "issues.json"
        f.write_text(json.dumps(issues), encoding="utf-8")
        (Path(d) / "feature.md").write_text(FEATURE, encoding="utf-8")
        (Path(d) / "todo.md").write_text(TODO, encoding="utf-8")
        p = Path(d) / "parents.json"
        p.write_text(json.dumps(PARENTS), encoding="utf-8")
        return subprocess.run([sys.executable, str(Path(rc.__file__).resolve()), "--repo", "o/r",
                               "--feature", str(Path(d) / "feature.md"), "--todo", str(Path(d) / "todo.md"),
                               "--issues-json", str(f), "--parents-json", str(p), *extra],
                              cwd=d, capture_output=True, text=True)

    def test_zero_diff_exit_0(self):
        with tempfile.TemporaryDirectory() as d:
            r = self.cli(d, base_issues())
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stdout.strip().splitlines()[-1], "差異 0")

    def test_diff_exit_1(self):
        with tempfile.TemporaryDirectory() as d:
            r = self.cli(d, base_issues() + [issue(20, stage="todo")])
            self.assertEqual(r.returncode, 1)
            self.assertEqual(r.stdout.strip().splitlines()[-1], "差異 1")

    def test_truncated_exit_3(self):
        with tempfile.TemporaryDirectory() as d:
            r = self.cli(d, base_issues() + [issue(100 + i, title="[測試] x") for i in range(992)])
            self.assertEqual(r.returncode, 3)
            self.assertIn("query 完整性：可能截斷", r.stdout)

    def test_log_appends(self):
        with tempfile.TemporaryDirectory() as d:
            log = Path(d) / "log.jsonl"
            self.cli(d, base_issues(), "--log", str(log))
            self.cli(d, base_issues(), "--log", str(log))
            rows = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(rows), 2)
            self.assertEqual(set(rows[0]), {"date", "repo", "counts", "diff_total"})
            self.assertEqual(rows[0]["diff_total"], 0)


if __name__ == "__main__":
    unittest.main()
