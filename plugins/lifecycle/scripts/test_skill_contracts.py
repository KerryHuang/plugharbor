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

    def test_pi_ask_tool_name_matches_installed_extension(self):
        # pi 的提問擴充（rpiv-ask-user-question）註冊的工具名是 ask_user_question，沒有 ask_user
        import re
        for rel in ["references/harness-terms.md", "skills/prototype-html/SKILL.md"]:
            self.assertIsNone(re.search(r"`ask_user`", read(rel)), rel)
        self.assertIn("`ask_user_question`", read("references/harness-terms.md"))

    def test_harness_terms_pointer_is_relative(self):
        # pi 不展開 ${CLAUDE_PLUGIN_ROOT}，指向對照檔的那一句要用相對路徑
        for skill in ["qa-verify", "prototype-html", "ticket-ops"]:
            self.assertIn("../../" + "references/harness-terms.md", read(f"skills/{skill}/SKILL.md"), skill)

    def test_no_removed_scale_or_explore_in_shared_refs(self):
        self.assertNotIn("full 規格", read("references/shared-preludes.md"))
        self.assertNotIn("`explore`", read("references/analysis-rigor.md"))

    def test_spec_check_applies_legacy_parity(self):
        # legacy-parity 說 spec-check 讀到「舊系統移植」表頭就套用，spec-check 要真的引用它
        self.assertIn("legacy-parity.md", read("skills/spec-check/SKILL.md"))

    def test_no_relay_era_wording(self):
        for rel, word in [("references/shared-preludes.md", "每棒"), ("references/shared-preludes.md", "交棒前清零"),
                          ("references/shared-preludes-details.md", "每棒"),
                          ("skills/triage/references/ticket-flow.md", "`scale`"),
                          ("skills/spec-check/references/modes/sample.md", "SPEC-INDEX"),
                          ("skills/spec-check/references/modes/sample.md", "規格所在功能目錄"),
                          ("agents/spec-sampler.md", "SPEC-INDEX"),
                          ("references/consultant-desk.md", "該階段正式文件")]:
            self.assertNotIn(word, read(rel), rel)


if __name__ == "__main__":
    unittest.main()
