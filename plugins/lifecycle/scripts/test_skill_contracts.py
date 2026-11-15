#!/usr/bin/env python3
"""skill 之間的接點契約：一方產出、另一方讀取的字樣要對得上（3.0.0 試用發現的斷點）。"""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


class SkillContracts(unittest.TestCase):
    def test_spec_check_pass_record_is_persisted_and_read(self):
        # spec-check 通過要留在規格表頭，implement 才能跨 session 判斷不重跑
        self.assertIn("| 規格檢查 |", read("skills/spec/references/lean-template.md"))
        self.assertIn("| 規格檢查 |", read("skills/spec-check/SKILL.md"))
        self.assertIn("| 規格檢查 |", read("skills/implement/SKILL.md"))

    def test_case_sha_untracked_uses_shasum(self):
        # .tmp/qa/ 轉出的案例檔沒被 git 追蹤，git log 會回空字串
        self.assertIn("git ls-files --error-unmatch", read("skills/qa-verify/SKILL.md"))

    def test_spec_to_acceptance_checks_tmp_ignored(self):
        self.assertIn("git check-ignore", read("skills/qa-verify/references/spec-to-acceptance.md"))

    def test_template_warns_api_cases_not_run(self):
        self.assertIn("[api]", read("skills/spec/references/lean-template.md"))

    def test_spec_follows_project_required_sections(self):
        self.assertIn("專案規則規定的必要章節", read("skills/spec/SKILL.md"))

    def test_implement_no_scale_passthrough(self):
        self.assertNotIn("`scale`", read("skills/implement/SKILL.md"))


if __name__ == "__main__":
    unittest.main()
