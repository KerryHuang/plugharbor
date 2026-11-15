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
        self.assertIsNone(re.search(r"`ask_user`", read("references/harness-terms.md")))
        self.assertIn("`ask_user_question`", read("references/harness-terms.md"))

    def test_harness_terms_pointer_is_relative(self):
        # pi 不展開 ${CLAUDE_PLUGIN_ROOT}，指向對照檔的那一句要用相對路徑
        self.assertIn("../../" + "references/harness-terms.md", read("skills/qa-verify/SKILL.md"))

    def test_no_removed_scale_or_explore_in_shared_refs(self):
        self.assertNotIn("full 規格", read("references/shared-preludes.md"))
        self.assertNotIn("`explore`", read("references/analysis-rigor.md"))

    def test_spec_check_applies_legacy_parity(self):
        # legacy-parity 說 spec-check 讀到「舊系統移植」表頭就套用，spec-check 要真的引用它
        self.assertIn("legacy-parity.md", read("skills/spec-check/SKILL.md"))

    def test_no_relay_era_wording(self):
        for rel, word in [("references/shared-preludes.md", "每棒"), ("references/shared-preludes.md", "交棒前清零"),
                          ("references/shared-preludes-details.md", "每棒"),
                          ("skills/spec-check/references/modes/sample.md", "SPEC-INDEX"),
                          ("skills/spec-check/references/modes/sample.md", "規格所在功能目錄"),
                          ("agents/spec-sampler.md", "SPEC-INDEX"),
                          ("references/consultant-desk.md", "該階段正式文件")]:
            self.assertNotIn(word, read(rel), rel)

    def test_pointer_survives_symlink_and_copy_install(self):
        # .agents/skills/<skill> 是 symlink 或複製：../../ 要從實體路徑算，否則解到 .agents/references（試用 pi 實測 ENOENT）
        files = []
        for plugin in ["lifecycle", "browser-docs", "tickets", "discovery", "delivery"]:
            self.assertTrue((ROOT.parent / plugin / "skills").is_dir(), plugin)
            files += (ROOT.parent / plugin / "skills").glob("*/SKILL.md")
        for f in sorted(files):
            head = f.read_text(encoding="utf-8")[:2000]
            self.assertIn("../../" + "references/harness-terms.md", head, f.parent.name)
            self.assertIn("realpath", head, f.parent.name)

    def test_harness_terms_scope_names_agy_and_path_rule_applies_everywhere(self):
        head = read("references/harness-terms.md")[:800]
        self.assertIn("agy", head)
        self.assertIn("所有 harness", head)

    def test_spec_dir_resolved_once_and_shared(self):
        # 只有 spec 改用專案目錄、其他 skill 只讀 config.py → implement／spec-check 找不到規格（S2、S3）
        s = read("skills/spec/SKILL.md")
        self.assertNotIn("回報時建議寫進", s)
        self.assertIn("寫進 `.plugharbor/lifecycle.yml` 的 `spec.dir`", s)
        self.assertIn("spec:\n  dir:", s)  # 寫明巢狀格式
        self.assertIn("其他鍵不動", s)
        self.assertIn("spec:\n  dir:", read("references/config.md"))

    def test_project_sections_do_not_shift_changelog_number(self):
        s = read("skills/spec/SKILL.md")
        self.assertNotIn("照加在 §6 之後", s)
        self.assertIn("§6 與 §7 之間", s)

    def test_spec_names_only_existing_downstream_skills(self):
        self.assertNotIn("`review`", read("skills/spec/SKILL.md"))

    def test_implement_clean_tree_rule_is_consistent(self):
        s = read("skills/implement/SKILL.md")
        self.assertNotIn("（spec 不 commit）", s)
        self.assertIn("`.tmp/`", s)

    def test_config_doc_matches_scale_notice_behavior(self):
        self.assertNotIn("固定回 `lean` 並在 stderr 提示", read("references/config.md"))


    def test_any_edit_after_spec_check_bumps_version(self):
        # 免重跑只比版本號：通過後改內容不 +1 就會被誤判沒改過
        self.assertIn("通過後再改任何內容", read("skills/spec-check/SKILL.md"))

    def test_relay_era_module_paths_gone(self):
        self.assertNotIn("需求文件.md", read("agents/scout.md"))
        self.assertNotIn("_context.yml", read("skills/spec-check/references/sample/impl-anchors.md"))


    def test_spec_lookup_tolerates_dated_filenames(self):
        # 檔名可照慣例加日期前綴（S10），用短名找 <spec.dir>/<feature>.md 會落空
        for rel in ["skills/spec-check/SKILL.md", "skills/implement/SKILL.md"]:
            self.assertIn("*<feature>*", read(rel), rel)

    def test_config_doc_records_spec_dir_rule(self):
        self.assertIn("專案規則", read("references/config.md"))

    def test_spec_check_says_how_to_validate_cases(self):
        self.assertIn("升兩級", read("skills/spec-check/SKILL.md"))


    def test_text_only_conversion_runs_before_env_preflight(self):
        # Codex、S6、pi 都卡在：轉檔與 validate 是純文字，卻要先補環境與瀏覽器
        s = read("skills/qa-verify/SKILL.md")
        self.assertLess(s.index("先做 Step 1 的轉檔與 validate"), s.index("preflight.sh"))

    def test_harness_terms_web_row_does_not_name_missing_gateway(self):
        self.assertNotIn("經 `mcp` gateway", read("references/harness-terms.md"))

    def test_dispatch_conventions_defer_to_skill_steps(self):
        self.assertIn("以 skill 為準", read("references/dispatch-conventions.md"))

    def test_dependency_check_handles_unprefixed_names(self):
        self.assertIn("不帶前綴", read("references/shared-preludes.md"))


    def test_ask_rule_allows_text_fallback_without_tool(self):
        # 寫死「必用 AskUserQuestion、不可純文字」，沒有提問工具的 harness 會無路可走（agy 試用）
        self.assertNotIn("1. 必用 `AskUserQuestion`，不可用純文字選單模擬。", read("references/shared-preludes-details.md"))

    def test_optional_deps_cover_split_plugins(self):
        s = read("references/shared-preludes.md")
        for name in ("`tickets:ticket-ops`", "`lifecycle:spec`", "`discovery:meeting-minutes`",
                     "`lifecycle:spec`、`spec-check`、`implement`", "`tickets:triage`",
                     "顧問 `lifecycle:domain-advisor`、勘察 `lifecycle:scout`"):
            self.assertIn(name, s)

    def test_only_mainline_skills_remain(self):
        self.assertEqual(sorted(p.name for p in (ROOT / "skills").iterdir() if p.is_dir()),
                         ["implement", "qa-verify", "release", "spec", "spec-check"])


if __name__ == "__main__":
    unittest.main()
