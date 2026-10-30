import json, subprocess, sys, unittest, pathlib
HOOK = pathlib.Path(__file__).with_name("agent-model-guard.py")

def run(payload):
    p = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(payload), capture_output=True, text=True)
    return p.returncode, p.stdout

class T(unittest.TestCase):
    def test_general_purpose_without_model_gets_sonnet(self):
        rc, out = run({"tool_name": "Agent", "tool_input": {"subagent_type": "general-purpose", "prompt": "x"}})
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out)["hookSpecificOutput"]["updatedInput"]["model"], "sonnet")

    def test_explicit_model_untouched(self):
        rc, out = run({"tool_name": "Agent", "tool_input": {"subagent_type": "general-purpose", "model": "opus"}})
        self.assertEqual((rc, out), (0, ""))

    def test_named_agent_untouched(self):
        rc, out = run({"tool_name": "Agent", "tool_input": {"subagent_type": "sa-flow:qa-runner-ui"}})
        self.assertEqual((rc, out), (0, ""))

    def test_fork_untouched(self):
        rc, out = run({"tool_name": "Agent", "tool_input": {"subagent_type": "fork"}})
        self.assertEqual((rc, out), (0, ""))

    def test_bad_stdin_fail_open(self):
        p = subprocess.run([sys.executable, str(HOOK)], input="not json", capture_output=True, text=True)
        self.assertEqual((p.returncode, p.stdout), (0, ""))

if __name__ == "__main__":
    unittest.main()
