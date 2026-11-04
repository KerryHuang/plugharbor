"""dispatch-stop-guard 測試：只管被派出的 worker（有 AGENT_DISPATCH_RESULT）；結果檔沒寫就擋 Stop，其他一律放行。"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / "dispatch-stop-guard.py"
HOOKS_JSON = Path(__file__).resolve().parents[1] / "hooks.json"


class DispatchStopGuard(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.result = Path(self._tmp.name) / "result.md"

    def tearDown(self):
        self._tmp.cleanup()

    def run_hook(self, stdin='{"hook_event_name": "Stop"}', result=True):
        env = {k: v for k, v in os.environ.items() if k != "AGENT_DISPATCH_RESULT"}
        if result:
            env["AGENT_DISPATCH_RESULT"] = str(self.result)
        p = subprocess.run([sys.executable, str(HOOK)], input=stdin.encode("utf-8"), capture_output=True, env=env)
        self.assertEqual(p.returncode, 0, p.stderr.decode("utf-8", "replace"))
        return p.stdout.decode("utf-8").strip()

    def test_not_a_worker_passes(self):
        self.assertEqual(self.run_hook(result=False), "")

    def test_missing_result_blocks(self):
        out = json.loads(self.run_hook())
        self.assertEqual(out["decision"], "block")
        self.assertIn(str(self.result), out["reason"])

    def test_result_written_passes(self):
        self.result.write_text("完成", encoding="utf-8")
        self.assertEqual(self.run_hook(), "")

    def test_stop_hook_active_passes(self):
        self.assertEqual(self.run_hook('{"hook_event_name": "Stop", "stop_hook_active": true}'), "")

    def test_bad_stdin_passes(self):
        self.assertEqual(self.run_hook("not json"), "")

    def test_registered_on_stop(self):
        hooks = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))["hooks"]["Stop"]
        commands = [h["command"] for entry in hooks for h in entry["hooks"]]
        self.assertTrue(any("dispatch-stop-guard.py" in c for c in commands))


if __name__ == "__main__":
    unittest.main()
