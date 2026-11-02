import json
import os
import tempfile
import unittest

import chain_cost as m

FEATURE = "docs/demo/report"


def write(path, entries):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")


def user(text, **kw):
    return {"type": "user", "timestamp": "2026-10-29T01:00:00Z", "message": {"content": text}, **kw}


def tool_result():
    return {"type": "user", "message": {"content": [{"type": "tool_result", "content": "x"}]}}


def assistant(mid, usage, *blocks, ts="2026-10-29T02:00:00Z"):
    return {"type": "assistant", "timestamp": ts,
            "message": {"id": mid, "usage": usage, "content": list(blocks)}}


def edit(path):
    return {"type": "tool_use", "name": "Edit", "input": {"file_path": path}}


U = {"input_tokens": 10, "cache_creation_input_tokens": 100, "cache_read_input_tokens": 1000, "output_tokens": 5}


class ChainCost(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        proj = os.path.join(self.tmp.name, "proj")
        a = f"/w/{FEATURE}/notes.md"
        write(os.path.join(proj, "aaaa1111.jsonl"), [
            user("寫報告"),
            user("<task-notification>done</task-notification>"),
            user("內部提示", isMeta=True),
            assistant("m1", U, edit(a)),
            assistant("m1", U, edit(a)),  # 串流重複列，同一 id 只算一次
            tool_result(),
            user("改成 80"),
            assistant("m2", U, {"type": "text", "text": "好"}, ts="2026-10-30T03:00:00Z"),
        ])
        write(os.path.join(proj, "aaaa1111", "subagents", "agent-x.jsonl"), [
            assistant("s1", U, {"type": "text", "text": "子代理"}),
        ])
        write(os.path.join(proj, "bbbb2222.jsonl"), [
            user("無關"),
            assistant("m9", U, edit("/w/docs/demo/other/a.md")),
        ])
        write(os.path.join(proj, "cccc3333.jsonl"), [
            user("兩個單位"),
            assistant("m3", U, edit(a), edit("/w/docs/demo/other/a.md")),
        ])
        self.rows = {r.session: r for r in m.collect(FEATURE, self.tmp.name)}

    def tearDown(self):
        self.tmp.cleanup()

    def test_only_sessions_touching_feature(self):
        self.assertEqual(sorted(self.rows), ["aaaa1111", "cccc3333"])

    def test_human_turns_exclude_tool_results_notifications_meta(self):
        self.assertEqual(self.rows["aaaa1111"].human_turns, 2)

    def test_tokens_dedupe_by_message_id_and_include_subagents(self):
        self.assertEqual(self.rows["aaaa1111"].tokens, 3 * 1115)
        self.assertEqual(self.rows["aaaa1111"].assistant_msgs, 2)

    def test_date_span(self):
        self.assertEqual(self.rows["aaaa1111"].first, "2026-10-29")
        self.assertEqual(self.rows["aaaa1111"].last, "2026-10-30")

    def test_multi_unit_flag(self):
        self.assertFalse(self.rows["aaaa1111"].multi_unit)
        self.assertTrue(self.rows["cccc3333"].multi_unit)

    def test_share_by_tool_calls(self):
        # aaaa1111 兩次工具呼叫都只碰本單位；cccc3333 一次碰本單位、一次碰other
        self.assertEqual(self.rows["aaaa1111"].share, 1.0)
        self.assertEqual(self.rows["cccc3333"].share, 0.5)
        self.assertEqual(self.rows["cccc3333"].tokens_share, 1115 * 0.5)
        self.assertEqual(self.rows["cccc3333"].human_turns_share, 0.5)

    def test_no_session_is_error(self):
        with self.assertRaises(LookupError):
            m.collect("docs/none/none", self.tmp.name)


    def test_units_glob_param(self):
        proj = os.path.join(self.tmp.name, "proj")
        write(os.path.join(proj, "dddd4444.jsonl"), [
            user("work"),
            assistant("w1", U, edit("/w/work/alpha/a.md"), edit("/w/docs/demo/report/x.md")),
        ])
        rows = {r.session: r for r in m.collect("work/alpha", self.tmp.name, units_glob="work/*")}
        self.assertEqual(list(rows), ["dddd4444"])
        self.assertFalse(rows["dddd4444"].multi_unit)  # docs/ 下的呼叫不在 glob 內，不計
        self.assertEqual(rows["dddd4444"].share, 1.0)


if __name__ == "__main__":
    unittest.main()
