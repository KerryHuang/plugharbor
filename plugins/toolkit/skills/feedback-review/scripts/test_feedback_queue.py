#!/usr/bin/env python3
"""feedback_queue.py 的行為驗證。HOME 一律導到暫存目錄，絕不碰真的 ~/.claude/feedback-loop。"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

SCRIPT = Path(__file__).with_name("feedback_queue.py")


class FeedbackQueueTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.home = self.tmp / "home"
        self.fb = self.home / ".claude" / "feedback-loop"
        self.fb.mkdir(parents=True)
        self.queue = self.fb / "queue.jsonl"
        recs = [{"id": f"id{i}", "ts": "2026-01-0%dT00:00:00+00:00" % (i + 1), "excerpt": f"不對{i}"} for i in range(3)]
        self.queue.write_text("".join(json.dumps(r) + "\n" for r in recs), encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def run_q(self, *args, check=True, cwd=None):
        env = dict(os.environ, HOME=str(self.home), USERPROFILE=str(self.home))
        p = subprocess.run([sys.executable, str(SCRIPT), *args], env=env, cwd=cwd,
                           capture_output=True, text=True, encoding="utf-8")
        if check:
            self.assertEqual(p.returncode, 0, p.stderr)
        return p

    def lines(self, path=None):
        path = path or self.queue
        return len(path.read_text(encoding="utf-8").splitlines()) if path.exists() else 0

    def pending(self, *extra):
        return json.loads(self.run_q("pending", *extra).stdout)

    def test_archive_moves_record_and_stamps(self):
        self.assertNotEqual(self.run_q("archive", "nope", check=False).returncode, 0)
        self.assertEqual(self.lines(), 3)
        self.run_q("archive", "id0", "--disposition", "雜訊")
        self.assertEqual(self.lines(), 2)
        self.assertFalse((self.fb / "queue.processing.jsonl").exists())
        self.assertIn("id0", (self.fb / "archive.jsonl").read_text(encoding="utf-8"))
        self.assertTrue((self.fb / "last-review").read_text().strip())
        self.assertEqual(len(self.pending()), 2)

    def test_bad_line_gets_bad_id_and_can_be_archived(self):
        with open(self.queue, "a", encoding="utf-8") as fh:
            fh.write("garbage\n")
        bad = [r["id"] for r in self.pending() if r["id"].startswith("bad-")]
        self.assertEqual(len(bad), 1)
        self.run_q("archive", bad[0])
        self.assertEqual(self.lines(), 3)

    def test_leftover_processing_file_is_merged_not_lost(self):
        proc = self.fb / "queue.processing.jsonl"
        self.queue.rename(proc)
        self.queue.write_text(json.dumps({"id": "late", "ts": "2026-02-01T00:00:00+00:00"}) + "\n", encoding="utf-8")
        self.assertEqual(len(self.pending()), 4)
        self.run_q("archive", "id0")
        self.assertEqual(len(self.pending()), 3)
        self.assertFalse(proc.exists())

    def test_since_date_excludes_that_day_and_stamp_only_writes_last_review(self):
        today = date.today().isoformat()
        self.assertEqual(len(self.pending("--since", today)), 0)
        self.assertEqual(len(self.pending("--since", "2000-01-01")), 3)
        self.run_q("stamp")
        self.assertTrue((self.fb / "last-review").read_text().strip())
        self.assertEqual(self.lines(), 3)

    def test_friction_appends_agent_record(self):
        self.run_q("friction", "--tried", "照規則做", "--found", "規則過時", "--led-by", "舊規則")
        recs = self.pending()
        self.assertEqual(len(recs), 4)
        r = recs[-1]
        self.assertEqual((r["source"], r["tried"], r["found"], r["led_by"]), ("agent", "照規則做", "規則過時", "舊規則"))
        self.assertIn("friction", r["matched"])
        self.assertNotEqual(self.run_q("friction", "--tried", "x", check=False).returncode, 0)

    def test_ledger_path(self):
        repo = self.tmp / "repo"
        (repo / "sub").mkdir(parents=True)
        (self.tmp / "norepo").mkdir()
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        out = lambda *a: json.loads(self.run_q("ledger", *a).stdout)["ledger"].replace("\\", "/")
        self.assertTrue(out("--cwd", str(repo / "sub")).endswith("repo/.claude/feedback-ledger.md"))
        self.assertTrue(out("--cwd", str(self.tmp / "norepo")).endswith(".claude/feedback-loop/ledger.md"))
        self.assertTrue(out("--user", "--cwd", str(repo)).endswith(".claude/feedback-loop/ledger.md"))


if __name__ == "__main__":
    unittest.main()
