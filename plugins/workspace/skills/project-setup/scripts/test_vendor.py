#!/usr/bin/env python3
"""vendor.py 的測試：python3 test_vendor.py"""
import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import vendor  # noqa: E402

MIT = (
    "MIT License\n\nPermission is hereby granted, free of charge, to any person "
    "obtaining a copy of this software...\n"
)
GPL = "GNU GENERAL PUBLIC LICENSE\nVersion 3, 29 June 2007\n"
SRC = {"repo": "https://example.com/o/r", "commit": "abc123", "path": "skills/x"}


def w(p, text="x"):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


class VendorTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.repo = base / "repo"
        self.skill = self.repo / "skills" / "x"
        self.proj = base / "proj"
        self.proj.mkdir()
        (self.repo / ".git").mkdir(parents=True)
        w(self.skill / "SKILL.md", "# x")
        w(self.skill / "references" / "a.md", "a")
        w(self.repo / "LICENSE", MIT)

    def tearDown(self):
        self.tmp.cleanup()

    def run_vendor(self):
        return vendor.vendor(self.skill, self.proj, SRC)

    def test_pure_mit_installs(self):
        r = self.run_vendor()
        self.assertEqual(r["status"], "installed")
        self.assertEqual(r["license"], "MIT")
        dest = Path(r["dest"])
        self.assertTrue((dest / "SKILL.md").is_file())
        self.assertTrue((dest / "references" / "a.md").is_file())
        meta = json.loads((dest / ".source.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["license"], "MIT")
        self.assertEqual(meta["commit"], "abc123")

    def test_scripts_dir_pending(self):
        w(self.skill / "scripts" / "x.py")
        r = self.run_vendor()
        self.assertEqual(r["status"], "pending")
        self.assertTrue(any("scripts" in s for s in r["reasons"]))

    def test_executable_file_pending(self):
        p = self.skill / "references" / "a.md"
        os.chmod(p, os.stat(p).st_mode | stat.S_IXUSR)
        r = self.run_vendor()
        self.assertEqual(r["status"], "pending")
        self.assertTrue(any("executable" in s for s in r["reasons"]))

    def test_hooks_or_mcp_pending(self):
        w(self.skill / "hooks" / "hooks.json", "{}")
        self.assertEqual(self.run_vendor()["status"], "pending")
        (self.skill / "hooks" / "hooks.json").unlink()
        (self.skill / "hooks").rmdir()
        w(self.skill / "sub" / ".mcp.json", "{}")
        self.assertEqual(self.run_vendor()["status"], "pending")

    def test_no_license_pending(self):
        (self.repo / "LICENSE").unlink()
        r = self.run_vendor()
        self.assertEqual(r["status"], "pending")
        self.assertTrue(any("license" in s for s in r["reasons"]))

    def test_gpl_pending(self):
        w(self.repo / "LICENSE", GPL)
        r = self.run_vendor()
        self.assertEqual(r["status"], "pending")
        self.assertTrue(any("license" in s for s in r["reasons"]))

    def test_collects_all_reasons(self):
        w(self.skill / "scripts" / "x.py")
        w(self.repo / "LICENSE", GPL)
        r = self.run_vendor()
        self.assertGreaterEqual(len(r["reasons"]), 2)

    def test_apache_installs(self):
        w(self.repo / "LICENSE", "Apache License\nVersion 2.0, January 2004\n")
        self.assertEqual(self.run_vendor()["license"], "Apache-2.0")

    def test_license_found_at_repo_root(self):
        self.assertFalse(list(self.skill.glob("LICENSE*")))
        self.assertEqual(self.run_vendor()["status"], "installed")

    def test_existing_dest_skipped(self):
        dest = self.proj / ".claude" / "skills" / "x"
        w(dest / "keep.txt", "old")
        r = self.run_vendor()
        self.assertEqual(r, {"status": "skipped", "reason": "exists"})
        self.assertEqual((dest / "keep.txt").read_text(encoding="utf-8"), "old")
        self.assertFalse((dest / "SKILL.md").exists())


if __name__ == "__main__":
    unittest.main()
