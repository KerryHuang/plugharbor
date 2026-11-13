#!/usr/bin/env python3
"""mirror.py 的測試：python3 test_mirror.py"""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent))
import mirror  # noqa: E402

GIT_ENV = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull)


def git(*args, cwd=None):
    subprocess.run(["git", *args], cwd=cwd, env=GIT_ENV, check=True,
                   capture_output=True, text=True)


class MirrorBase(unittest.TestCase):
    dirname = "proj"

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / self.dirname
        self.root.mkdir()

    def skill(self, name, body="# x\n"):
        d = self.root / ".claude" / "skills" / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text(body, encoding="utf-8")
        return d


class TestMirror(MirrorBase):
    def test_links_each_skill(self):
        self.skill("a", "hello")
        r = mirror.mirror(self.root)
        link = self.root / ".agents" / "skills" / "a"
        self.assertEqual(r["linked"], ["a"])
        self.assertTrue(link.is_symlink())
        self.assertEqual(os.readlink(link), os.path.join("..", "..", ".claude", "skills", "a"))
        self.assertEqual((link / "SKILL.md").read_text(encoding="utf-8"), "hello")

    def test_ignores_files_and_dirs_without_skill_md(self):
        self.skill("a")
        (self.root / ".claude" / "skills" / "noskill").mkdir()
        (self.root / ".claude" / "skills" / "file.txt").write_text("x", encoding="utf-8")
        r = mirror.mirror(self.root)
        self.assertEqual(r["linked"], ["a"])

    def test_no_skills_dir(self):
        self.assertEqual(mirror.mirror(self.root), {"linked": [], "copied": [], "skipped": []})

    def test_existing_real_dir_skipped(self):
        self.skill("a")
        d = self.root / ".agents" / "skills" / "a"
        d.mkdir(parents=True)
        (d / "mine.txt").write_text("keep", encoding="utf-8")
        r = mirror.mirror(self.root)
        self.assertEqual(r["skipped"], ["a"])
        self.assertEqual(r["linked"], [])
        self.assertEqual((d / "mine.txt").read_text(encoding="utf-8"), "keep")
        self.assertFalse(d.is_symlink())

    def test_symlink_elsewhere_skipped(self):
        self.skill("a")
        other = self.root / "other"
        other.mkdir()
        dest = self.root / ".agents" / "skills" / "a"
        dest.parent.mkdir(parents=True)
        os.symlink(str(other), str(dest))
        r = mirror.mirror(self.root)
        self.assertEqual(r["skipped"], ["a"])
        self.assertEqual(Path(os.readlink(dest)), other)

    def test_rerun_idempotent(self):
        self.skill("a")
        mirror.mirror(self.root)
        r = mirror.mirror(self.root)
        self.assertEqual(r, {"linked": [], "copied": [], "skipped": []})

    def test_symlink_unsupported_falls_back_to_copy(self):
        d = self.skill("a", "hello")
        (d / "sub").mkdir()
        (d / "sub" / "f.txt").write_text("f", encoding="utf-8")
        with mock.patch("os.symlink", side_effect=OSError):
            r = mirror.mirror(self.root)
            self.assertEqual(r["copied"], ["a"])
            dest = self.root / ".agents" / "skills" / "a"
            self.assertFalse(dest.is_symlink())
            self.assertTrue((dest / ".mirror-source").is_file())
            self.assertEqual((dest / "sub" / "f.txt").read_text(encoding="utf-8"), "f")
            r2 = mirror.mirror(self.root)
            self.assertEqual(r2, {"linked": [], "copied": [], "skipped": []})

    def test_copy_changed_source_not_overwritten(self):
        d = self.skill("a", "v1")
        with mock.patch("os.symlink", side_effect=OSError):
            mirror.mirror(self.root)
            (d / "SKILL.md").write_text("v2", encoding="utf-8")
            r = mirror.mirror(self.root)
        self.assertEqual(r["skipped"], ["a"])
        dest = self.root / ".agents" / "skills" / "a"
        self.assertEqual((dest / "SKILL.md").read_text(encoding="utf-8"), "v1")

    def test_copy_does_not_follow_symlinks(self):
        d = self.skill("a")
        secret = self.root / "secret.txt"
        secret.write_text("s", encoding="utf-8")
        os.symlink(str(secret), str(d / "link.txt"))
        real = os.symlink
        calls = []

        def fail_first(*a, **k):  # 只讓鏡像那次建 link 失敗；copytree 還原 symlink 要正常
            if not calls:
                calls.append(1)
                raise OSError
            return real(*a, **k)

        with mock.patch("os.symlink", side_effect=fail_first):
            mirror.mirror(self.root)
        copied = self.root / ".agents" / "skills" / "a" / "link.txt"
        self.assertTrue(copied.is_symlink())

    def test_copy_failure_removes_partial(self):
        self.skill("a")
        with mock.patch("os.symlink", side_effect=OSError), \
                mock.patch("mirror._write_marker", side_effect=OSError("boom")):
            r = mirror.mirror(self.root)
        self.assertEqual(r["skipped"], ["a"])
        self.assertFalse((self.root / ".agents" / "skills" / "a").exists())


