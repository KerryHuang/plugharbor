"""send-retry-hint 測試：SendMessage 收件人找不到時注入「用 ListAgents 找回收件方重送一次」，其他情況不輸出。"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / "send-retry-hint.py"
NOT_FOUND = "No agent named '%s' is reachable.\nUse ListAgents to see everyone you can message."


def run_hook(payload):
    p = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(payload).encode("utf-8"),
                       capture_output=True, timeout=10)
    assert p.returncode == 0, p.stderr.decode("utf-8", "replace")
    out = p.stdout.decode("utf-8").strip()
    return json.loads(out)["hookSpecificOutput"]["additionalContext"] if out else None


def payload(to, response, tool="SendMessage"):
    return {"hook_event_name": "PostToolUse", "tool_name": tool, "tool_input": {"to": to}, "tool_response": response}


class SendRetryHint(unittest.TestCase):
    def test_name_with_ref_hints_same_ref(self):
        ctx = run_hook(payload("plugharbor-25 [44dec6]", {"success": False, "message": NOT_FOUND % "plugharbor-25 [44dec6]"}))
        self.assertIn("[44dec6]", ctx)
        self.assertIn("ListAgents", ctx)

    def test_bare_name_still_hints(self):
        ctx = run_hook(payload("plugharbor-25", {"success": False, "message": NOT_FOUND % "plugharbor-25"}))
        self.assertIn("ListAgents", ctx)
        self.assertNotIn("[]", ctx)

    def test_success_is_silent(self):
        self.assertIsNone(run_hook(payload("x [abc123]", {"success": True, "message": "Message sent"})))

    def test_other_failure_is_silent(self):
        self.assertIsNone(run_hook(payload("x", {"success": False, "message": "2 agents are named 'x'"})))

    def test_other_tool_is_silent(self):
        self.assertIsNone(run_hook(payload("x", {"success": False, "message": NOT_FOUND % "x"}, tool="Bash")))

    def test_string_response_and_bad_input_fail_open(self):
        self.assertIn("ListAgents", run_hook(payload("y", NOT_FOUND % "y")))
        p = subprocess.run([sys.executable, str(HOOK)], input=b"not json", capture_output=True, timeout=10)
        self.assertEqual((p.returncode, p.stdout), (0, b""))


if __name__ == "__main__":
    unittest.main()
