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

    def test_registered_on_compact_matcher(self):
        cfg = json.loads((HOOKS / "hooks.json").read_text(encoding="utf-8"))["hooks"]["SessionStart"]
        cmds = [h["command"] for m in cfg if m.get("matcher") == "compact" for h in m["hooks"]]
        self.assertTrue(any("compact-context.py" in c for c in cmds), cfg)


if __name__ == "__main__":
    unittest.main()
