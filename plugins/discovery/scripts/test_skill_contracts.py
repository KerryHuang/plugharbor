#!/usr/bin/env python3
"""discovery 的 skill 接點契約：一方產出、另一方讀取的字樣要對得上。"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


class SkillContracts(unittest.TestCase):
    def test_pi_ask_tool_name_matches_installed_extension(self):
        # pi 的提問擴充註冊的工具名是 ask_user_question，沒有 ask_user
        self.assertIsNone(re.search(r"`ask_user`", read("skills/prototype-html/SKILL.md")))

    def test_harness_terms_pointer_is_relative(self):
        # pi 不展開 ${CLAUDE_PLUGIN_ROOT}，指向對照檔的那一句要用相對路徑
        self.assertIn("../../" + "references/harness-terms.md", read("skills/prototype-html/SKILL.md"))

    def test_relay_era_module_paths_gone(self):
        self.assertNotIn("§Step 0.5", read("skills/interview-prep/SKILL.md"))


if __name__ == "__main__":
    unittest.main()
