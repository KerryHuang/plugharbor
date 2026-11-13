"""detect.py 的單元測試（unittest，僅用標準函式庫）。"""
import json
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import detect  # noqa: E402


def git(root, *args):
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.com",
         "-c", "commit.gpgsign=false", *args],
        cwd=root, check=True, capture_output=True,
    )


def write(root, rel, text=""):
    p = Path(root) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


class DetectTest(unittest.TestCase):
    def test_empty_dir(self):
        with tempfile.TemporaryDirectory() as d:
            r = detect.inventory(Path(d))
            self.assertTrue(r["is_empty"])
            self.assertFalse(r["has_git"])
            self.assertEqual(r["git_mode"], "init")
            self.assertEqual(r["signals"], [])

    def test_only_git_dir_is_empty_and_init(self):
        with tempfile.TemporaryDirectory() as d:
            git(d, "init")
            r = detect.inventory(Path(d))
            self.assertTrue(r["is_empty"])
            self.assertTrue(r["has_git"])
            self.assertEqual(r["git_mode"], "init")

    def test_untracked_existing_repo_is_local(self):
        with tempfile.TemporaryDirectory() as d:
            git(d, "init")
            write(d, "a.cs")
            git(d, "add", "a.cs")
            git(d, "commit", "-m", "x")
            self.assertEqual(detect.inventory(Path(d))["git_mode"], "local")

    def test_tracked_ai_config_is_shared(self):
        with tempfile.TemporaryDirectory() as d:
            git(d, "init")
            write(d, "AGENTS.md", "# x\n")
            git(d, "add", "AGENTS.md")
            git(d, "commit", "-m", "x")
            r = detect.inventory(Path(d))
            self.assertEqual(r["git_mode"], "shared")
            self.assertEqual(r["existing"]["agents_md"], "present")

    def _signals_case(self, root):
        write(root, "x.csproj", "<Project><PackageReference Include=\"Avalonia\"/></Project>")
        r = detect.inventory(Path(root))
        self.assertIn("dotnet", r["signals"])
        self.assertIn("backend", r["suggested_plugins"])
        self.assertIn("avalonia", r["signals"])
        self.assertIn("desktop", r["suggested_plugins"])

    def test_signals_and_suggestions(self):
        with tempfile.TemporaryDirectory() as d:
            self._signals_case(d)
        with tempfile.TemporaryDirectory() as d:
            write(d, "x.csproj", "<Project/>")
            r = detect.inventory(Path(d))
            self.assertNotIn("desktop", r["suggested_plugins"])
        with tempfile.TemporaryDirectory() as d:
            write(d, "package.json", json.dumps({"dependencies": {"vue": "^3"}}))
            r = detect.inventory(Path(d))
            self.assertIn("node", r["signals"])
            self.assertIn("vue", r["signals"])
            self.assertIn("frontend", r["suggested_plugins"])
        with tempfile.TemporaryDirectory() as d:
            write(d, "db/a.sql", "select 1;")
            r = detect.inventory(Path(d))
            self.assertIn("sql", r["signals"])
            self.assertIn("database", r["suggested_plugins"])

    def test_claude_md_variants(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(detect.inventory(Path(d))["existing"]["claude_md"], "none")
        with tempfile.TemporaryDirectory() as d:
            write(d, "CLAUDE.md", "@AGENTS.md\n")
            self.assertEqual(detect.inventory(Path(d))["existing"]["claude_md"], "at-agents")
        with tempfile.TemporaryDirectory() as d:
            write(d, "CLAUDE.md", "# 自訂\n")
            self.assertEqual(detect.inventory(Path(d))["existing"]["claude_md"], "custom")

    def test_existing_skills_and_pi(self):
        with tempfile.TemporaryDirectory() as d:
            write(d, ".claude/skills/foo/SKILL.md")
            write(d, ".agents/skills/bar/SKILL.md")
            write(d, ".pi/settings.json", "{}")
            e = detect.inventory(Path(d))["existing"]
            self.assertEqual(e["claude_skills"], ["foo"])
            self.assertEqual(e["agents_skills"], ["bar"])
            self.assertTrue(e["pi_settings"])

    def test_path_with_space_and_cjk(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "我的 專案"
            root.mkdir()
            self._signals_case(root)

    def test_subdir_of_repo_never_init(self):
        with tempfile.TemporaryDirectory() as d:
            git(d, "init")
            write(d, "top.txt")
            git(d, "add", "top.txt")
            git(d, "commit", "-m", "x")
            sub = Path(d) / "sub"
            sub.mkdir()
            r = detect.inventory(sub)  # 空的子目錄也不能 init
            self.assertTrue(r["has_git"])
            self.assertEqual(r["git_toplevel"], str(Path(d).resolve()))
            self.assertEqual(r["git_mode"], "local")
            write(sub, "AGENTS.md", "# x\n")
            git(d, "add", "sub/AGENTS.md")
            self.assertEqual(detect.inventory(sub)["git_mode"], "shared")

    def test_subdir_ignores_toplevel_ai_config_outside_root(self):
        with tempfile.TemporaryDirectory() as d:
            git(d, "init")
            write(d, "AGENTS.md", "# top\n")
            write(d, "sub/a.cs")
            git(d, "add", "AGENTS.md", "sub/a.cs")
            git(d, "commit", "-m", "x")
            self.assertEqual(detect.inventory(Path(d) / "sub")["git_mode"], "local")

    def test_toplevel_equals_root_and_none(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(detect.inventory(Path(d))["git_toplevel"])
            git(d, "init")
            self.assertEqual(detect.inventory(Path(d))["git_toplevel"], str(Path(d).resolve()))

    def test_git_missing_means_no_repo(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch("subprocess.run", side_effect=OSError):
                r = detect.inventory(Path(d))
            self.assertFalse(r["has_git"])
            self.assertIsNone(r["git_toplevel"])

    def test_cli_prints_json(self):
        with tempfile.TemporaryDirectory() as d:
            p = subprocess.run([sys.executable, str(HERE / "detect.py"), d],
                               capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(p.returncode, 0)
            self.assertIn("git_mode", json.loads(p.stdout))


if __name__ == "__main__":
    unittest.main()
