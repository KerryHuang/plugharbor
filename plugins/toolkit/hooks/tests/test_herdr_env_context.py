"""herdr-env-context 測試：只有 HERDR_ENV=1 才注入，其餘靜默。"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / "herdr-env-context.py"


def run(herdr_env):
    env = {k: v for k, v in os.environ.items() if k != "HERDR_ENV"}
    if herdr_env is not None:
        env["HERDR_ENV"] = herdr_env
    return subprocess.run([sys.executable, str(HOOK)], env=env, capture_output=True, timeout=10)


def run_hc(state, stdin, terminal="t5"):
    env = {k: v for k, v in os.environ.items() if k not in ("HERDR_ENV", "HC_TERMINAL_ID", "XDG_STATE_HOME")}
    env.update({"HC_TERMINAL_ID": terminal, "XDG_STATE_HOME": state})
    return subprocess.run([sys.executable, str(HOOK)], env=env, input=stdin, capture_output=True, timeout=10)


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

    def test_records_session_id_under_hc(self):
        with tempfile.TemporaryDirectory() as d:
            p = run_hc(d, b'{"session_id":"abc"}')
            self.assertEqual(p.returncode, 0)
            f = Path(d) / "plugharbor" / "hc-sessions" / "t5"
            self.assertEqual(f.read_text(encoding="utf-8").strip(), "abc")

    def test_no_record_without_hc(self):
        with tempfile.TemporaryDirectory() as d:
            env = {k: v for k, v in os.environ.items() if k != "HC_TERMINAL_ID"}
            env.update({"HERDR_ENV": "1", "XDG_STATE_HOME": d})
            p = subprocess.run([sys.executable, str(HOOK)], env=env, input=b'{"session_id":"abc"}',
                               capture_output=True, timeout=10)
            self.assertEqual(p.returncode, 0)
            self.assertFalse((Path(d) / "plugharbor").exists())

    def test_record_overwrites_after_clear(self):
        with tempfile.TemporaryDirectory() as d:
            run_hc(d, b'{"session_id":"abc"}')
            run_hc(d, b'{"session_id":"def"}')
            f = Path(d) / "plugharbor" / "hc-sessions" / "t5"
            self.assertEqual(f.read_text(encoding="utf-8").strip(), "def")

    def test_bad_stdin_keeps_output_and_exit_zero(self):
        with tempfile.TemporaryDirectory() as d:
            for stdin in (b"", b"not json", b'{"session_id":3}', b"[]"):
                p = run_hc(d, stdin)
                self.assertEqual(p.returncode, 0)
            self.assertFalse((Path(d) / "plugharbor").exists())
            env = {k: v for k, v in os.environ.items() if k != "XDG_STATE_HOME"}
            env.update({"HERDR_ENV": "1", "HC_TERMINAL_ID": "t5", "XDG_STATE_HOME": d})
            p = subprocess.run([sys.executable, str(HOOK)], env=env, input=b"garbage", capture_output=True, timeout=10)
            self.assertIn("herdr", json.loads(p.stdout.decode("utf-8"))["hookSpecificOutput"]["additionalContext"])


if __name__ == "__main__":
    unittest.main()
