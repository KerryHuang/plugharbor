"""herdr-env-context 測試：只有 HERDR_ENV=1 才注入，其餘靜默。"""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / "herdr-env-context.py"


def run(herdr_env):
    env = {k: v for k, v in os.environ.items() if k != "HERDR_ENV"}
    if herdr_env is not None:
        env["HERDR_ENV"] = herdr_env
    return subprocess.run([sys.executable, str(HOOK)], env=env, capture_output=True, timeout=10)


class HerdrEnvContext(unittest.TestCase):
    def test_injects_when_inside_herdr(self):
        p = run("1")
        self.assertEqual(p.returncode, 0)
        output = json.loads(p.stdout.decode("utf-8"))["hookSpecificOutput"]
        self.assertEqual(output["hookEventName"], "SessionStart")
        self.assertIn("herdr", output["additionalContext"])

    def test_silent_outside_herdr(self):
        for value in (None, "", "0"):
            p = run(value)
            self.assertEqual(p.returncode, 0)
            self.assertEqual(p.stdout, b"")


if __name__ == "__main__":
    unittest.main()
