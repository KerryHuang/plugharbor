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
        self.assertEqual(p["location"], ".github/ticket-assets/shot-one.png")
        self.assertIn("example-org/example-repo", p["markdown"])
        self.assertNotIn(" ", p["markdown"])

    def test_special_filename_is_url_encoded(self):
        p = tb.github_attach_plan("o/r", "/tmp/截圖 (1)#a.png")
        url = p["markdown"].split("](", 1)[1].rstrip(")")
        self.assertIn("%E6%88%AA%E5%9C%96-%281%29%23a.png", url)
        self.assertTrue(url.endswith("?raw=true"))
        self.assertNotIn("#", url)
        self.assertNotIn("(", url)

DENY = "# 註解\n\nSecretCorp\nregex:10\\.0\\.\\d+\\.\\d+\n"


class Leak(unittest.TestCase):
    def pats(self, d):
        (Path(d) / ".leak-denylist").write_text(DENY, encoding="utf-8")
        return tb.load_denylist(Path(d))

    def test_denylist_comments_regex_case(self):
        with tempfile.TemporaryDirectory() as d:
            hits = tb.scan_leaks("hello secretcorp\nip 10.0.3.4", self.pats(d))
        self.assertEqual(hits, [(1, "secretcorp"), (2, "10.0.3.4")])

    def test_no_hit_returns_empty(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(tb.scan_leaks("乾淨內文", self.pats(d)), [])

    def test_missing_denylist_returns_none(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(tb.load_denylist(Path(d)))

    def test_cli_exit_codes(self):
        with tempfile.TemporaryDirectory() as d:
            self.pats(d)
            f = Path(d) / "body.md"
            f.write_text("x\n含 SECRETCORP", encoding="utf-8")
            r = Cli.run_cli(self, d, "leak", str(f))
            self.assertEqual(r.returncode, 4)
            self.assertEqual(r.stdout.strip(), "L2 SECRETCORP")
            f.write_text("乾淨", encoding="utf-8")
            self.assertEqual(Cli.run_cli(self, d, "leak", str(f)).returncode, 0)
            (Path(d) / ".leak-denylist").unlink()
            r = Cli.run_cli(self, d, "leak", str(f))
            self.assertEqual(r.returncode, 5)
            self.assertTrue(r.stderr.strip())

    def test_parser_matches_validate(self):
        v = Path(__file__).resolve().parents[5] / "scripts" / "ci" / "validate.py"
        if not v.exists():
            self.skipTest("不在 plugharbor repo 內")
        import importlib.util
        spec = importlib.util.spec_from_file_location("validate_ci", v)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        with tempfile.TemporaryDirectory() as d:
            ours = self.pats(d)
            mod.ROOT = Path(d)
            theirs = mod.load_denylist()
        self.assertEqual([(p.pattern, p.flags) for p in ours], [(p.pattern, p.flags) for p in theirs])


GITHUB_BOARD = {"ticket": {**GITHUB["ticket"], "project": {"owner": "example-org", "number": 3, "options": {
    "backlog": "Backlog", "todo": "Todo", "in-progress": "In Progress", "in-review": "In Review",
    "done": "Done", "canceled": "Canceled"}}}}


class ProjectOption(unittest.TestCase):
    def test_no_project_returns_none(self):
        self.assertIsNone(tb.project_option(GITHUB, "todo"))

    def test_maps_stage(self):
        self.assertEqual(tb.project_option(GITHUB_BOARD, "in_progress"), "In Progress")

    def test_missing_option_raises(self):
        import copy
        cfg = copy.deepcopy(GITHUB_BOARD)
        del cfg["ticket"]["project"]["options"]["canceled"]
        with self.assertRaises(ValueError) as cm:
            tb.project_option(cfg, "canceled")
        self.assertIn("canceled", str(cm.exception))

    def test_unknown_stage_raises(self):
        with self.assertRaises(ValueError):
            tb.project_option(GITHUB_BOARD, "shipping")

    def test_cli_json(self):
        import yaml
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / ".plugharbor").mkdir()
            (Path(d) / ".plugharbor" / "lifecycle.yml").write_text(yaml.safe_dump(GITHUB_BOARD), encoding="utf-8")
            r = Cli.run_cli(self, d, "project-option", "done")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(json.loads(r.stdout), {"owner": "example-org", "number": 3, "field": "Status", "option": "Done"})
            (Path(d) / ".plugharbor" / "lifecycle.yml").write_text(yaml.safe_dump(GITHUB), encoding="utf-8")
            r = Cli.run_cli(self, d, "project-option", "done")
            self.assertEqual((r.returncode, r.stdout.strip()), (0, "null"))


class Cli(unittest.TestCase):
    def run_cli(self, cwd, *args):
        return subprocess.run([sys.executable, str(Path(tb.__file__).resolve()), *args],
                              cwd=cwd, capture_output=True, text=True)

    def test_stage_prints_json(self):
        import yaml
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / ".plugharbor").mkdir()
            (Path(d) / ".plugharbor" / "lifecycle.yml").write_text(yaml.safe_dump(LINEAR))
            r = self.run_cli(d, "stage", "done")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(json.loads(r.stdout), {"state": "Done"})

    def test_missing_config_exit_2(self):
        with tempfile.TemporaryDirectory() as d:
            r = self.run_cli(d, "stage", "done")
            self.assertEqual(r.returncode, 2)
            self.assertTrue(r.stderr.strip())

    def test_old_delivery_flow_yml_exit_3(self):
        import yaml
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / ".plugharbor").mkdir()
            (Path(d) / ".plugharbor" / "delivery-flow.yml").write_text(yaml.safe_dump(LINEAR), encoding="utf-8")
            r = self.run_cli(d, "stage", "done")
            self.assertEqual(r.returncode, 3)
            self.assertIn("delivery-flow.yml", r.stderr)

    def test_unknown_stage_exit_2(self):
        import yaml
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / ".plugharbor").mkdir()
            (Path(d) / ".plugharbor" / "lifecycle.yml").write_text(yaml.safe_dump(LINEAR))
            r = self.run_cli(d, "stage", "nope")
            self.assertEqual(r.returncode, 2)
            self.assertIn("backlog", r.stderr)


if __name__ == "__main__":
    unittest.main()
