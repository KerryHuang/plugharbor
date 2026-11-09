"""disabled-skills 測試：明確停用的 plugharbor plugin／skill → 開場一行＋細節檔；忽略清單只限當下專案。"""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / "disabled-skills.py"
PLUGINS = {"toolkit": "通用 hooks——guard", "browser-docs": "瀏覽器實機操作——截圖", "lifecycle": "軟體交付生命週期——規格"}
ALL_ON = {"toolkit@plugharbor": True, "browser-docs@plugharbor": True, "lifecycle@plugharbor": True}


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name).resolve()
        self.root = root
        self.home, self.cwd, self.mp = root / "home", root / "proj", root / "home/.claude/plugins/marketplaces/plugharbor"
        self.cwd.mkdir(parents=True)
        write(self.mp / ".claude-plugin/marketplace.json",
              {"name": "plugharbor", "plugins": [{"name": n, "description": d, "source": f"./plugins/{n}"}
                                                 for n, d in PLUGINS.items()]})
        write(self.home / ".claude/plugins/known_marketplaces.json",
              {"plugharbor": {"installLocation": str(self.mp)}})
        self.user({"enabledPlugins": dict(ALL_ON)})

    def tearDown(self):
        self.tmp.cleanup()

    def user(self, data):
        write(self.home / ".claude/settings.json", data)

    def disable(self, plugin="browser-docs"):
        self.user({"enabledPlugins": dict(ALL_ON, **{f"{plugin}@plugharbor": False})})

    def skill(self, plugin, name, frontmatter):
        path = self.mp / f"plugins/{plugin}/skills/{name}/SKILL.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"---\nname: {name}\n{frontmatter}\n---\n\n# body\n", encoding="utf-8")
        return path

    def run_raw(self, stdin=b"", args=(), extra_env=None):
        env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
        env.update(HOME=str(self.home), **(extra_env or {}))
        return subprocess.run([sys.executable, str(HOOK), *args], input=stdin, env=env, capture_output=True, timeout=10)

    def hook(self, payload):
        p = self.run_raw(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
        self.assertEqual(p.returncode, 0, p.stderr)
        if not p.stdout:
            return ""
        out = json.loads(p.stdout.decode("utf-8"))["hookSpecificOutput"]
        self.assertEqual(out["hookEventName"], payload["hook_event_name"])
        return out["additionalContext"]

    def session(self, cwd=None):
        return self.hook({"hook_event_name": "SessionStart", "cwd": str(cwd or self.cwd)})

    def ignore(self, key, cwd=None):
        p = self.run_raw(args=("ignore", key, "--cwd", str(cwd or self.cwd)))
        self.assertEqual(p.returncode, 0, p.stderr)

    def details(self, ctx):
        return Path(re.search(r"細節見 `([^`]+)`", ctx).group(1)).read_text(encoding="utf-8")


class SessionLine(Base):
    def test_silent_when_everything_enabled(self):
        self.assertEqual(self.session(), "")

    def test_session_one_line_names_only(self):
        self.disable()
        ctx = self.session()
        self.assertEqual(ctx.count("\n"), 0)
        self.assertTrue(ctx.startswith("[toolkit] plugharbor 停用中：browser-docs"), ctx)
        self.assertIn("用到前先問使用者", ctx)
        self.assertIn("claude plugin enable browser-docs@plugharbor --scope user", self.details(ctx))

    def test_local_scope_overrides_user(self):
        write(self.cwd / ".claude/settings.local.json", {"enabledPlugins": {"browser-docs@plugharbor": False}})
        self.assertIn("--scope local", self.details(self.session()))

    def test_never_enabled_plugin_is_not_listed(self):
        # 專案層 plugin 刻意只裝在特定專案（如公司 workspace 用自家 sdlc），沒寫 false 就不算被 /doctor 關掉
        self.user({"enabledPlugins": {"toolkit@plugharbor": True, "browser-docs@plugharbor": True}})
        self.assertEqual(self.session(), "")

    def test_lists_skill_turned_off_by_override(self):
        self.skill("browser-docs", "live-drive", "description: x")
        write(self.cwd / ".claude/settings.local.json", {"skillOverrides": {"browser-docs:live-drive": "off"}})
        ctx = self.session()
        self.assertIn("browser-docs:live-drive", ctx)
        self.assertIn(".claude/settings.local.json", self.details(ctx))

    def test_manual_only_skill_override_is_not_listed(self):
        self.skill("toolkit", "handoff", "description: x\ndisable-model-invocation: true")
        self.user({"enabledPlugins": dict(ALL_ON), "skillOverrides": {"toolkit:handoff": "off"}})
        self.assertEqual(self.session(), "")

    def test_silent_without_marketplace_clone(self):
        (self.home / ".claude/plugins/known_marketplaces.json").unlink()
        self.disable()
        self.assertEqual(self.session(), "")

    def test_broken_settings_file_is_ignored(self):
        (self.cwd / ".claude").mkdir()
        (self.cwd / ".claude/settings.json").write_text("{not json", encoding="utf-8")
        self.assertEqual(self.session(), "")

    def test_bad_stdin_fail_open(self):
        for bad in (b"not json", b"[]", b"{}"):
            p = self.run_raw(bad)
            self.assertEqual((p.returncode, p.stdout), (0, b""), p.stderr)


class IgnoreList(Base):
    def test_ignore_cli(self):
        self.ignore("browser-docs")
        data = json.loads((self.home / ".claude/disabled-skills/ignore.json").read_text(encoding="utf-8"))
        self.assertEqual(data, {str(self.cwd): ["browser-docs"]})

    def test_ignore_whole_plugin(self):
        self.disable()
        self.ignore("browser-docs")
        self.assertEqual(self.session(), "")

    def test_ignore_only_this_project(self):
        self.disable()
        self.ignore("browser-docs")
        other = self.root / "other"
        other.mkdir()
        self.assertIn("browser-docs", self.session(cwd=other))

    def test_ignore_key_resolves_cwd(self):
        self.disable()
        self.ignore("browser-docs", cwd=str(self.cwd) + "/")
        link = self.root / "link"
        link.symlink_to(self.cwd)
        self.assertEqual(self.session(cwd=link), "")

    def test_ignore_pruned_when_reenabled(self):
        self.disable()
        self.ignore("browser-docs")
        self.user({"enabledPlugins": dict(ALL_ON)})
        self.session()
        self.disable()
        self.assertIn("browser-docs", self.session())


class PromptMatch(Base):
    def setUp(self):
        super().setUp()
        self.skill("browser-docs", "live-drive",
                   'description: Use when 使用者說「重現這個 bug」。\ntriggers: ["跑一次 e2e", "錄音"]')

    def prompt(self, text, session="s1"):
        payload = {"hook_event_name": "UserPromptSubmit", "cwd": str(self.cwd), "prompt": text}
        if session is not None:
            payload["session_id"] = session
        return self.hook(payload)

    def test_prompt_matches_trigger_of_disabled_plugin(self):
        self.disable()
        ctx = self.prompt("幫我跑一次 E2E")
        self.assertIn("browser-docs:live-drive", ctx)
        self.assertIn("AskUserQuestion", ctx)
        for opt in ("用它並重開", "只這次用", "不要"):
            self.assertIn(opt, ctx)
        self.assertIn("ignore browser-docs", ctx)

    def test_prompt_matches_quoted_phrase(self):
        self.disable()
        self.assertIn("browser-docs:live-drive", self.prompt("可以幫我重現這個 bug 嗎"))

    def test_enabled_skill_not_matched(self):
        self.assertEqual(self.prompt("幫我跑一次 e2e"), "")

    def test_no_match_silent(self):
        self.disable()
        self.assertEqual(self.prompt("今天天氣如何"), "")

    def test_same_session_asks_once(self):
        self.disable()
        self.assertNotEqual(self.prompt("跑一次 e2e", session="s1"), "")
        self.assertEqual(self.prompt("再跑一次 e2e", session="s1"), "")
        self.assertNotEqual(self.prompt("跑一次 e2e", session="s2"), "")

    def test_ignored_not_matched(self):
        self.disable()
        self.ignore("browser-docs")
        self.assertEqual(self.prompt("跑一次 e2e"), "")

    def test_skill_override_matched(self):
        write(self.cwd / ".claude/settings.local.json", {"skillOverrides": {"browser-docs:live-drive": "off"}})
        self.assertIn("browser-docs:live-drive", self.prompt("跑一次 e2e"))

    def test_match_cap_three(self):
        names = ["p1", "p2", "p3", "p4"]
        write(self.mp / ".claude-plugin/marketplace.json",
              {"plugins": [{"name": n, "description": n} for n in names]})
        for n in names:
            self.skill(n, "s", 'description: x\ntriggers: ["共同片語"]')
        self.user({"enabledPlugins": {f"{n}@plugharbor": False for n in names}})
        ctx = self.prompt("這裡有共同片語")
        self.assertEqual(len(re.findall(r"^- p\d:s：", ctx, re.M)), 3)

    def test_prompt_edge_inputs(self):
        self.disable()
        for payload in ({"hook_event_name": "UserPromptSubmit", "cwd": str(self.cwd)},
                        {"hook_event_name": "UserPromptSubmit", "cwd": str(self.cwd), "prompt": 123}):
            p = self.run_raw(json.dumps(payload).encode("utf-8"))
            self.assertEqual((p.returncode, p.stdout), (0, b""), p.stderr)
        self.assertIn("browser-docs:live-drive", self.prompt("跑一次 e2e", session=None))
        self.assertIn("browser-docs:live-drive", self.prompt("跑一次 e2e", session=None))

    def test_short_phrase_ignored(self):
        self.disable()
        self.assertEqual(self.prompt("幫我錄音"), "")

    # ---- 最終審查修正 ----

    def test_ignore_command_shell_safe(self):
        evil = self.root / 'proj$(touch PWNED)"q'
        evil.mkdir()
        write(evil / ".claude/settings.local.json", {"enabledPlugins": {"browser-docs@plugharbor": False}})
        payload = {"hook_event_name": "UserPromptSubmit", "cwd": str(evil), "prompt": "跑一次 e2e", "session_id": "x"}
        ctx = self.hook(payload)
        cmd = re.search(r"忽略 `(.+)`$", ctx, re.M).group(1)
        p = subprocess.run(["sh", "-c", cmd], cwd=self.root, env=dict(os.environ, HOME=str(self.home)),
                           capture_output=True, timeout=10)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertFalse((self.root / "PWNED").exists())
        data = json.loads((self.home / ".claude/disabled-skills/ignore.json").read_text(encoding="utf-8"))
        self.assertEqual(data, {str(evil): ["browser-docs"]})

    def test_ascii_phrase_needs_word_boundary(self):
        self.skill("browser-docs", "annotate-screenshot", 'description: x\ntriggers: ["hangfire"]')
        self.disable()
        self.assertEqual(self.prompt("hangfires everywhere", session="a"), "")
        self.assertIn("browser-docs:annotate-screenshot", self.prompt("set up a hangfire job", session="b"))

    def test_single_ascii_word_from_description_not_used(self):
        self.skill("browser-docs", "pdf-converter", "description: Use when 使用者說「commit」「提交這次改動」。")
        self.disable()
        self.assertEqual(self.prompt("please commit this", session="a"), "")
        self.assertIn("browser-docs:pdf-converter", self.prompt("幫我提交這次改動", session="b"))

    def test_two_skills_of_same_plugin_both_prompted(self):
        self.skill("browser-docs", "annotate-screenshot", 'description: x\ntriggers: ["截圖加紅框"]')
        self.disable()
        ctx = self.prompt("跑一次 e2e 再截圖加紅框")
        self.assertIn("browser-docs:live-drive", ctx)
        self.assertIn("browser-docs:annotate-screenshot", ctx)

    def test_dedupe_is_per_skill(self):
        self.skill("browser-docs", "annotate-screenshot", 'description: x\ntriggers: ["截圖加紅框"]')
        self.disable()
        self.assertIn("browser-docs:live-drive", self.prompt("跑一次 e2e"))
        self.assertIn("browser-docs:annotate-screenshot", self.prompt("截圖加紅框"))

    def test_project_dir_env_wins_over_payload_cwd(self):
        write(self.cwd / ".claude/settings.local.json", {"enabledPlugins": {"browser-docs@plugharbor": False}})
        sub = self.cwd / "src"
        sub.mkdir()
        payload = {"hook_event_name": "UserPromptSubmit", "cwd": str(sub), "prompt": "跑一次 e2e", "session_id": "x"}
        p = self.run_raw(json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                         extra_env={"CLAUDE_PROJECT_DIR": str(self.cwd)})
        self.assertIn("browser-docs:live-drive", p.stdout.decode("utf-8"))


class PruneSafety(Base):
    def test_prune_skipped_when_marketplace_unreadable(self):
        self.disable()
        self.ignore("browser-docs")
        mj = self.mp / ".claude-plugin/marketplace.json"
        backup = mj.read_text(encoding="utf-8")
        mj.unlink()
        self.session()
        mj.write_text(backup, encoding="utf-8")
        self.assertEqual(self.session(), "")

    def test_prune_skipped_when_settings_broken(self):
        self.disable()
        self.ignore("browser-docs")
        (self.home / ".claude/settings.json").write_text("{broken", encoding="utf-8")
        self.session()
        self.disable()
        self.assertEqual(self.session(), "")


if __name__ == "__main__":
    unittest.main()
