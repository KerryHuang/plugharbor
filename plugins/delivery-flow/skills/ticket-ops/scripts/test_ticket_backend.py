#!/usr/bin/env python3
"""ticket_backend 的測試。直接執行：python3 test_ticket_backend.py"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ticket_backend as tb  # noqa: E402

LINEAR = {"ticket": {"tool": "linear", "team": "Platform", "states": {
    "backlog": "Backlog", "todo": "Todo", "in-progress": "In Progress",
    "in-review": "In Review", "done": "Done", "canceled": "Canceled"}}}
GITHUB = {"ticket": {"tool": "github", "repo": "example-org/example-repo", "states": {
    "backlog": "stage:backlog", "todo": "stage:todo", "in-progress": "stage:in-progress",
    "in-review": "stage:in-review", "done": "closed", "canceled": "closed: not planned"}}}


class StageToNative(unittest.TestCase):
    def test_linear_maps_to_state_name(self):
        self.assertEqual(tb.stage_to_native(LINEAR, "in-review"), {"state": "In Review"})

    def test_underscore_alias(self):
        self.assertEqual(tb.stage_to_native(LINEAR, "in_progress"), {"state": "In Progress"})

    def test_github_open_stage_swaps_labels(self):
        r = tb.stage_to_native(GITHUB, "in-progress")
        self.assertEqual(r["labels_add"], ["stage:in-progress"])
        self.assertEqual(sorted(r["labels_remove"]),
                         ["stage:backlog", "stage:in-review", "stage:todo"])
        self.assertFalse(r["close"])

    def test_github_done_closes_and_clears_labels(self):
        r = tb.stage_to_native(GITHUB, "done")
        self.assertEqual(r["labels_add"], [])
        self.assertEqual(len(r["labels_remove"]), 4)
        self.assertTrue(r["close"])
        self.assertEqual(r["reason"], "completed")

    def test_github_canceled_closes_not_planned(self):
        r = tb.stage_to_native(GITHUB, "canceled")
        self.assertTrue(r["close"])
        self.assertEqual(r["reason"], "not planned")

    def test_unknown_stage_lists_valid_values(self):
        with self.assertRaises(ValueError) as cm:
            tb.stage_to_native(LINEAR, "shipping")
        for s in tb.STAGES:
            self.assertIn(s, str(cm.exception))

    def test_unmapped_stage_raises_config_missing(self):
        cfg = {"ticket": {"tool": "linear", "states": {"todo": "Todo"}}}
        with self.assertRaises(tb.ConfigMissing):
            tb.stage_to_native(cfg, "done")

    def test_unsupported_tool(self):
        with self.assertRaises(ValueError):
            tb.stage_to_native({"ticket": {"tool": "trello", "states": {}}}, "todo")


class AttachPlan(unittest.TestCase):
    def test_commit_plan_location_in_markdown(self):
        p = tb.github_attach_plan("example-org/example-repo", "/tmp/shot one.png")
        self.assertEqual(p["method"], "commit")
        self.assertTrue(p["location"])
        self.assertIn(p["location"], p["markdown"])
        self.assertIn("example-org/example-repo", p["markdown"])
        self.assertNotIn(" ", p["location"])

    def test_gist_fallback_reports_location(self):
        p = tb.github_attach_plan("example-org/example-repo", "/tmp/a.png", method="gist")
        self.assertEqual(p["method"], "gist")
        self.assertTrue(p["location"])
        self.assertIn(p["location"], p["markdown"])

    def test_bad_method(self):
        with self.assertRaises(ValueError):
            tb.github_attach_plan("o/r", "a.png", method="ftp")


class Cli(unittest.TestCase):
    def run_cli(self, cwd, *args):
        return subprocess.run([sys.executable, str(Path(tb.__file__).resolve()), *args],
                              cwd=cwd, capture_output=True, text=True)

    def test_stage_prints_json(self):
        import yaml
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / ".plugharbor").mkdir()
            (Path(d) / ".plugharbor" / "delivery-flow.yml").write_text(yaml.safe_dump(LINEAR))
            r = self.run_cli(d, "stage", "done")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(json.loads(r.stdout), {"state": "Done"})

    def test_missing_config_exit_2(self):
        with tempfile.TemporaryDirectory() as d:
            r = self.run_cli(d, "stage", "done")
            self.assertEqual(r.returncode, 2)
            self.assertTrue(r.stderr.strip())

    def test_unknown_stage_exit_2(self):
        import yaml
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / ".plugharbor").mkdir()
            (Path(d) / ".plugharbor" / "delivery-flow.yml").write_text(yaml.safe_dump(LINEAR))
            r = self.run_cli(d, "stage", "nope")
            self.assertEqual(r.returncode, 2)
            self.assertIn("backlog", r.stderr)


if __name__ == "__main__":
    unittest.main()
