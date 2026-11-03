"""loop-guard 測試：同指紋 3 次才注入、之後只 systemMessage、輪界歸零、subagent 各自計數、壞輸入靜默。

HOME 一律導到暫存目錄，絕不碰真的 ~/.claude/loop-guard 或 ~/.codex/loop-guard。
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / "loop-guard.py"


class LoopGuardBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def run_hook(self, payload=None, stdin=None):
        env = dict(os.environ, HOME=str(self.home), USERPROFILE=str(self.home))
        data = stdin if stdin is not None else json.dumps(payload)
        p = subprocess.run([sys.executable, str(HOOK)], input=data.encode("utf-8"), capture_output=True, env=env)
        self.assertEqual(p.returncode, 0, p.stderr.decode("utf-8", "replace"))
        out = p.stdout.decode("utf-8").strip()
        return json.loads(out) if out else {}


class ClaudeCode(LoopGuardBase):
    def fail(self, error="Exit code 1\nls: ./missing_42: No such file or directory", tool="Bash", agent=None, sid="s1"):
        p = {"session_id": sid, "hook_event_name": "PostToolUseFailure", "tool_name": tool,
             "tool_input": {"command": "ls"}, "error": error, "is_interrupt": False}
        if agent:
            p["agent_id"] = agent
        return self.run_hook(p)

    def prompt(self, sid="s1"):
        return self.run_hook({"session_id": sid, "hook_event_name": "UserPromptSubmit", "prompt": "x"})

    def test_third_same_failure_injects_context(self):
        self.assertEqual(self.fail(), {})
        self.assertEqual(self.fail(), {})
        out = self.fail()
        ctx = out["hookSpecificOutput"]
        self.assertEqual(ctx["hookEventName"], "PostToolUseFailure")
        self.assertIn("停下重估", ctx["additionalContext"])
        self.assertIn("friction", ctx["additionalContext"])
        self.assertIn("3", out["systemMessage"])

    def test_after_trigger_only_system_message(self):
        for _ in range(3):
            self.fail()
        out = self.fail()
        self.assertNotIn("hookSpecificOutput", out)
        self.assertIn("4", out["systemMessage"])
        out = self.fail()
        self.assertNotIn("hookSpecificOutput", out)
        self.assertIn("5", out["systemMessage"])

    def test_numbers_and_paths_normalized(self):
        self.fail("Exit code 1\nls: /tmp/a/b42: No such file or directory")
        self.fail("Exit code 2\nls: /var/x/y7: No such file or directory")
        self.assertIn("hookSpecificOutput", self.fail("Exit code 1\nls: /opt/q/z0x1f: No such file or directory"))

    def test_exit_code_line_skipped(self):
        """第一行都是 Exit code 1，但下一行不同 → 不同指紋，不該觸發。"""
        self.fail("Exit code 1\nls: x: No such file or directory")
        self.fail("Exit code 1\nnpm ERR! missing script: build")
        self.assertEqual(self.fail("Exit code 1\nTraceback (most recent call last):"), {})

    def test_exit_code_only_falls_back(self):
        for _ in range(2):
            self.fail("Exit code 1")
        self.assertIn("hookSpecificOutput", self.fail("Exit code 1\n\n"))

    def test_path_only_line_not_merged(self):
        """整行只有路徑／數字時正規化後為空，不該把不同失敗併成同一指紋。"""
        self.fail("Exit code 1\n/a/b/c")
        self.fail("Exit code 1\n/x/y")
        self.assertEqual(self.fail("Exit code 1\n12345"), {})

    def test_stale_state_pruned_active_kept(self):
        self.fail(sid="old")
        self.fail(sid="live")
        base = self.home / ".claude" / "loop-guard"
        stale = 10 * 86400
        for f in (base / "old").iterdir():
            t = f.stat().st_mtime - stale
            os.utime(f, (t, t))
        os.utime(base / "live", (0, 0))   # 目錄 mtime 舊但檔案新 → 仍算活躍
        self.prompt(sid="other")
        self.assertFalse((base / "old").exists())
        self.assertTrue((base / "live" / "main.json").exists())

    def test_tool_name_part_of_fingerprint(self):
        self.fail(tool="Bash", error="File does not exist.")
        self.fail(tool="Read", error="File does not exist.")
        self.assertEqual(self.fail(tool="Edit", error="File does not exist."), {})

    def test_user_prompt_resets_main(self):
        self.fail()
        self.fail()
        self.prompt()
        self.assertEqual(self.fail(), {})
        self.assertEqual(self.fail(), {})
        self.assertIn("hookSpecificOutput", self.fail())

    def test_reset_rearms_injection(self):
        for _ in range(3):
            self.fail()
        self.prompt()
        for _ in range(2):
            self.fail()
        self.assertIn("hookSpecificOutput", self.fail())

    def test_subagent_counts_independent(self):
        self.fail()
        self.fail()
        self.assertEqual(self.fail(agent="a1"), {})
        self.assertEqual(self.fail(agent="a1"), {})
        self.assertIn("hookSpecificOutput", self.fail())
        self.assertIn("hookSpecificOutput", self.fail(agent="a1"))

    def test_user_prompt_does_not_reset_subagent(self):
        self.fail(agent="a1")
        self.fail(agent="a1")
        self.prompt()
        self.assertIn("hookSpecificOutput", self.fail(agent="a1"))

    def test_sessions_independent(self):
        self.fail(sid="s1")
        self.fail(sid="s1")
        self.assertEqual(self.fail(sid="s2"), {})

    def test_unsafe_ids_stay_in_state_dir(self):
        self.fail(sid="../../evil", agent="../x")
        self.assertFalse((self.home / "evil").exists())
        self.assertTrue((self.home / ".claude" / "loop-guard").is_dir())

    def test_bad_input_silent(self):
        self.assertEqual(self.run_hook(stdin="not json"), {})
        self.assertEqual(self.run_hook(stdin=""), {})
        self.assertEqual(self.run_hook(stdin="[]"), {})
        self.assertEqual(self.run_hook({"hook_event_name": "PostToolUseFailure"}), {})
        self.assertEqual(self.run_hook({"session_id": "s1", "hook_event_name": "PostToolUseFailure", "error": None}), {})

    def test_claude_post_tool_use_ignored(self):
        """Claude 的 PostToolUse（沒有 turn_id）是成功呼叫，不計數。"""
        p = {"session_id": "s1", "hook_event_name": "PostToolUse", "tool_name": "Bash", "tool_response": {"stdout": "x"}}
        for _ in range(4):
            self.assertEqual(self.run_hook(p), {})


class Codex(LoopGuardBase):
    def setUp(self):
        super().setUp()
        self.transcript = self.home / "rollout.jsonl"
        self.transcript.write_text("", encoding="utf-8")
        self.n = 0

    def call(self, status="failed", output="ls: ./missing_42: No such file or directory\n", turn="t1",
             agent=None, tool="Bash", record=True):
        self.n += 1
        cid = f"exec-{self.n}"
        if record:
            item = {"type": "CommandExecution", "id": cid, "status": status,
                    "exit_code": 1 if status == "failed" else 0}
            line = {"type": "event_msg", "payload": {"type": "item_completed", "turn_id": turn, "item": item}}
            with self.transcript.open("a", encoding="utf-8") as f:
                f.write(json.dumps(line) + "\n")
        p = {"session_id": "c1", "turn_id": turn, "hook_event_name": "PostToolUse", "tool_name": tool,
             "tool_use_id": cid, "tool_input": {"command": "ls"}, "tool_response": output,
             "transcript_path": str(self.transcript)}
        if agent:
            p["agent_id"] = agent
        return self.run_hook(p)

    def test_third_failure_injects_post_tool_use_context(self):
        self.call()
        self.call()
        out = self.call()
        self.assertEqual(out["hookSpecificOutput"]["hookEventName"], "PostToolUse")
        self.assertIn("停下重估", out["hookSpecificOutput"]["additionalContext"])
        self.assertTrue((self.home / ".codex" / "loop-guard").is_dir())
        self.assertNotIn("hookSpecificOutput", self.call())

    def test_success_not_counted(self):
        for _ in range(4):
            self.assertEqual(self.call(status="completed"), {})

    def test_missing_transcript_record_not_counted(self):
        """transcript 找不到這筆呼叫 → 不能判定失敗，fail-open 不計數。"""
        for _ in range(4):
            self.assertEqual(self.call(record=False), {})

    def test_new_turn_resets(self):
        self.call(turn="t1")
        self.call(turn="t1")
        self.assertEqual(self.call(turn="t2"), {})
        self.assertEqual(self.call(turn="t2"), {})
        self.assertIn("hookSpecificOutput", self.call(turn="t2"))

    def test_subagent_independent(self):
        self.call()
        self.call()
        self.assertEqual(self.call(agent="sub-1"), {})
        self.assertIn("hookSpecificOutput", self.call())


if __name__ == "__main__":
    unittest.main()
