#!/usr/bin/env python3
"""守門：四份文件規格鏈（lifecycle 3.0.0 移除）不得殘留在 plugin 內容裡。"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

REMOVED_SKILLS = ["spec-chain", "explore", "consolidate-docs", "write-doc", "dev-feedback"]
BANNED = [r"lifecycle:(explore|spec-chain|consolidate-docs|write-doc|dev-feedback)\b",
          r"scale:\s*full", r"--stage\s+(frd|sad|bfs|ffs|index)",
          r"\b(FRD|SAD|BFS|FFS)\b"]
SCAN_DIRS = ["skills", "agents", "references", "templates"]
EXTS = {".md", ".py", ".json"}
SELF = Path(__file__).resolve()


def scanned_files():
    files = [ROOT / "README.md"]
    for d in SCAN_DIRS:
        files += [p for p in (ROOT / d).rglob("*") if p.is_file() and p.suffix in EXTS]
    return [p for p in files if p.is_file() and p.name != "CHANGELOG.md" and p.resolve() != SELF]


class NoSpecChain(unittest.TestCase):
    def test_removed_skill_dirs_absent(self):
        left = [s for s in REMOVED_SKILLS if (ROOT / "skills" / s).exists()]
        self.assertEqual(left, [])

    def test_no_banned_tokens(self):
        pats = [re.compile(p) for p in BANNED]
        hits = []
        for p in scanned_files():
            for n, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if "allow-legacy" in line:
                    continue
                for pat in pats:
                    m = pat.search(line)
                    if m:
                        hits.append(f"{p.relative_to(ROOT)}:{n}: {m.group(0)}")
                        break
        self.assertEqual(hits, [], f"{len(hits)} 處殘留：\n" + "\n".join(hits[:80]))

    def test_no_orphan_files(self):
        targets = [p for p in (ROOT / "references").rglob("*") if p.is_file()]
        targets += [p for p in (ROOT / "templates").rglob("*") if p.is_file()]
        targets += [p for p in (ROOT / "skills").glob("*/references/**/*") if p.is_file()]
        corpus = {p: p.read_text(encoding="utf-8", errors="replace")
                  for p in ROOT.rglob("*")
                  if p.is_file() and p.suffix in EXTS | {".sh", ".yml", ".js"} and p.name != "CHANGELOG.md"}
        orphans = []
        for t in targets:
            if not any(t.stem in text for p, text in corpus.items() if p != t):
                orphans.append(str(t.relative_to(ROOT)))
        self.assertEqual(orphans, [])

    def test_spec_writer_agent_removed(self):
        self.assertFalse((ROOT / "agents" / "spec-writer.md").exists())

    def test_config_has_no_scale_default(self):
        import config
        self.assertNotIn("scale", config.DEFAULTS)


if __name__ == "__main__":
    unittest.main()
