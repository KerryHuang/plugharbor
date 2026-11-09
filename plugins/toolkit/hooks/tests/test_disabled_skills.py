"""disabled-skills 測試：依 user → project → local 設定算出不可用的 plugharbor plugin／skill，沒有就靜默。"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / "disabled-skills.py"
PLUGINS = {"toolkit": "通用 hooks——guard", "browser-docs": "瀏覽器實機操作——截圖", "lifecycle": "軟體交付生命週期——規格"}


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


class DisabledSkills(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.home, self.cwd, self.mp = root / "home", root / "proj", root / "home/.claude/plugins/marketplaces/plugharbor"
        self.cwd.mkdir(parents=True)
        write(self.mp / ".claude-plugin/marketplace.json",
              {"name": "plugharbor", "plugins": [{"name": n, "description": d, "source": f"./plugins/{n}"}
                                                 for n, d in PLUGINS.items()]})
        write(self.home / ".claude/plugins/known_marketplaces.json",
              {"plugharbor": {"installLocation": str(self.mp)}})
        self.user({"enabledPlugins": {"toolkit@plugharbor": True, "browser-docs@plugharbor": True,
                                      "lifecycle@plugharbor": True}})

    def tearDown(self):
        self.tmp.cleanup()

    def user(self, data):
        write(self.home / ".claude/settings.json", data)

    def run_hook(self):
        env = dict(os.environ, HOME=str(self.home))
        p = subprocess.run([sys.executable, str(HOOK)], input=json.dumps({"cwd": str(self.cwd)}).encode(),
                           env=env, capture_output=True, timeout=10)
        self.assertEqual(p.returncode, 0, p.stderr)
        if not p.stdout:
            return ""
        out = json.loads(p.stdout.decode("utf-8"))["hookSpecificOutput"]
        self.assertEqual(out["hookEventName"], "SessionStart")
        return out["additionalContext"]

    def test_silent_when_everything_enabled(self):
        self.assertEqual(self.run_hook(), "")

    def test_lists_plugin_disabled_at_user_scope(self):
        self.user({"enabledPlugins": {"toolkit@plugharbor": True, "browser-docs@plugharbor": False,
                                      "lifecycle@plugharbor": True}})
        ctx = self.run_hook()
        self.assertIn("browser-docs（瀏覽器實機操作）", ctx)
        self.assertIn("claude plugin enable browser-docs@plugharbor --scope user", ctx)
        self.assertNotIn("lifecycle", ctx)
        self.assertIn(str(self.mp / "plugins"), ctx)

    def test_local_scope_overrides_user(self):
        write(self.cwd / ".claude/settings.local.json", {"enabledPlugins": {"browser-docs@plugharbor": False}})
        ctx = self.run_hook()
        self.assertIn("claude plugin enable browser-docs@plugharbor --scope local", ctx)

    def test_never_enabled_plugin_is_not_listed(self):
        # 專案層 plugin 刻意只裝在特定專案（如公司 workspace 用自家 sdlc），沒寫 false 就不算被 /doctor 關掉
        self.user({"enabledPlugins": {"toolkit@plugharbor": True, "browser-docs@plugharbor": True}})
        self.assertEqual(self.run_hook(), "")

    def test_lists_skill_turned_off_by_override(self):
        write(self.cwd / ".claude/settings.local.json", {"skillOverrides": {"browser-docs:live-drive": "off"}})
        ctx = self.run_hook()
        self.assertIn("browser-docs:live-drive", ctx)
        self.assertIn(".claude/settings.local.json", ctx)

    def test_manual_only_skill_override_is_not_listed(self):
        skill = self.mp / "plugins/toolkit/skills/handoff/SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("---\nname: handoff\ndisable-model-invocation: true\n---\n", encoding="utf-8")
        self.user({"enabledPlugins": {"toolkit@plugharbor": True, "browser-docs@plugharbor": True,
                                      "lifecycle@plugharbor": True}, "skillOverrides": {"toolkit:handoff": "off"}})
        self.assertEqual(self.run_hook(), "")

    def test_silent_without_marketplace_clone(self):
        (self.home / ".claude/plugins/known_marketplaces.json").unlink()
        self.user({"enabledPlugins": {"browser-docs@plugharbor": False}})
        self.assertEqual(self.run_hook(), "")

    def test_bad_stdin_fail_open(self):
        for bad in (b"not json", b"[]"):
            p = subprocess.run([sys.executable, str(HOOK)], input=bad, env=dict(os.environ, HOME=str(self.home)),
                               capture_output=True, timeout=10)
            self.assertEqual((p.returncode, p.stdout), (0, b""), p.stderr)

    def test_broken_settings_file_is_ignored(self):
        (self.cwd / ".claude").mkdir()
        (self.cwd / ".claude/settings.json").write_text("{not json", encoding="utf-8")
        self.assertEqual(self.run_hook(), "")


if __name__ == "__main__":
    unittest.main()