class TestCjk(MirrorBase):
    dirname = "我的 專案"

    def test_path_with_space_and_cjk(self):
        self.skill("技能 一", "內容")
        git("init", "-q", str(self.root))
        r = mirror.mirror(self.root)
        self.assertEqual(r["linked"], ["技能 一"])
        link = self.root / ".agents" / "skills" / "技能 一"
        self.assertEqual((link / "SKILL.md").read_text(encoding="utf-8"), "內容")
        added = mirror.exclude(self.root, [".agents/skills/技能 一"])
        self.assertEqual(added, ["/.agents/skills/技能 一"])
        text = (self.root / ".git" / "info" / "exclude").read_text(encoding="utf-8")
        self.assertIn("/.agents/skills/技能 一\n", text)


class TestExclude(MirrorBase):
    def setUp(self):
        super().setUp()
        git("init", "-q", str(self.root))
        self.file = self.root / ".git" / "info" / "exclude"

    def test_exclude_idempotent(self):
        self.assertEqual(mirror.exclude(self.root, [".agents/skills/a"]), ["/.agents/skills/a"])
        self.assertEqual(mirror.exclude(self.root, ["/.agents/skills/a"]), [])
        lines = self.file.read_text(encoding="utf-8").splitlines()
        self.assertEqual(lines.count("/.agents/skills/a"), 1)

    def test_unanchored_existing_line_counts_as_present(self):
        self.file.write_text(".pi/settings.json\n", encoding="utf-8")
        self.assertEqual(mirror.exclude(self.root, [".pi/settings.json"]), [])
        self.assertEqual(self.file.read_text(encoding="utf-8"), ".pi/settings.json\n")

    def test_preserves_existing_without_trailing_newline(self):
        self.file.write_text("# keep\n*.log", encoding="utf-8")
        mirror.exclude(self.root, ["x"])
        self.assertEqual(self.file.read_text(encoding="utf-8"), "# keep\n*.log\n/x\n")

    def test_dedupe_within_call(self):
        self.assertEqual(mirror.exclude(self.root, ["a", "a"]), ["/a"])

    def test_not_git_repo_errors_without_creating_git(self):
        plain = self.root.parent / "plain"
        plain.mkdir()
        with self.assertRaises(mirror.NotGitRepo):
            mirror.exclude(plain, ["a"])
        self.assertFalse((plain / ".git").exists())

    def test_git_file_worktree_style(self):
        wt = self.root.parent / "wt"
        gitdir = self.root.parent / "realgit"
        git("init", "-q", "--separate-git-dir", str(gitdir), str(wt))
        self.assertTrue((wt / ".git").is_file())
        with mock.patch.dict(os.environ, GIT_ENV):
            added = mirror.exclude(wt, ["a"])
        self.assertEqual(added, ["/a"])
        self.assertIn("/a\n", (gitdir / "info" / "exclude").read_text(encoding="utf-8"))


