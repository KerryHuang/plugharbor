import json
import os
import tempfile
import unittest

import advisor_last_reply as m


def write(dir_, name, entries):
    proj = os.path.join(dir_, "proj")
    os.makedirs(proj, exist_ok=True)
    path = os.path.join(proj, name)
    with open(path, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    return path


def user(text):
    return {"type": "user", "message": {"content": text}}


def tool_result():
    return {"type": "user", "message": {"content": [{"type": "tool_result", "content": "x"}]}}


def assistant(mid, *blocks):
    return {"type": "assistant", "message": {"id": mid, "content": list(blocks)}}


def text(t):
    return {"type": "text", "text": t}


class LastReply(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_only_last_turn_after_tool_use(self):
        p = write(self.tmp.name, "abc.jsonl", [
            user("第 1 輪"), assistant("m1", text("舊回覆")),
            user("第 2 輪"), assistant("m2", text("先查一下"), {"type": "tool_use"}),
            tool_result(), assistant("m3", text("D-1 同意")),
        ])
        self.assertEqual(m.last_reply(p), "先查一下\n\nD-1 同意")

    def test_streamed_duplicate_blocks_once(self):
        p = write(self.tmp.name, "abc.jsonl", [
            user("q"), assistant("m1", text("A")), assistant("m1", text("A")),
        ])
        self.assertEqual(m.last_reply(p), "A")

    def test_no_text_after_last_prompt_is_empty(self):
        p = write(self.tmp.name, "abc.jsonl", [
            user("q1"), assistant("m1", text("舊")), user("q2"),
        ])
        self.assertEqual(m.last_reply(p), "")

    def test_find_rejects_ambiguous_prefix(self):
        write(self.tmp.name, "ab1.jsonl", [])
        write(self.tmp.name, "ab2.jsonl", [])
        with self.assertRaises(LookupError):
            m.find_transcript("ab", root=self.tmp.name)


if __name__ == "__main__":
    unittest.main()
