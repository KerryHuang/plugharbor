"""text-question-guard 測試：回合以文字問句結尾、又沒呼叫 AskUserQuestion 時擋 Stop，其他一律放行。"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / "text-question-guard.py"


def user(text):
    return {"type": "user", "message": {"role": "user", "content": text}}


def tool_result():
    return {"type": "user", "message": {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": "x", "content": "ok"}]}}


def assistant(text):
    return {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": text}]}}


def tool_use(name):
    return {"type": "assistant", "message": {"role": "assistant", "content": [
        {"type": "tool_use", "id": "x", "name": name, "input": {}}]}}


class TextQuestionGuard(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.transcript = Path(self._tmp.name) / "t.jsonl"

    def tearDown(self):
        self._tmp.cleanup()

    def run_hook(self, rows, active=False, last=None, env=None):
        self.transcript.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
        payload = {"hook_event_name": "Stop", "stop_hook_active": active, "transcript_path": str(self.transcript)}
        if last is not None:
            payload["last_assistant_message"] = last
        p = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(payload).encode("utf-8"),
                           capture_output=True, timeout=10, env={**os.environ, **(env or {})})
        self.assertEqual(p.returncode, 0, p.stderr.decode("utf-8", "replace"))
        return p.stdout.decode("utf-8").strip()

    def test_text_question_at_end_blocks(self):
        # 2026-11-12 brainstorming：用文字一題一題問
        rows = [user("開了就離開"), assistant("理解了。\n\n下一個問題：你不在的時候要先照跑，還是直接跳過這張？")]
        out = json.loads(self.run_hook(rows))
        self.assertEqual(out["decision"], "block")
        self.assertIn("直接跳過這張", out["reason"])

    def test_payload_last_message_is_used(self):
        rows = [user("幫我看"), assistant("我先查。"), tool_result()]
        self.assertEqual(json.loads(self.run_hook(rows, last="查完了。要我接著改嗎？"))["decision"], "block")

    def test_question_with_trailing_title_line_blocks(self):
        rows = [user("繼續"), assistant("做完一半。\n\n要不要我接著做第二段？\n\n建議 session 標題：/rename 整理")]
        self.assertEqual(json.loads(self.run_hook(rows))["decision"], "block")

    def test_ask_user_question_in_turn_passes(self):
        rows = [user("繼續"), tool_use("AskUserQuestion"), tool_result(), assistant("你選了 A，還有其他想法嗎？")]
        self.assertEqual(self.run_hook(rows), "")

    def test_statement_end_passes(self):
        rows = [user("繼續"), assistant("為什麼會這樣？因為快取過期。\n\n✅ 已修好，可以收工。")]
        self.assertEqual(self.run_hook(rows), "")

    def test_question_in_code_passes(self):
        rows = [user("繼續"), assistant("範例：\n\n```\nok = input('continue?')\n```")]
        self.assertEqual(self.run_hook(rows), "")

    def test_old_turn_question_not_rescanned(self):
        rows = [user("A"), assistant("要我做嗎？"), user("好"), assistant("✅ 做完了。")]
        self.assertEqual(self.run_hook(rows), "")

    def test_stop_hook_active_passes(self):
        rows = [user("繼續"), assistant("要我接著做嗎？")]
        self.assertEqual(self.run_hook(rows, active=True), "")

    def test_unattended_worker_passes(self):
        rows = [user("繼續"), assistant("要我接著做嗎？")]
        self.assertEqual(self.run_hook(rows, env={"AGENT_DISPATCH_UNATTENDED": "1"}), "")

    def test_missing_transcript_fails_open(self):
        p = subprocess.run([sys.executable, str(HOOK)], input=b'{"transcript_path": "/nonexistent/x.jsonl"}',
                           capture_output=True, timeout=10)
        self.assertEqual((p.returncode, p.stdout), (0, b""))


if __name__ == "__main__":
    unittest.main()
