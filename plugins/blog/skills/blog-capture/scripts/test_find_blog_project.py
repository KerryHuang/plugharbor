# -*- coding: utf-8 -*-
"""find_blog_project 測試：用暫存目錄模擬 ~/.claude.json 與專案。"""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from find_blog_project import find  # noqa: E402


class FindBlogProjectTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = os.path.realpath(self.tmp.name)
        self.cj = os.path.join(self.root, "claude.json")

    def tearDown(self):
        self.tmp.cleanup()

    def mkproject(self, name, posts):
        p = os.path.join(self.root, name)
        os.makedirs(os.path.join(p, ".claude", "rules"))
        if posts:
            open(os.path.join(p, ".claude", "rules", "posts.md"), "w", encoding="utf-8").close()
        return p

    def write(self, paths):
        with open(self.cj, "w", encoding="utf-8") as f:
            json.dump({"projects": {p: {} for p in paths}}, f)

    def test_only_projects_with_posts_rules(self):
        blog = self.mkproject("blog", True)
        other = self.mkproject("app", False)
        self.write([other, blog, os.path.join(self.root, "gone")])
        self.assertEqual(find(self.cj), [blog])

    def test_multiple_hits_sorted(self):
        b = self.mkproject("b-site", True)
        a = self.mkproject("a-site", True)
        self.write([b, a])
        self.assertEqual(find(self.cj), [a, b])

    def test_missing_or_broken_json(self):
        self.assertEqual(find(os.path.join(self.root, "nope.json")), [])
        with open(self.cj, "w", encoding="utf-8") as f:
            f.write("{broken")
        self.assertEqual(find(self.cj), [])


if __name__ == "__main__":
    unittest.main()
