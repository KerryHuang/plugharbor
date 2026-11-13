#!/usr/bin/env python3
"""vendor.py 的測試：python3 test_vendor.py"""
import json
import os
import shutil
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
    'THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.\n'
)
ASIS = 'THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.'
ISC = ("Permission to use, copy, modify, and/or distribute this software for any purpose "
       "with or without fee is hereby granted, provided that the above copyright notice "
       "and this permission notice appear in all copies. " + ASIS)
ZERO = ("Permission to use, copy, modify, and/or distribute this software for any purpose "
        "with or without fee is hereby granted. " + ASIS)
BSD2 = ("Redistribution and use in source and binary forms, with or without modification, "
        "are permitted provided that: Redistributions of source code must retain the notice. "
        "Redistributions in binary form must reproduce the notice. "
        'THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS".')
BSD3 = BSD2.replace("THIS SOFTWARE", "Neither the name of the author may be used. THIS SOFTWARE")
BSD4 = BSD3 + " All advertising materials mentioning features must display acknowledgement."
UNLICENSE = """This is free and unencumbered software released into the public domain.

Anyone is free to copy, modify, publish, use, compile, sell, or
distribute this software, either in source code form or as a compiled
binary, for any purpose, commercial or non-commercial, and by any
means.

In jurisdictions that recognize copyright laws, the author or authors
of this software dedicate any and all copyright interest in the
software to the public domain.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.

For more information, please refer to <https://unlicense.org>
"""
CC0 = """Creative Commons Legal Code

CC0 1.0 Universal

Statement of Purpose

The laws of most jurisdictions throughout the world automatically confer
exclusive Copyright and Related Rights upon the creator of a Work.

1. Copyright and Related Rights. A Work made available under CC0 may be
protected by copyright and related or neighboring rights.

2. Waiver. To the greatest extent permitted by, but not in contravention
of, applicable law, Affirmer hereby overtly, fully, permanently,
irrevocably and unconditionally waives, abandons, and surrenders all of
Affirmer's Copyright and Related Rights.

3. Public License Fallback. Should any part of the Waiver for any reason
be judged legally invalid or ineffective under applicable law, then the
Waiver shall be preserved to the maximum extent permitted.
(Abridged: the full CC0 legal code is longer; distinctive sections kept.)
"""
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
        w(self.repo / "LICENSE", "Apache License\nVersion 2.0, January 2004\nTERMS AND CONDITIONS FOR USE\n")
        self.assertEqual(self.run_vendor()["license"], "Apache-2.0")

    def lic(self, text):
        w(self.repo / "LICENSE", text)
        return self.run_vendor()

    def test_licenses_positive(self):
        for text, name in [(ISC, "ISC"), (ZERO, "0BSD"), (BSD2, "BSD-2-Clause"), (BSD3, "BSD-3-Clause"),
                           (UNLICENSE, "Unlicense"), (CC0, "CC0-1.0")]:
            with self.subTest(name):
                shutil.rmtree(self.proj / ".claude", ignore_errors=True)
                self.assertEqual(self.lic(text).get("license"), name)

    def test_loose_matches_rejected(self):
        for text in [GPL + "compatible with Apache License Version 2.0 TERMS AND CONDITIONS",
                     MIT + " Commons Clause License Condition",
                     MIT + " for non-commercial purposes only",
                     MIT + " NonCommercial use",
                     MIT + " for non-commercial use only",
                     BSD4]:
            self.assertEqual(self.lic(text)["status"], "pending")

    def test_multiple_license_files(self):
        w(self.repo / "LICENSE-APACHE", "Apache License\nVersion 2.0\nTERMS AND CONDITIONS\n")
        w(self.repo / "LICENSE-MIT", MIT)
        (self.repo / "LICENSE").unlink()
        r = self.run_vendor()
        self.assertEqual(r["status"], "installed")
        self.assertEqual(r["license"], "Apache-2.0 / MIT")

    def test_mixed_license_files_pending(self):
        w(self.repo / "LICENSE", MIT)
        w(self.repo / "COPYING", GPL)
        self.assertEqual(self.run_vendor()["status"], "pending")

    def test_symlinks_pending(self):
        outside = Path(self.tmp.name) / "outside.txt"
        w(outside, "o")
        cases = {"file": outside, "dir": Path(self.tmp.name), "dangling": Path(self.tmp.name) / "nope"}
        for name, target in cases.items():
            with self.subTest(name):
                link = self.skill / f"link-{name}"
                os.symlink(target, link)
                r = self.run_vendor()
                self.assertEqual(r["status"], "pending")
                self.assertTrue(any("symlink" in s for s in r["reasons"]))
                self.assertFalse((self.proj / ".claude").exists())
                link.unlink()

    def test_skill_dir_symlink_pending(self):
        link = Path(self.tmp.name) / "linked"
        os.symlink(self.skill, link)
        r = vendor.vendor(link, self.proj, SRC)
        self.assertEqual(r["status"], "pending")
        self.assertTrue(any("symlink" in s for s in r["reasons"]))

    def test_script_file_and_case_dirs_pending(self):
        w(self.skill / "references" / "foo.sh", "echo")
        self.assertTrue(any("executable" in s for s in self.run_vendor()["reasons"]))
        (self.skill / "references" / "foo.sh").unlink()
        w(self.skill / "references" / "tool", "#!/bin/sh\n")
        self.assertTrue(any("executable" in s for s in self.run_vendor()["reasons"]))
        (self.skill / "references" / "tool").unlink()
        w(self.skill / "Scripts" / "a.md", "x")
        self.assertTrue(any("scripts" in s for s in self.run_vendor()["reasons"]))

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
