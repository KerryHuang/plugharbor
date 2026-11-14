"""reply-language-guard 測試：使用者用 CJK 提問、這回合卻有整段英文回覆時擋 Stop，其他一律放行。"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[1]
HOOK = HOOKS / "reply-language-guard.py"


def user(text):
    return {"type": "user", "message": {"role": "user", "content": text}}


def tool_result():
    return {"type": "user", "message": {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": "x", "content": "ok"}]}}


def assistant(*texts):
    return {"type": "assistant", "message": {"role": "assistant", "content": [
        {"type": "text", "text": t} for t in texts]}}


def meta(text, **extra):
    """跨 session 訊息、subagent 交回、Stop hook 回饋等：isMeta 的 user 列，會開啟新回合。"""
    return {"type": "user", "isMeta": True, "message": {"role": "user", "content": text}, **extra}


class ReplyLanguageGuard(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.transcript = Path(self._tmp.name) / "t.jsonl"

    def tearDown(self):
        self._tmp.cleanup()

    def run_hook(self, rows, active=False, path=None, last=None):
        self.transcript.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
        payload = {"hook_event_name": "Stop", "stop_hook_active": active,
                   "transcript_path": str(path or self.transcript)}
        if last is not None:
            payload["last_assistant_message"] = last
        p = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(payload).encode("utf-8"),
                           capture_output=True, timeout=10)
        self.assertEqual(p.returncode, 0, p.stderr.decode("utf-8", "replace"))
        return p.stdout.decode("utf-8").strip()

    def test_english_narration_after_chinese_prompt_blocks(self):
        rows = [user("幫我更新平面圖"), assistant("我先看檔案。"), tool_result(),
                assistant("Now updating the README."), tool_result(), assistant("✅ 平面圖已更新。")]
        out = json.loads(self.run_hook(rows))
        self.assertEqual(out["decision"], "block")
        self.assertIn("Now updating the README", out["reason"])

    def test_old_english_before_meta_turn_start_is_not_rescanned(self):
        # 2026-11-14 自動駕駛 session：開場回合的英文句，在之後每個由跨 session 訊息開啟的回合都被重擋
        rows = [user("繼續自動駕駛"), assistant("Now the docs cleanup. Let me look at the repo state."),
                tool_result(), assistant("整理完成。"),
                meta("Another Claude session sent a message: ...", origin={"kind": "peer"}),
                assistant("收到，照做。"), tool_result(), assistant("✅ 已完成。")]
        self.assertEqual(self.run_hook(rows), "")

    def test_english_after_meta_turn_start_still_blocks(self):
        rows = [user("繼續自動駕駛"), assistant("好。"),
                meta("Stop hook feedback: ..."), assistant("Now checking the CI status again.")]
        self.assertEqual(json.loads(self.run_hook(rows))["decision"], "block")

    def test_all_chinese_passes(self):
        rows = [user("幫我更新平面圖"), assistant("我先看檔案。"), tool_result(), assistant("✅ 已更新 `README.md`。")]
        self.assertEqual(self.run_hook(rows), "")

    def test_english_prompt_is_not_enforced(self):
        rows = [user("please update the floor plan"), assistant("Now updating the README.")]
        self.assertEqual(self.run_hook(rows), "")

    def test_code_and_paths_are_ignored(self):
        rows = [user("跑測試"), assistant("```\nFAILED tests/test_a.py::test_x - AssertionError: expected value\n```"),
                assistant("`git status --short` 的輸出：https://example.com/foo/bar and more")]
        self.assertEqual(self.run_hook(rows), "")

    def test_short_english_fragment_passes(self):
        rows = [user("更新 README"), assistant("Now README.")]
        self.assertEqual(self.run_hook(rows), "")

    def test_only_current_turn_counts(self):
        rows = [user("第一題"), assistant("Earlier I answered in English here."), user("第二題"), assistant("這次用中文。")]
        self.assertEqual(self.run_hook(rows), "")

    def test_meta_and_compact_summary_are_not_prompts(self):
        rows = [user("幫我更新平面圖"),
                {"type": "user", "isCompactSummary": True, "message": {"role": "user", "content": "This session is being continued"}},
                {"type": "user", "isMeta": True, "message": {"role": "user", "content": "Caveat: the messages below"}},
                assistant("Now writing floor plan v4 to the builder's dimensions.")]
        self.assertEqual(json.loads(self.run_hook(rows))["decision"], "block")

    def test_last_message_not_yet_in_transcript_blocks(self):
        # Stop 觸發時最後一則回覆還沒寫進 transcript，只在 payload 的 last_assistant_message
        out = json.loads(self.run_hook([user("介紹貓")], last="Cats are curious, independent animals."))
        self.assertEqual(out["decision"], "block")

    def test_second_stop_passes(self):
        rows = [user("幫我更新平面圖"), assistant("Now updating the README.")]
        self.assertEqual(self.run_hook(rows, active=True), "")

    def test_missing_transcript_passes(self):
        self.assertEqual(self.run_hook([], path=Path(self._tmp.name) / "nope.jsonl"), "")

    def test_registered_on_stop(self):
        cfg = json.loads((HOOKS / "hooks.json").read_text(encoding="utf-8"))["hooks"]["Stop"]
        cmds = [h["command"] for m in cfg for h in m["hooks"]]
        self.assertTrue(any("reply-language-guard.py" in c for c in cmds), cfg)


if __name__ == "__main__":
    unittest.main()
