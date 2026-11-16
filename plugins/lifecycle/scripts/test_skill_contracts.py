#!/usr/bin/env python3
"""skill 之間的接點契約：一方產出、另一方讀取的字樣要對得上（3.0.0 試用發現的斷點）。"""
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


class SkillContracts(unittest.TestCase):
    def test_spec_check_pass_record_is_persisted_and_read(self):
        # spec-check 通過要留在規格表頭，implement 才能跨 session 判斷不重跑
        self.assertIn("> 實作前檢查：", read("skills/spec-check/SKILL.md"))
        self.assertIn("> 實作前檢查：", read("skills/implement/SKILL.md"))

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
        self.assertIn("放 `## 留給 builder` 之前", s)

    def test_spec_names_only_existing_downstream_skills(self):
        self.assertNotIn("`review`", read("skills/spec/SKILL.md"))

    def test_implement_clean_tree_rule_is_consistent(self):
        s = read("skills/implement/SKILL.md")
        self.assertNotIn("（spec 不 commit）", s)
        self.assertIn("`.tmp/`", s)
        self.assertIn("設計文件", s)

    def test_config_doc_matches_scale_notice_behavior(self):
        self.assertNotIn("固定回 `lean` 並在 stderr 提示", read("references/config.md"))


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
        t = read("skills/spec-check/SKILL.md")
        self.assertIn("spec_to_cases.py", t)
        self.assertIn("validate.py acceptance", t)

    def test_legacy_parity_marker_both_formats(self):
        # 移植標記新舊並存：觸發句要新舊都認（模型是否真的觸發屬行為，這裡只驗字樣；未驗證）
        for rel in ("references/legacy-parity.md", "skills/spec-check/SKILL.md", "skills/spec/SKILL.md"):
            t = read(rel)
            self.assertIn("來源：舊系統移植", t, rel)
            self.assertIn("來源｜舊系統移植", t, rel)
        self.assertIn("來源：舊系統移植", read("skills/spec/references/lean-template.md"))

    def test_shared_refs_use_new_sections(self):
        # 只有舊名的章節寫法會指向新範本不存在的章節；舊名只能以「（舊範本 §n）」括號別名出現
        import re
        plug = ROOT.parent
        files = [ROOT / "references" / n for n in ("shared-preludes.md", "shared-preludes-details.md",
                                                    "consultant-desk.md", "analysis-rigor.md", "legacy-parity.md")]
        files.append(plug / "tickets/skills/ticket-reply/SKILL.md")
        files.append(plug / "tickets/references/pipeline.md")
        bad = re.compile(r"§5 決策表|§7 變更|§2\.3|§3\.4")
        for f in files:
            for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                rest = re.sub(r"[（，]舊範本[^）]*）", "", line)
                self.assertIsNone(bad.search(rest), f"{f.name}:{n}: {line}")


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

    def test_template_sections_align_superpowers(self):
        t = read("skills/spec/references/lean-template.md")
        pos = -1
        for h in ("## 起因", "## 目標", "## 限制", "## 做法比較", "## 決定", "## 驗收", "## 留給 builder"):
            i = t.find("\n" + h, pos + 1)
            self.assertGreater(i, pos, h)
            pos = i
        for want in ("票號：", "### AC-01", "#### 步驟", "#### 預期", "（拍板：", "TD-01"):
            self.assertIn(want, t, want)
        for bad in ("##### ", "§2.3", "| 拍板 |"):
            self.assertNotIn(bad, t, bad)

    def test_agents_section_markers_and_contract(self):
        lines = read("templates/agents-md-section.md").rstrip("\n").split("\n")
        self.assertEqual(lines[0], "<!-- plugharbor-lifecycle begin -->")
        self.assertEqual(lines[-1], "<!-- plugharbor-lifecycle end -->")
        self.assertLessEqual(len(lines), 30)
        s = "\n".join(lines)
        for want in ("起因", "目標", "限制", "做法比較", "決定", "驗收", "留給 builder",
                     "lifecycle:implement", "docs/superpowers/plans/", "計畫審查", "### ",
                     "#### 預期", "lifecycle:release", "同步票"):
            self.assertIn(want, s, want)

    def test_spec_routes_by_superpowers(self):
        s = read("skills/spec/SKILL.md")
        for want in ("superpowers:brainstorming", "一次一題", "AskUserQuestion", "lean-template.md"):
            self.assertIn(want, s, want)

    def test_only_mainline_skills_remain(self):
        self.assertEqual(sorted(p.name for p in (ROOT / "skills").iterdir() if p.is_dir()),
                         ["implement", "qa-verify", "release", "spec", "spec-check"])

    def test_pass_record_hash_behavior(self):
        # implement 與 spec-check 的雜湊指令逐字相同；只改紀錄行不變，改正文就變
        cmds = []
        for rel in ("skills/implement/SKILL.md", "skills/spec-check/SKILL.md"):
            m = re.search(r"grep -v '\^> 實作前檢查：' <[^>]+> \| shasum \| cut -c1-8", read(rel))
            self.assertIsNotNone(m, rel)
            cmds.append(m.group(0))
        self.assertEqual(cmds[0], cmds[1])
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "x.md"

            def h():
                c = re.sub(r"<[^>]+>", str(f), cmds[0])
                return subprocess.run(c, shell=True, capture_output=True, text=True).stdout.strip()

            body = "# 功能\n票號：無 · 狀態：草稿 · 2026-11-16\n%s\n## 起因\n甲\n"
            f.write_text(body % "> 實作前檢查：✅ 2026-11-16（內容 aaaaaaaa）", encoding="utf-8")
            h1 = h()
            self.assertEqual(len(h1), 8)
            f.write_text(body % "> 實作前檢查：✅ 2026-12-01（內容 bbbbbbbb）", encoding="utf-8")
            self.assertEqual(h(), h1)
            f.write_text((body % "> 實作前檢查：✅ 2026-11-16（內容 aaaaaaaa）").replace("甲", "乙"), encoding="utf-8")
            self.assertNotEqual(h(), h1)

    def test_implement_has_no_learnings(self):
        for rel in ("skills/implement/SKILL.md", "skills/implement/references/after.md",
                    "skills/implement/references/fallback.md"):
            self.assertNotIn("LEARNINGS", read(rel), rel)

    def test_after_only_acceptance_and_backfill(self):
        t = read("skills/implement/references/after.md")
        heads = re.findall(r"^## .*$", t, re.M)
        self.assertEqual(len(heads), 2, heads)
        self.assertIn("驗收", heads[0])
        self.assertIn("回填", heads[1])
        for want in ("spec_to_cases.py", "同步票", "未設 ticket.tool"):
            self.assertIn(want, t, want)
        for bad in ("整合測試", "lifecycle:" + "debugger"):
            self.assertNotIn(bad, t, bad)

    def test_fallback_plan_same_format(self):
        t = read("skills/implement/references/fallback.md")
        for want in ("docs/superpowers/plans/", "**Goal:**", "**Architecture:**", "**Tech Stack:**",
                     "**Spec:**", "## Global Constraints", "## Review Focus", "**Interfaces:**",
                     "- [ ]", "自審"):
            self.assertIn(want, t, want)
        self.assertNotIn("lifecycle:reviewer", t)

    def test_both_paths_run_plan_review(self):
        for rel in ("skills/implement/SKILL.md", "skills/implement/references/fallback.md"):
            self.assertIn("plan-review.md", read(rel), rel)
        t = read("skills/implement/references/plan-review.md")
        for want in ("toolkit:agent-dispatch", "自審", "必修", "≥ 3"):
            self.assertIn(want, t, want)

    def test_plan_review_pinned_before_execution_handoff(self):
        # 審查要寫進交給 writing-plans 的引用指令，否則使用者一回覆就轉進執行
        t = read("skills/implement/SKILL.md")
        quote = "\n".join(l for l in t.splitlines() if l.startswith(">"))
        self.assertIn("plan-review.md", quote)
        self.assertIn("Execution Handoff", quote)
        self.assertIn("實際絕對路徑", t)

    def test_plan_and_review_not_skipped_for_small_changes(self):
        # e2e 起因：一個函式的小功能，兩條路徑都以「改動小」跳過 writing-plans、計畫檔或計畫審查
        self.assertIn("不因改動小而省略", read("skills/implement/SKILL.md"))
        self.assertIn("不因改動小而省略", read("skills/implement/references/fallback.md"))
        self.assertIn("不因計畫小而跳級", read("skills/implement/references/plan-review.md"))

    def test_agents_section_minimal_case_converts(self):
        # 直接 brainstorming 的使用者只看得到 AGENTS 段落：它的最小案例必須能被轉檔器收
        sec = read("templates/agents-md-section.md")
        m = re.search(r"^  ```\n(.*?)^  ```", sec, re.M | re.S)
        self.assertIsNotNone(m, "段落要放一個 fenced 最小案例")
        doc = "\n".join(l[2:] if l.startswith("  ") else l for l in m.group(1).split("\n"))
        self.assertIn("## 驗收", doc)
        self.assertIn("清單", sec)
        script = ROOT / "skills" / "qa-verify" / "scripts" / "spec_to_cases.py"
        d = Path(tempfile.mkdtemp())
        (d / "s.md").write_text("# x\n\n" + doc + "\n", encoding="utf-8")
        p = subprocess.run(["python3", str(script), str(d / "s.md"), str(d / "o.md")],
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)

    def test_direct_superpowers_path_reaches_after_and_implement(self):
        sec = read("templates/agents-md-section.md")
        for want in ("after.md", "開始實作", "沿用計畫"):
            self.assertIn(want, sec, want)
        t = read("skills/implement/SKILL.md")
        for want in ("既有計畫", "plan-review-", "after.md"):
            self.assertIn(want, t, want)
        self.assertLess(t.index("既有計畫"), t.index("superpowers:writing-plans"))

    def test_after_routes_by_design_doc_first(self):
        t = read("skills/implement/references/after.md")
        self.assertLess(t.index("無設計文件"), t.index("spec_to_cases.py"))
        for want in ("非 0", "不建立"):
            self.assertIn(want, t, want)

    def test_plan_reviewer_returns_stdout_only(self):
        t = read("skills/implement/references/plan-review.md")
        self.assertNotIn("寫到 <結果檔>", t)
        for want in ("stdout", "主控"):
            self.assertIn(want, t, want)
        self.assertLessEqual(len(t.rstrip("\n").split("\n")), 40)

    def test_fallback_after_once_header_and_gitignore(self):
        t = read("skills/implement/references/fallback.md")
        self.assertIn("**For agentic workers:**", t)
        self.assertIn(".gitignore", t)
        step3 = t[t.index("3. **逐 task 做**"):t.index("4. **自審**")]
        self.assertIn("after.md", step3)
        self.assertIn("不", step3[step3.index("after.md"):])

    def test_spec_check_component_check_scope_and_names(self):
        t = read("skills/spec-check/SKILL.md")
        self.assertIn("全文", t)
        self.assertNotIn("第 4 項", t)

    def test_debugger_agent_removed(self):
        self.assertFalse((ROOT / "agents" / ("debugger" + ".md")).exists())


if __name__ == "__main__":
    unittest.main()
