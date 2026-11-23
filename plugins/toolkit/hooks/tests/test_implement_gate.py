"""implement-gate 測試：有 lifecycle.yml 且沒叫過 implement 才擋第一次；已叫過、已擋過、無設定、壞輸入一律放行。"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / "implement-gate.py"


def skill_line(name):
    return json.dumps({"message": {"content": [{"type": "tool_use", "name": "Skill", "input": {"skill": name}}]}})


class ImplementGate(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.repo = self.root / "repo"
        (self.repo / ".git").mkdir(parents=True)
        (self.repo / ".plugharbor").mkdir()
        (self.repo / ".plugharbor" / "lifecycle.yml").write_text("spec:\n  dir: docs\n", encoding="utf-8")
        (self.repo / "sub").mkdir()
        self.transcript = self.root / "t.jsonl"
        self.transcript.write_text("", encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def run_hook(self, skill="superpowers:writing-plans", cwd=None, tool="Skill", stdin=None):
        payload = {"tool_name": tool, "tool_input": {"skill": skill}, "cwd": str(cwd or self.repo / "sub"),
                   "transcript_path": str(self.transcript)}
        data = stdin if stdin is not None else json.dumps(payload)
        p = subprocess.run([sys.executable, str(HOOK)], input=data.encode(), capture_output=True)
        self.assertEqual(p.returncode, 0)
        return p.stdout.decode().strip()

    def test_first_call_denied(self):
        out = json.loads(self.run_hook())["hookSpecificOutput"]
        self.assertEqual(out["permissionDecision"], "deny")
        self.assertIn("lifecycle:implement", out["permissionDecisionReason"])

    def test_all_three_gated(self):
        for s in ("superpowers:writing-plans", "superpowers:executing-plans", "superpowers:subagent-driven-development"):
            with self.subTest(skill=s):
                self.assertIn("deny", self.run_hook(skill=s))

    def test_second_call_after_deny_allowed(self):
        reason = json.loads(self.run_hook())["hookSpecificOutput"]["permissionDecisionReason"]
        self.transcript.write_text(
            json.dumps({"message": {"content": [{"type": "tool_result", "content": reason}]}}) + "\n", encoding="utf-8")
        self.assertEqual(self.run_hook(), "")

    def test_implement_already_called_allowed(self):
        self.transcript.write_text(skill_line("lifecycle:implement") + "\n", encoding="utf-8")
        self.assertEqual(self.run_hook(), "")

    def test_other_skill_in_transcript_still_denied(self):
        self.transcript.write_text(skill_line("superpowers:brainstorming") + "\n", encoding="utf-8")
        self.assertIn("deny", self.run_hook())

    def test_no_lifecycle_config_allowed(self):
        (self.repo / ".plugharbor" / "lifecycle.yml").unlink()
        self.assertEqual(self.run_hook(), "")

    def test_other_skill_or_tool_allowed(self):
        self.assertEqual(self.run_hook(skill="superpowers:brainstorming"), "")
        self.assertEqual(self.run_hook(tool="Bash"), "")

    def test_missing_transcript_fail_open(self):
        self.transcript.unlink()
        self.assertEqual(self.run_hook(), "")

    def test_bad_stdin_fail_open(self):
        self.assertEqual(self.run_hook(stdin="not json"), "")

    def test_worktree_git_file_counts_as_root(self):
        wt = self.root / "wt"
        wt.mkdir()
        (wt / ".git").write_text("gitdir: x\n", encoding="utf-8")
        self.assertEqual(self.run_hook(cwd=wt), "")  # worktree 根沒有 lifecycle.yml → 不擋
        (wt / ".plugharbor").mkdir()
        (wt / ".plugharbor" / "lifecycle.yml").write_text("x: 1\n", encoding="utf-8")
        self.assertIn("deny", self.run_hook(cwd=wt))


if __name__ == "__main__":
    unittest.main()
