"""herdr-env-context 測試：只有 HERDR_ENV=1 才注入，其餘靜默。"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / "herdr-env-context.py"


CLEAN = ("HERDR_ENV", "HERDR_PANE_ID", "HC_TERMINAL_ID")


def run(herdr_env, pane="w:p1", extra=None):
    env = {k: v for k, v in os.environ.items() if k not in CLEAN}
    if herdr_env is not None:
        env["HERDR_ENV"] = herdr_env
    if pane:
        env["HERDR_PANE_ID"] = pane
    env.update(extra or {})
    return subprocess.run([sys.executable, str(HOOK)], env=env, input=b"", capture_output=True, timeout=10)


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

    def test_injects_with_only_hc_terminal_id(self):
        p = run(None, pane=None, extra={"HC_TERMINAL_ID": "t1"})
        ctx = json.loads(p.stdout.decode("utf-8"))["hookSpecificOutput"]["additionalContext"]
        self.assertIn("herdr", ctx)

    def test_message_not_tied_to_var_name_and_not_longer(self):
        p = run("1")
        ctx = json.loads(p.stdout.decode("utf-8"))["hookSpecificOutput"]["additionalContext"]
        self.assertNotIn("HERDR_ENV=1", ctx)
        old = ("[toolkit] 本 session 在 herdr 內（HERDR_ENV=1），不必再檢查能否開 pane，也不必向使用者提這件事。"
               "這只代表「能開」；該不該開仍照派工判準，長任務照判準表開 pane。")
        self.assertLessEqual(len(ctx), len(old))

    def test_silent_when_herdr_env_without_pane_id(self):
        p = run("1", pane=None)
        self.assertEqual(p.stdout, b"")

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

    def test_record_is_atomic_replace(self):
        # 先寫暫存檔再 os.replace：self-rotate 輪詢讀檔時不會讀到寫一半的空檔
        import importlib.util
        from unittest import mock
        spec = importlib.util.spec_from_file_location("herdr_env_context", HOOK)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        calls = []
        real = os.replace
        with tempfile.TemporaryDirectory() as d:
            def spy(src, dst):
                calls.append((src, dst))
                return real(src, dst)
            env = {"HC_TERMINAL_ID": "t5", "XDG_STATE_HOME": d}
            stdin = mock.Mock()
            stdin.buffer.read.return_value = b'{"session_id":"abc"}'
            with mock.patch.dict(os.environ, env), mock.patch.object(mod.sys, "stdin", stdin), \
                    mock.patch.object(mod.os, "replace", spy):
                mod.record_session_id()
            final = Path(d) / "plugharbor" / "hc-sessions" / "t5"
            self.assertEqual([c[1] for c in calls], [str(final)])
            self.assertNotEqual(calls[0][0], str(final))
            self.assertEqual(os.path.dirname(calls[0][0]), str(final.parent))
            self.assertEqual(final.read_text(encoding="utf-8").strip(), "abc")
            self.assertEqual([x.name for x in final.parent.iterdir()], ["t5"])  # 沒留暫存檔

    def test_bad_stdin_keeps_output_and_exit_zero(self):
        with tempfile.TemporaryDirectory() as d:
            for stdin in (b"", b"not json", b'{"session_id":3}', b"[]"):
                p = run_hc(d, stdin)
                self.assertEqual(p.returncode, 0)
            self.assertFalse((Path(d) / "plugharbor").exists())
            env = {k: v for k, v in os.environ.items() if k != "XDG_STATE_HOME"}
            env.update({"HC_TERMINAL_ID": "t5", "XDG_STATE_HOME": d})
            p = subprocess.run([sys.executable, str(HOOK)], env=env, input=b"garbage", capture_output=True, timeout=10)
            self.assertIn("herdr", json.loads(p.stdout.decode("utf-8"))["hookSpecificOutput"]["additionalContext"])


if __name__ == "__main__":
    unittest.main()
