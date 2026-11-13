"""rm-scratch-allow 測試：rm 目標全在暫存區（scratchpad、.tmp/、.superpowers/）才自動核准，其他不表態。"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[1]
HOOK = HOOKS / "rm-scratch-allow.py"


class RmScratchAllow(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(os.path.realpath(self._tmp.name))
        self.repo = root / "repo"
        (self.repo / ".tmp" / "20261113-x").mkdir(parents=True)
        (self.repo / ".superpowers" / "sdd").mkdir(parents=True)
        (self.repo / "src").mkdir()
        self.scratch = root / "claude-501" / "-proj" / "sess-1" / "scratchpad"
        (self.scratch / "e2e").mkdir(parents=True)
        os.symlink(self.repo / "src", self.repo / ".tmp" / "link")

    def tearDown(self):
        self._tmp.cleanup()

    def run_hook(self, command, cwd=None, tool="Bash"):
        payload = {"hook_event_name": "PermissionRequest", "tool_name": tool, "cwd": str(cwd or self.repo),
                   "tool_input": {"command": command}}
        env = dict(os.environ, CLAUDE_SCRATCH_BASE=str(self.scratch.parents[3]))
        p = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(payload).encode("utf-8"),
                           capture_output=True, timeout=10, env=env)
        self.assertEqual(p.returncode, 0, p.stderr.decode("utf-8", "replace"))
        out = p.stdout.decode("utf-8").strip()
        if not out:
            return None
        return json.loads(out)["hookSpecificOutput"]["decision"]["behavior"]

    # 放行
    def test_scratchpad_allows(self):
        self.assertEqual(self.run_hook(f"rm -rf {self.scratch}/e2e"), "allow")

    def test_repo_tmp_relative_allows(self):
        self.assertEqual(self.run_hook("rm -rf .tmp/20261113-x"), "allow")

    def test_superpowers_allows(self):
        self.assertEqual(self.run_hook(f"rm -r {self.repo}/.superpowers/sdd"), "allow")

    def test_with_harmless_chain_allows(self):
        cmd = f"rm -rf {self.scratch}/e2e && echo cleaned; cd {self.repo} && ls"
        self.assertEqual(self.run_hook(cmd), "allow")

    def test_with_readonly_chain_allows(self):
        cmd = "rm -rf .superpowers/sdd && git status --short && git branch --show-current | head -3; sed -n 1,5p a.md; grep -n x b | wc -l"
        self.assertEqual(self.run_hook(cmd), "allow")

    def test_cd_then_relative_allows(self):
        self.assertEqual(self.run_hook(f"cd {self.repo} && rm -rf .tmp/20261113-x", cwd=self.scratch), "allow")

    def test_symlink_itself_allows(self):
        self.assertEqual(self.run_hook("rm -f .tmp/link"), "allow")

    # 不表態（照常跳確認）
    def test_outside_target(self):
        self.assertIsNone(self.run_hook("rm -rf src"))

    def test_one_of_many_outside(self):
        self.assertIsNone(self.run_hook(f"rm -rf .tmp/20261113-x {self.repo}/src"))

    def test_dotdot_escape(self):
        self.assertIsNone(self.run_hook("rm -rf .tmp/../src"))

    def test_symlink_trailing_slash(self):
        self.assertIsNone(self.run_hook("rm -rf .tmp/link/"))

    def test_scratch_root_itself(self):
        self.assertIsNone(self.run_hook(f"rm -rf {self.scratch.parents[2]}"))

    def test_tmp_dir_name_only_in_middle_of_word(self):
        self.assertIsNone(self.run_hook(f"rm -rf {self.repo}/src.tmp"))

    def test_other_command_in_chain(self):
        self.assertIsNone(self.run_hook("rm -rf .tmp/20261113-x && git push --force"))

    def test_writing_variants_of_readonly_commands(self):
        for cmd in ("rm -rf .tmp/20261113-x && sed -i s/a/b/ f", "rm -rf .tmp/20261113-x && git branch -D x",
                    "rm -rf .tmp/20261113-x && git checkout .", "rm -rf .tmp/20261113-x && python3 x.py"):
            with self.subTest(cmd=cmd):
                self.assertIsNone(self.run_hook(cmd))

    def test_scratch_root_needs_uid_name(self):
        other = self.scratch.parents[3] / "claude-del.bak" / "a" / "b" / "c"
        other.mkdir(parents=True)
        env_root = self.scratch.parents[3]
        payload = {"hook_event_name": "PermissionRequest", "tool_name": "Bash", "cwd": str(self.repo),
                   "tool_input": {"command": f"rm -rf {other}"}}
        env = dict(os.environ, CLAUDE_SCRATCH_BASE=str(env_root))
        p = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(payload).encode("utf-8"),
                           capture_output=True, timeout=10, env=env)
        self.assertEqual(p.stdout, b"")
        payload["tool_input"]["command"] = f"rm -rf {self.scratch}/e2e"
        p = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(payload).encode("utf-8"),
                           capture_output=True, timeout=10, env=env)
        self.assertIn(b"allow", p.stdout)

    def test_substitution_variables_globs(self):
        for cmd in ("rm -rf $(pwd)/.tmp", "rm -rf $HOME/.tmp", "rm -rf .tmp/*", "rm -rf `pwd`", "echo x > a && rm -rf .tmp/20261113-x"):
            with self.subTest(cmd=cmd):
                self.assertIsNone(self.run_hook(cmd))

    def test_no_target(self):
        self.assertIsNone(self.run_hook("rm -rf"))

    def test_no_rm_at_all(self):
        self.assertIsNone(self.run_hook("echo hi"))

    def test_non_bash_tool(self):
        self.assertIsNone(self.run_hook("rm -rf .tmp/x", tool="Write"))

    def test_bad_stdin(self):
        p = subprocess.run([sys.executable, str(HOOK)], input=b"not json", capture_output=True, timeout=10)
        self.assertEqual((p.returncode, p.stdout), (0, b""))

    def test_registered_on_permission_request(self):
        cfg = json.loads((HOOKS / "hooks.json").read_text(encoding="utf-8"))["hooks"]["PermissionRequest"]
        cmds = [h["command"] for m in cfg if m.get("matcher") == "Bash" for h in m["hooks"]]
        self.assertTrue(any("rm-scratch-allow.py" in c for c in cmds), cfg)


if __name__ == "__main__":
    unittest.main()
