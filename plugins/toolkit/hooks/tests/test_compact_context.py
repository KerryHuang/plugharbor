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

    def run_with(self, loaded, installed):
        """loaded：本 session 載入的 toolkit 版本（CLAUDE_PLUGIN_ROOT）；installed：installed_plugins.json 記的版本。"""
        import os, tempfile
        home = tempfile.mkdtemp()
        reg = Path(home, ".claude", "plugins")
        reg.mkdir(parents=True)
        if installed is not None:
            (reg / "installed_plugins.json").write_text(json.dumps({"version": 2, "plugins": {
                "toolkit@plugharbor": [{"scope": "user", "version": installed}]}}), encoding="utf-8")
        env = {**os.environ, "HOME": home, "USERPROFILE": home,
               "CLAUDE_PLUGIN_ROOT": str(Path(home, ".claude", "plugins", "cache", "plugharbor", "toolkit", loaded))}
        p = subprocess.run([sys.executable, str(HOOK)], capture_output=True, timeout=10, env=env)
        self.assertEqual(p.returncode, 0)
        return json.loads(p.stdout.decode("utf-8"))["hookSpecificOutput"]["additionalContext"]

    def test_warns_when_loaded_version_is_behind(self):
        ctx = self.run_with("0.13.0", "0.21.3")
        self.assertIn("0.13.0", ctx)
        self.assertIn("0.21.3", ctx)
        self.assertIn("新 session", ctx)

    def test_no_warning_when_current_or_unknown(self):
        for loaded, installed in (("0.21.3", "0.21.3"), ("0.22.0", "0.21.3"), ("0.13.0", None), ("dev", "0.21.3")):
            ctx = self.run_with(loaded, installed)
            self.assertNotIn("新 session", ctx, (loaded, installed))
            self.assertIn("語言", ctx)

    def test_registered_on_compact_matcher(self):
        cfg = json.loads((HOOKS / "hooks.json").read_text(encoding="utf-8"))["hooks"]["SessionStart"]
        cmds = [h["command"] for m in cfg if m.get("matcher") == "compact" for h in m["hooks"]]
        self.assertTrue(any("compact-context.py" in c for c in cmds), cfg)


if __name__ == "__main__":
    unittest.main()
