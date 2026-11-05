"""harvest.py 測試：網址拆解與鎖定檔。用本機 git repo 當上游，不連網。"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("harvest.py")
GIT_ENV = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com"}


def run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True,
                          text=True, encoding="utf-8", env=GIT_ENV)


def parse(url):
    r = run("parse-url", url)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, env=GIT_ENV)


def commit(repo, name):
    (Path(repo) / name).write_text(name + "\n", encoding="utf-8")
    git(repo, "add", name)
    git(repo, "commit", "-q", "-m", name)


def head(repo):
    return subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True,
                          text=True, check=True).stdout.strip()


class HarvestTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.up = self.tmp / "up"
        self.up_nolicense = self.tmp / "up2"
        for repo in (self.up, self.up_nolicense):
            repo.mkdir()
            git(repo, "init", "-q", "-b", "main")
            commit(repo, "README.md")
        commit(self.up, "LICENSE")
        self.lock = self.tmp / "harvest-lock.json"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def add(self, target="research:ai-radar", up=None):
        up = up or self.up
        r = run("lock", "add", str(self.lock), "--url", str(up), "--clone", str(up),
                "--version", "-", "--license", "MIT", "--target", target, "--date", "2026-11-05")
        self.assertEqual(r.returncode, 0, r.stderr)
        return self.entries()[-1]

    def entries(self):
        return json.loads(self.lock.read_text(encoding="utf-8"))["entries"]

    def check(self):
        return run("lock", "check", str(self.lock))

    def test_parse_url_github_tree_subpath(self):
        j = parse("https://github.com/Owner/Repo/tree/main/plugins/x/")
        self.assertEqual(j, {"clone_url": "https://github.com/Owner/Repo.git", "ref": "main",
                             "subpath": "plugins/x", "key": "owner/repo/plugins/x"})

    def test_parse_url_dot_git_and_slash(self):
        self.assertEqual(parse("https://github.com/o/r.git/")["key"], "o/r")
        self.assertEqual(parse("https://github.com/o/r")["ref"], "")

    def test_parse_url_other_host(self):
        j = parse("https://gitlab.com/g/sub/r")
        self.assertEqual((j["clone_url"], j["key"]), ("https://gitlab.com/g/sub/r.git", "g/sub/r"))

    def test_parse_url_local_path(self):
        self.assertEqual(parse(str(self.up))["clone_url"], str(self.up.resolve()))

    def test_parse_url_query_and_fragment(self):
        for u in ("https://github.com/o/r?tab=readme-ov-file", "https://github.com/o/r#readme"):
            j = parse(u)
            self.assertEqual((j["clone_url"], j["key"]), ("https://github.com/o/r.git", "o/r"))

    def test_parse_url_blob_file(self):
        j = parse("https://github.com/o/r/blob/main/skills/x/SKILL.md")
        self.assertEqual((j["clone_url"], j["ref"], j["subpath"], j["key"]),
                         ("https://github.com/o/r.git", "main", "skills/x", "o/r/skills/x"))

    def test_parse_url_www_host(self):
        self.assertEqual(parse("https://www.github.com/o/r")["clone_url"], "https://github.com/o/r.git")

    def set_ref(self, ref):
        data = json.loads(self.lock.read_text(encoding="utf-8"))
        data["entries"][0]["ref"] = ref
        self.lock.write_text(json.dumps(data), encoding="utf-8")

    def test_lock_check_annotated_tag_same(self):
        git(self.up, "tag", "-a", "v1", "-m", "v1")
        self.add()
        self.set_ref("v1")
        r = self.check()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(r.stdout.startswith("SAME"))

    def test_lock_check_pinned_sha(self):
        self.add()
        self.set_ref(head(self.up))
        commit(self.up, "x.md")
        r = self.check()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(r.stdout.startswith("PINNED"))

    def test_parse_url_garbage_exit2(self):
        self.assertEqual(run("parse-url", "not a url").returncode, 2)

    def test_lock_add_records_commit_and_license(self):
        e = self.add()
        self.assertEqual(e["commit"], head(self.up))
        self.assertEqual(e["license_file"], "LICENSE")
        self.assertEqual(e["targets"], ["research:ai-radar"])

    def test_lock_add_same_key_merges_targets(self):
        self.add(target="research:ai-radar")
        self.add(target="lifecycle:spec")
        self.assertEqual(len(self.entries()), 1)
        self.assertEqual(self.entries()[0]["targets"], ["lifecycle:spec", "research:ai-radar"])

    def test_lock_check_same_exit0(self):
        self.add()
        r = self.check()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(r.stdout.startswith("SAME"))

    def test_lock_check_updated(self):
        self.add()
        commit(self.up, "x.md")
        r = self.check()
        self.assertEqual(r.returncode, 3)
        self.assertIn("UPDATED", r.stdout)
        self.assertNotIn("LICENSE-CHANGED", r.stdout)

    def test_lock_check_license_added(self):
        self.add(up=self.up_nolicense)
        self.assertIsNone(self.entries()[0]["license_file"])
        commit(self.up_nolicense, "LICENSE")
        self.assertIn("LICENSE-CHANGED", self.check().stdout)

    def test_lock_check_unreachable(self):
        self.add()
        shutil.rmtree(self.up)
        r = self.check()
        self.assertEqual(r.returncode, 3)
        self.assertIn("UNREACHABLE", r.stdout)

    def test_lock_check_no_lock(self):
        r = run("lock", "check", str(self.tmp / "none.json"))
        self.assertEqual((r.returncode, r.stdout.strip()), (0, "NO-LOCK"))


if __name__ == "__main__":
    unittest.main()
