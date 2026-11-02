"""retro-due-reminder 測試：待驗指標到期才提醒，驗過且無新證據不重提，任何異常靜默放行。"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / "retro-due-reminder.py"

CONFIG = "retrospective:\n  path: docs/retrospective\n  units_glob: \"docs/*/*\"\n"


def entry(eid, due, status="open", checks=()):
    lines = [
        f"  - id: {eid}",
        f"    source: 20260101-x/report.md",
        f"    metric: 指標{eid}",
        f"    criterion: 可數的判準",
        f"    due: {due}",
        f"    status: {status}",
        "    checks:",
    ]
    lines += [f"      - {{date: \"{d}\", verdict: not-due, evidence: \"x\"}}" for d in checks]
    return "\n".join(lines)


class RetroDueReminder(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "專案 根"
        self.root.mkdir()
        self.git("init", "-q")
        self.git("config", "user.email", "test@example.com")
        self.git("config", "user.name", "test")
        (self.root / ".plugharbor").mkdir()
        (self.root / ".plugharbor" / "toolkit.yml").write_text(CONFIG, encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def git(self, *args, date=None):
        env = dict(os.environ)
        if date:
            env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = f"{date}T12:00:00"
        subprocess.run(["git", *args], cwd=self.root, env=env, check=True, capture_output=True)

    def add_unit(self, rel, date):
        d = self.root / rel
        d.mkdir(parents=True)
        (d / "a.md").write_text("x", encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", rel, date=date)

    def ledger(self, *entries):
        d = self.root / "docs" / "retrospective"
        d.mkdir(parents=True, exist_ok=True)
        (d / "metrics.yml").write_text("# 帳本\nmetrics:\n" + "\n\n".join(entries) + "\n", encoding="utf-8")

    def run_hook(self, payload=None, env_root=True, stdin=None):
        env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
        if env_root:
            env["CLAUDE_PROJECT_DIR"] = str(self.root)
        data = stdin if stdin is not None else json.dumps(payload or {"source": "startup", "cwd": str(self.root)})
        p = subprocess.run([sys.executable, str(HOOK)], input=data.encode("utf-8"), capture_output=True, env=env)
        self.assertEqual(p.returncode, 0, p.stderr.decode("utf-8", "replace"))
        out = p.stdout.decode("utf-8")
        return json.loads(out)["hookSpecificOutput"]["additionalContext"] if out else ""

    def test_new_chains_due_lists_entry(self):
        self.add_unit("docs/a/u1", "2026-01-10")
        self.add_unit("docs/a/u2", "2026-01-11")
        self.ledger(entry("M-1", '{new_chains: 2, since: "2026-01-05"}'))
        msg = self.run_hook()
        self.assertIn("M-1", msg)
        self.assertIn("2/2", msg)
        self.assertIn("toolkit:retrospective", msg)

    def test_not_enough_units_silent(self):
        self.add_unit("docs/a/u1", "2026-01-10")
        self.ledger(entry("M-1", '{new_chains: 2, since: "2026-01-05"}'))
        self.assertEqual(self.run_hook(), "")

    def test_units_before_since_not_counted(self):
        self.add_unit("docs/a/u1", "2026-01-01")
        self.add_unit("docs/a/u2", "2026-01-10")
        self.ledger(entry("M-1", '{new_chains: 2, since: "2026-01-05"}'))
        self.assertEqual(self.run_hook(), "")

    def test_entry_units_glob_overrides_setting(self):
        self.add_unit("specs/u1", "2026-01-10")
        self.ledger(entry("M-1", '{new_chains: 1, since: "2026-01-05", units_glob: "specs/*"}'))
        self.assertIn("M-1", self.run_hook())

    def test_checked_after_latest_unit_silent_then_new_unit_reminds(self):
        self.add_unit("docs/a/u1", "2026-01-10")
        self.ledger(entry("M-1", '{new_chains: 1, since: "2026-01-05"}', checks=["2026-01-12"]))
        self.assertEqual(self.run_hook(), "")
        self.add_unit("docs/a/u2", "2026-01-15")
        self.assertIn("M-1", self.run_hook())

    def test_date_due_and_checked(self):
        self.ledger(entry("M-1", '{date: "2000-01-01"}'), entry("M-2", '{date: "2999-01-01"}'))
        msg = self.run_hook()
        self.assertIn("M-1", msg)
        self.assertNotIn("M-2", msg)
        self.ledger(entry("M-1", '{date: "2000-01-01"}', checks=["2000-01-02"]))
        self.assertEqual(self.run_hook(), "")

    def test_closed_entry_skipped(self):
        self.ledger(entry("M-1", '{date: "2000-01-01"}', status="passed"))
        self.assertEqual(self.run_hook(), "")

    def test_broken_entry_does_not_hide_others(self):
        self.ledger(entry("M-1", "壞掉"), entry("M-2", '{date: "2000-01-01"}'))
        msg = self.run_hook()
        self.assertIn("M-2", msg)
        self.assertNotIn("M-1", msg)

    def test_no_config_silent(self):
        (self.root / ".plugharbor" / "toolkit.yml").unlink()
        self.ledger(entry("M-1", '{date: "2000-01-01"}'))
        self.assertEqual(self.run_hook(), "")

    def test_no_ledger_silent(self):
        self.assertEqual(self.run_hook(), "")

    def test_garbage_ledger_silent(self):
        d = self.root / "docs" / "retrospective"
        d.mkdir(parents=True)
        (d / "metrics.yml").write_bytes(b"\xff\xfe not yaml")
        self.assertEqual(self.run_hook(), "")

    def test_bad_stdin_silent(self):
        self.ledger(entry("M-1", '{date: "2000-01-01"}'))
        self.assertEqual(self.run_hook(stdin="not json"), "")

    def test_project_dir_env_wins_over_cwd(self):
        self.ledger(entry("M-1", '{date: "2000-01-01"}'))
        sub = self.root / "docs"
        self.assertIn("M-1", self.run_hook({"source": "startup", "cwd": str(sub)}))

    def test_cwd_used_without_env(self):
        self.ledger(entry("M-1", '{date: "2000-01-01"}'))
        self.assertIn("M-1", self.run_hook(env_root=False))

    def test_not_git_repo_new_chains_silent(self):
        subprocess.run(["rm", "-rf", str(self.root / ".git")], check=True)
        self.ledger(entry("M-1", '{new_chains: 1, since: "2026-01-05"}'))
        self.assertEqual(self.run_hook(), "")


if __name__ == "__main__":
    unittest.main()
