#!/usr/bin/env python3
"""tickets 的 skill 接點契約：一方產出、另一方讀取的字樣要對得上。"""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


class SkillContracts(unittest.TestCase):
    def test_no_relay_era_wording(self):
        self.assertNotIn("`scale`", read("skills/triage/references/ticket-flow.md"))

    def test_harness_terms_pointer_is_relative(self):
        # pi 不展開 ${CLAUDE_PLUGIN_ROOT}，指向對照檔的那一句要用相對路徑
        self.assertIn("../../" + "references/harness-terms.md", read("skills/ticket-ops/SKILL.md"))

    def test_reconcile_finds_checklist_parser(self):
        # reconcile.py 以 parents[3]/scripts/feature_checklist.py 找清單解析器
        self.assertTrue((ROOT / "scripts" / "feature_checklist.py").exists())
        self.assertIn("parents[3]", read("skills/ticket-ops/scripts/reconcile.py"))


if __name__ == "__main__":
    unittest.main()
