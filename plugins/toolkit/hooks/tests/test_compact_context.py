"""compact-context 測試：輸出 SessionStart additionalContext，且在 hooks.json 掛在 compact matcher。"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[1]
HOOK = HOOKS / "compact-context.py"


class CompactContext(unittest.TestCase):
    def test_injects_language_reminder(self):
        p = subprocess.run([sys.executable, str(HOOK)], capture_output=True, timeout=10)
        self.assertEqual(p.returncode, 0)
        output = json.loads(p.stdout.decode("utf-8"))["hookSpecificOutput"]
        self.assertEqual(output["hookEventName"], "SessionStart")
        self.assertIn("語言", output["additionalContext"])

    def run_with(self, loaded, installed, herdr=False):
        """loaded：本 session 載入的 toolkit 版本（CLAUDE_PLUGIN_ROOT）；installed：installed_plugins.json 記的版本。"""
        import os, tempfile
        home = tempfile.mkdtemp()
        reg = Path(home, ".claude", "plugins")
        reg.mkdir(parents=True)
        if installed is not None:
            (reg / "installed_plugins.json").write_text(json.dumps({"version": 2, "plugins": {
                "toolkit@plugharbor": [{"scope": "user", "version": installed}]}}), encoding="utf-8")
        env = {k: v for k, v in os.environ.items() if k != "HERDR_ENV"}
        if herdr:
            env["HERDR_ENV"] = "1"
        env = {**env, "HOME": home, "USERPROFILE": home,
               "CLAUDE_PLUGIN_ROOT": str(Path(home, ".claude", "plugins", "cache", "plugharbor", "toolkit", loaded))}
        p = subprocess.run([sys.executable, str(HOOK)], capture_output=True, timeout=10, env=env)
        self.assertEqual(p.returncode, 0)
        return json.loads(p.stdout.decode("utf-8"))["hookSpecificOutput"]["additionalContext"]

    def test_warns_when_loaded_version_is_behind(self):
        ctx = self.run_with("0.13.0", "0.21.3")
        self.assertIn("0.13.0", ctx)
        self.assertIn("已安裝的是 0.21.3", ctx)

    def test_no_warning_when_current_or_unknown(self):
        for loaded, installed in (("0.21.3", "0.21.3"), ("0.22.0", "0.21.3"), ("0.13.0", None), ("dev", "0.21.3")):
            ctx = self.run_with(loaded, installed)
            self.assertNotIn("已安裝的是", ctx, (loaded, installed))
            self.assertIn("語言", ctx)

    def test_handoff_note_in_herdr_points_to_skill(self):
        ctx = self.run_with("0.23.0", "0.23.0", herdr=True)
        self.assertIn(str(Path("toolkit", "0.23.0", "skills", "handoff", "SKILL.md")), ctx)
        self.assertIn("AskUserQuestion", ctx)
        self.assertIn("任務已完成就不換", ctx)

    def test_handoff_note_outside_herdr_suggests_command(self):
        ctx = self.run_with("0.23.0", "0.23.0")
        self.assertIn("/handoff", ctx)
        self.assertNotIn("SKILL.md", ctx)

    def test_language_reminder_covers_tool_descriptions(self):
        self.assertIn("工具呼叫的說明文字", self.run_with("0.23.0", "0.23.0"))

    def test_registered_on_compact_matcher(self):
        cfg = json.loads((HOOKS / "hooks.json").read_text(encoding="utf-8"))["hooks"]["SessionStart"]
        cmds = [h["command"] for m in cfg if m.get("matcher") == "compact" for h in m["hooks"]]
        self.assertTrue(any("compact-context.py" in c for c in cmds), cfg)


if __name__ == "__main__":
    unittest.main()