class TestExcludeSubdir(MirrorBase):
    def setUp(self):
        super().setUp()
        git("init", "-q", str(self.root))
        self.sub = self.root / "sub"
        self.sub.mkdir()

    def test_subdir_lines_anchored_to_toplevel(self):
        added = mirror.exclude(self.sub, [".agents/skills/x", "AGENTS.md"])
        self.assertEqual(added, ["/sub/.agents/skills/x", "/sub/AGENTS.md"])
        text = (self.root / ".git" / "info" / "exclude").read_text(encoding="utf-8")
        self.assertIn("/sub/AGENTS.md\n", text)
        self.assertEqual(mirror.exclude(self.sub, ["AGENTS.md"]), [])

    def test_subdir_really_ignored(self):
        (self.sub / "AGENTS.md").write_text("x", encoding="utf-8")
        mirror.exclude(self.sub, ["AGENTS.md"])
        out = subprocess.run(["git", "status", "--short"], cwd=self.root, env=GIT_ENV,
                             capture_output=True, text=True).stdout
        self.assertEqual(out.strip(), "")

    def test_subdir_not_confused_by_toplevel_line(self):
        f = self.root / ".git" / "info" / "exclude"
        f.write_text("/AGENTS.md\n", encoding="utf-8")
        self.assertEqual(mirror.exclude(self.sub, ["AGENTS.md"]), ["/sub/AGENTS.md"])


class TestAnchorNormalize(MirrorBase):
    def setUp(self):
        super().setUp()
        git("init", "-q", str(self.root))
        self.file = self.root / ".git" / "info" / "exclude"

    def test_leading_dot_slash_and_trailing_slash(self):
        self.assertEqual(mirror.exclude(self.root, ["./x", "y/"]), ["/x", "/y"])

    def test_existing_trailing_slash_line_counts_as_present(self):
        self.file.write_text(".agents/plugharbor/\n", encoding="utf-8")
        self.assertEqual(mirror.exclude(self.root, [".agents/plugharbor"]), [])
        self.assertEqual(mirror.exclude(self.root, ["./.agents/plugharbor/"]), [])

    def test_dot_slash_equals_plain_in_one_call(self):
        self.assertEqual(mirror.exclude(self.root, ["./a", "a", "a/"]), ["/a"])

    def test_symlink_with_trailing_slash_really_ignored(self):
        self.skill("s")
        mirror.mirror(self.root)
        mirror.exclude(self.root, [".agents/skills/s/", ".claude/skills/s/"])
        out = subprocess.run(["git", "status", "--short"], cwd=self.root, env=GIT_ENV,
                             capture_output=True, text=True).stdout
        self.assertEqual(out.strip(), "")


class TestOutsideProject(MirrorBase):
    def test_symlinked_agents_dir_outside_is_skipped(self):
        self.skill("a")
        outside = self.root.parent / "outside"
        outside.mkdir()
        os.symlink(str(outside), str(self.root / ".agents"))
        r = mirror.mirror(self.root)
        self.assertEqual(r, {"linked": [], "copied": [], "skipped": ["a"]})
        self.assertEqual(list(outside.iterdir()), [])

    def test_symlinked_agents_skills_outside_is_skipped(self):
        self.skill("a")
        outside = self.root.parent / "outside"
        outside.mkdir()
        (self.root / ".agents").mkdir()
        os.symlink(str(outside), str(self.root / ".agents" / "skills"))
        self.assertEqual(mirror.mirror(self.root)["skipped"], ["a"])
        self.assertEqual(list(outside.iterdir()), [])


class TestCliEncoding(MirrorBase):
    def test_cli_utf8_stdout_even_if_locale_ascii(self):
        self.skill("技能")
        env = dict(os.environ, LC_ALL="C", LANG="C", PYTHONUTF8="0", PYTHONCOERCECLOCALE="0")
        env.pop("PYTHONIOENCODING", None)
        p = subprocess.run([sys.executable, str(Path(__file__).parent / "mirror.py"), str(self.root)],
                           capture_output=True, env=env)
        self.assertEqual(p.returncode, 0, p.stderr.decode("utf-8", "replace"))
        self.assertIn("技能", p.stdout.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
