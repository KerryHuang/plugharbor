import json
import os
import socket
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

TOWER = Path(__file__).resolve().parent / "tower.py"
sys.path.insert(0, str(TOWER.parent))
import tower  # noqa: E402


def git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


class TowerTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        base = Path(self._tmp.name).resolve()
        self.home = base / "home"
        self.home.mkdir()
        self.repo = base / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-q", "-b", "main")
        git(self.repo, "config", "user.email", "t@example.com")
        git(self.repo, "config", "user.name", "t")
        (self.repo / "a.py").write_text("x\n")
        git(self.repo, "add", "a.py")
        git(self.repo, "commit", "-q", "-m", "init")
        self.tdir = self.repo / ".git" / "tower"

    def run_cli(self, cwd, *args):
        env = dict(os.environ, HOME=str(self.home))
        return subprocess.run(
            [sys.executable, str(TOWER), *args],
            cwd=cwd, env=env, capture_output=True, text=True,
        )

    def takeoff(self, cwd=None, goal="g", paths=("a.py",)):
        r = self.run_cli(cwd or self.repo, "takeoff", "--goal", goal, "--paths", *paths)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def flight(self, fid):
        return json.loads((self.tdir / "flights" / f"{fid}.json").read_text())

    def test_takeoff_creates_flight_in_git_common_dir(self):
        out = self.takeoff()
        f = self.flight(out["id"])
        self.assertEqual(f["state"], "flying")
        self.assertEqual(f["schema"], 1)
        self.assertEqual(len(f["host"]), 8)
        self.assertNotEqual(f["host"], socket.gethostname())
        self.assertEqual(out["overlaps"], [])

    def test_worktree_shares_board(self):
        out = self.takeoff()
        wt = self.repo.parent / "wt2"
        git(self.repo, "worktree", "add", "-q", "-b", "other", str(wt))
        r = self.run_cli(wt, "radar", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        ids = [f["id"] for f in json.loads(r.stdout)]
        self.assertIn(out["id"], ids)

    def test_second_takeoff_same_worktree_rejected(self):
        out = self.takeoff()
        r = self.run_cli(self.repo, "takeoff", "--goal", "g2", "--paths", "b.py")
        self.assertEqual(r.returncode, 2)
        self.assertIn(out["id"], r.stdout + r.stderr)

    def test_beat_updates_time_and_touched(self):
        out = self.takeoff()
        before = self.flight(out["id"])["beat"]
        r = self.run_cli(self.repo, "beat", "--touched", "a.py", str(self.repo / "a.py"))
        self.assertEqual(r.returncode, 0, r.stderr)
        f = self.flight(out["id"])
        self.assertEqual(f["touched"], ["a.py"])
        self.assertGreaterEqual(f["beat"], before)

    def test_beat_in_subdir_records_repo_relative_path(self):
        out = self.takeoff()
        sub = self.repo / "hooks"
        sub.mkdir()
        r = self.run_cli(sub, "beat", "--touched", "x.py", "../a.py")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.flight(out["id"])["touched"], ["hooks/x.py", "a.py"])

    def test_beat_backslash_path_normalized(self):
        out = self.takeoff()
        r = self.run_cli(self.repo, "beat", "--touched", "sub\\x.py")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.flight(out["id"])["touched"], ["sub/x.py"])

    def test_incoming_changes_and_scope_filters(self):
        git(self.repo, "checkout", "-q", "-b", "side")
        (self.repo / "src").mkdir()
        (self.repo / "src" / "c.py").write_text("c\n")
        (self.repo / "docs").mkdir()
        (self.repo / "docs" / "feature.md").write_text("f\n")
        git(self.repo, "add", "src/c.py", "docs/feature.md")
        git(self.repo, "commit", "-q", "-m", "side")
        git(self.repo, "checkout", "-q", "main")
        inc = tower.incoming_changes(self.repo, ["side", "not-a-ref", "-m", "sync", "main"])
        self.assertEqual(inc, {"src/c.py", "docs/feature.md"})
        self.assertEqual(tower.incoming_changes(self.repo, ["not-a-ref"]), set())
        self.assertEqual(tower.incoming_changes(self.repo, []), set())
        # 共用跑道檔與 scope override 的略過由 hook 端的 add_incoming_scope 負責
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "tower_landing_hook", TOWER.parents[3] / "hooks" / "tower-landing.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        me = {"paths": ["docs/**"], "overrides": []}
        res = {"scope_extra": [], "code": 0}
        mod.add_incoming_scope(tower, me, str(self.repo), ["side"], res)
        self.assertEqual((res["scope_extra"], res["code"]), (["src/c.py"], 10))  # docs/feature.md 在範圍內
        res = {"scope_extra": [], "code": 0}
        mod.add_incoming_scope(tower, dict(me, paths=[]), str(self.repo), ["side"], res)
        self.assertEqual(res["scope_extra"], ["src/c.py"])  # docs/feature.md 是共用跑道
        res = {"scope_extra": [], "code": 0}
        mod.add_incoming_scope(tower, dict(me, overrides=[{"kind": "scope"}]), str(self.repo), ["side"], res)
        self.assertEqual((res["scope_extra"], res["code"]), ([], 0))

    def _race(self, args, mutate):
        """in-process 跑 CLI；_target 回傳後呼叫 mutate，模擬讀寫之間航班檔被改。"""
        from unittest import mock
        real = tower._target

        def racing(a, tdir, root):
            f = real(a, tdir, root)
            mutate(f)
            return f

        old = os.getcwd()
        os.chdir(self.repo)
        try:
            with mock.patch.object(tower, "_target", racing):
                return tower.main(args)
        finally:
            os.chdir(old)

    def test_cli_writes_skip_released_or_landed_flight(self):
        out = self.takeoff()
        path = self.tdir / "flights" / f"{out['id']}.json"
        for args in (["beat"], ["amend", "--goal", "z"], ["override", "--kind", "scope", "--reason", "r"]):
            self.assertEqual(self._race(args, lambda f: path.unlink()), 1, args)
            self.assertFalse(path.exists(), args)
            out = self.takeoff()
            path = self.tdir / "flights" / f"{out['id']}.json"
            code = self._race(args, lambda f: self.set_state(f["id"], "landed"))
            self.assertEqual(code, 1, args)
            self.assertEqual(self.flight(out["id"])["state"], "landed", args)
            path.unlink()
            out = self.takeoff()
            path = self.tdir / "flights" / f"{out['id']}.json"

    def set_state(self, fid, state):
        p = self.tdir / "flights" / f"{fid}.json"
        d = json.loads(p.read_text())
        d["state"] = state
        p.write_text(json.dumps(d))

    def test_paths_backslash_normalized(self):
        out = self.takeoff(paths=("docs\\sub\\**",))
        self.assertEqual(self.flight(out["id"])["paths"], ["docs/sub/**"])
        r = self.run_cli(self.repo, "amend", "--paths", "src\\a.py", "b.py")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.flight(out["id"])["paths"], ["src/a.py", "b.py"])

    def test_release_deletes_file_and_logs(self):
        out = self.takeoff()
        r = self.run_cli(self.repo, "release")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse((self.tdir / "flights" / f"{out['id']}.json").exists())
        last = (self.tdir / "log.jsonl").read_text().strip().splitlines()[-1]
        self.assertEqual(json.loads(last)["kind"], "release")

    def test_corrupt_flight_skipped(self):
        self.takeoff()
        (self.tdir / "flights" / "bad.json").write_text("{")
        r = self.run_cli(self.repo, "radar")
        self.assertEqual(r.returncode, 0)
        self.assertIn("bad.json", r.stderr)

    def test_amend_override_landed(self):
        out = self.takeoff()
        r = self.run_cli(self.repo, "amend", "--goal", "new", "--paths", "x/**")
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self.run_cli(self.repo, "override", "--kind", "scope", "--reason", "why")
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self.run_cli(self.repo, "landed")
        self.assertEqual(r.returncode, 0, r.stderr)
        f = self.flight(out["id"])
        self.assertEqual(f["goal"], "new")
        self.assertEqual(f["paths"], ["x/**"])
        self.assertEqual(f["overrides"][0]["reason"], "why")
        self.assertEqual(f["state"], "landed")

    # ---- Task 2 ----

    def fake(self, fid, **kw):
        wt = self.repo.parent / f"wt-{fid}"
        wt.mkdir(exist_ok=True)
        f = {"id": fid, "schema": 1, "goal": f"goal-{fid}",
             "work": {"segment": None, "feature": None, "ticket": None},
             "paths": [], "touched": [], "branch": "b", "worktree": str(wt),
             "session": "", "cli": "claude", "host": "00000000", "mode": "",
             "started": "2026-01-01T00:00:00+00:00",
             "beat": datetime.now(timezone.utc).isoformat(timespec="seconds"),
             "overrides": [], "state": "flying"}
        work = kw.pop("work", {})
        f["work"].update(work)
        f.update(kw)
        d = self.tdir / "flights"
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{fid}.json").write_text(json.dumps(f))
        return f

    def take(self, *extra, paths=("a.py",)):
        r = self.run_cli(self.repo, "takeoff", "--goal", "me", "--paths", *paths, *extra)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    B = "20260101-0000-aaaa"

    def test_same_segment_is_work_overlap(self):
        self.fake(self.B, work={"segment": "a7"})
        out = self.take("--segment", "a7")
        self.assertEqual(out["overlaps"][0]["kind"], "work")
        self.assertEqual(out["overlaps"][0]["flight"], self.B)

    def test_same_feature_or_ticket_is_work_overlap(self):
        self.fake(self.B, work={"feature": "login", "ticket": "T-1"})
        out = self.take("--feature", "login")
        self.assertEqual([o["kind"] for o in out["overlaps"]], ["work"])
        self.run_cli(self.repo, "release")
        out = self.take("--ticket", "T-1")
        self.assertEqual([o["kind"] for o in out["overlaps"]], ["work"])

    def test_path_overlap_glob(self):
        self.fake(self.B, touched=["plugins/toolkit/hooks/x.py"])
        out = self.take(paths=("plugins/toolkit/**",))
        self.assertEqual(out["overlaps"][0]["kind"], "path")
        self.assertIn("plugins/toolkit/hooks/x.py", out["overlaps"][0]["detail"])

    def test_shared_runway_excluded(self):
        self.fake(self.B, touched=["docs/feature.md", "plugins/a/CHANGELOG.md"])
        out = self.take(paths=("docs/feature.md", "plugins/a/CHANGELOG.md"))
        self.assertEqual(out["overlaps"], [])

    def test_project_shared_config(self):
        self.fake(self.B, touched=["README.md"])
        self.assertEqual(len(self.take(paths=("README.md",))["overlaps"]), 1)
        self.run_cli(self.repo, "release")
        (self.repo / ".plugharbor").mkdir()
        (self.repo / ".plugharbor" / "tower.yml").write_text("shared:\n  - README.md\n")
        self.assertEqual(self.take(paths=("README.md",))["overlaps"], [])

    def test_lost_flight_not_overlap(self):
        old = (datetime.now(timezone.utc) - timedelta(minutes=31)).isoformat(timespec="seconds")
        self.fake(self.B, work={"segment": "a7"}, beat=old)
        self.assertEqual(self.take("--segment", "a7")["overlaps"], [])
        r = self.run_cli(self.repo, "radar", "--json")
        states = {f["id"]: f["state"] for f in json.loads(r.stdout)}
        self.assertEqual(states[self.B], "lost")

    def test_missing_worktree_is_lost(self):
        f = self.fake(self.B)
        f["worktree"] = str(self.repo.parent / "gone")
        self.assertTrue(tower.is_lost(f, datetime.now(timezone.utc)))
        f["worktree"] = str(self.repo)
        self.assertFalse(tower.is_lost(f, datetime.now(timezone.utc)))

    def test_beat_outputs_overlaps(self):
        self.take("--segment", "a7")
        self.fake(self.B, work={"segment": "a7"})
        r = self.run_cli(self.repo, "beat")
        self.assertEqual(json.loads(r.stdout)["overlaps"][0]["kind"], "work")

    def test_match_glob(self):
        self.assertTrue(tower.match("a/b/CHANGELOG.md", "**/CHANGELOG.md"))
        self.assertTrue(tower.match("CHANGELOG.md", "**/CHANGELOG.md"))
        self.assertTrue(tower.match("a/b/c.py", "a/**"))
        self.assertFalse(tower.match("a/b/c.py", "a/*"))
        self.assertTrue(tower.match("a/c.py", "a/*.py"))

    def test_match_dir_prefix(self):
        self.assertTrue(tower.match("backend/tests/a.py", "backend/tests"))
        self.assertTrue(tower.match("backend/tests/a.py", "backend/tests/"))
        self.assertTrue(tower.match("backend/tests", "backend/tests/"))
        self.assertFalse(tower.match("backend/tests2/a.py", "backend/tests"))
        self.assertTrue(tower._in_scope("backend/src/x/y.py", ["backend/src"]))
        self.assertTrue(tower._path_hits("backend/src", "backend/src/x.py"))
        self.assertTrue(tower._path_hits("backend/src/x.py", "backend/src"))

    def test_dir_vs_file_overlap(self):
        self.fake(self.B, touched=["backend/src/x.py"])
        out = self.take(paths=("backend/src",))
        self.assertEqual(out["overlaps"][0]["kind"], "path")

    def test_repeated_paths_flag_accumulates(self):
        r = self.run_cli(self.repo, "takeoff", "--goal", "g", "--paths", "backend/src",
                         "--paths", "backend/tests")
        self.assertEqual(r.returncode, 0, r.stderr)
        fid = json.loads(r.stdout)["id"]
        self.assertEqual(self.flight(fid)["paths"], ["backend/src", "backend/tests"])
        r = self.run_cli(self.repo, "amend", "--paths", "a.py", "--paths", "b.py")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.flight(fid)["paths"], ["a.py", "b.py"])

    def test_warns_stale_in_progress_feature(self):
        (self.repo / "docs").mkdir()
        (self.repo / "docs" / "feature.md").write_text(
            "- [ ] 🚧 登入流程\n- [x] 其他\n")
        out = self.take("--feature", "登入流程")
        self.assertEqual(len(out["warnings"]), 1)
        self.assertIn("登入流程", out["warnings"][0])
        self.run_cli(self.repo, "release")
        self.fake(self.B, work={"feature": "登入流程"})
        self.assertEqual(self.take("--feature", "登入流程")["warnings"], [])

    def test_non_dict_flight_json_skipped(self):
        self.takeoff()
        (self.tdir / "flights" / "arr.json").write_text("[1]")
        r = self.run_cli(self.repo, "radar")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("arr.json", r.stderr)

    def test_bad_id_rejected(self):
        self.takeoff()
        r = self.run_cli(self.repo, "release", "--id", "../../x")
        self.assertEqual(r.returncode, 2)

    # ---- land-check ----

    def mkwt(self, name, paths=("a.py",), feature=None):
        wt = self.repo.parent / name
        git(self.repo, "worktree", "add", "-q", "-b", name, str(wt))
        args = ["takeoff", "--goal", name, "--paths", *paths]
        if feature:
            args += ["--feature", feature]
        r = self.run_cli(wt, *args)
        self.assertEqual(r.returncode, 0, r.stderr)
        return wt, json.loads(r.stdout)["id"]

    def land(self, wt):
        r = self.run_cli(wt, "land-check")
        return r.returncode, json.loads(r.stdout)

    def test_clean_land_returns_0(self):
        wt, _ = self.mkwt("fa")
        (wt / "a.py").write_text("y\n")
        code, out = self.land(wt)
        self.assertEqual(code, 0, out)
        self.assertEqual(out["code"], 0)

    def test_scope_extra_returns_10(self):
        wt, _ = self.mkwt("fa")
        (wt / "x.txt").write_text("y\n")
        code, out = self.land(wt)
        self.assertEqual(code, 10)
        self.assertEqual(out["scope_extra"], ["x.txt"])

    def test_override_clears_10(self):
        wt, _ = self.mkwt("fa")
        (wt / "x.txt").write_text("y\n")
        r = self.run_cli(wt, "override", "--kind", "scope", "--reason", "r")
        self.assertEqual(r.returncode, 0, r.stderr)
        code, _ = self.land(wt)
        self.assertEqual(code, 0)

    def test_collision_actual_changes_returns_11(self):
        wa, _ = self.mkwt("fa")
        wb, _ = self.mkwt("fb")
        (wb / "a.py").write_text("b\n")
        (wa / "a.py").write_text("a\n")
        code, out = self.land(wa)
        self.assertEqual(code, 11)
        self.assertEqual(out["collisions"][0]["files"], ["a.py"])

    def test_declared_only_not_collision(self):
        wa, _ = self.mkwt("fa")
        self.mkwt("fb")
        (wa / "a.py").write_text("a\n")
        code, out = self.land(wa)
        self.assertEqual(code, 0, out)
        self.assertEqual(out["collisions"], [])

    def _advance_main(self):
        (self.repo / "m.txt").write_text("m\n")
        git(self.repo, "add", "m.txt")
        git(self.repo, "commit", "-q", "-m", "m")

    def test_same_worktree_sibling_not_self_collision(self):
        wa, fid = self.mkwt("fa")
        (wa / "a.py").write_text("a\n")
        me = self.flight(fid)
        sibling = dict(me, id="20260101-0000-abcd", goal="dup")
        tower.save_flight(self.tdir, sibling)
        code, out = self.land(wa)
        self.assertEqual(code, 0, out)
        self.assertEqual(out["collisions"], [])
        self.assertEqual(tower.compute_overlaps(self.tdir, me), [])

    def test_behind_main_returns_12(self):
        wa, _ = self.mkwt("fa")
        self._advance_main()
        code, out = self.land(wa)
        self.assertEqual(code, 12)
        self.assertTrue(out["behind"])

    def test_priority_11_over_12_over_10(self):
        wa, _ = self.mkwt("fa")
        wb, _ = self.mkwt("fb")
        (wb / "a.py").write_text("b\n")
        self._advance_main()
        (wa / "a.py").write_text("a\n")
        (wa / "x.txt").write_text("x\n")
        code, out = self.land(wa)
        self.assertEqual(code, 11)
        self.assertTrue(out["behind"])
        self.assertEqual(out["scope_extra"], ["x.txt"])
        git(wb, "checkout", "-q", "a.py")  # B 還原後不再碰撞，剩 12 > 10
        code, _ = self.land(wa)
        self.assertEqual(code, 12)

    def test_shared_runway_not_collision(self):
        wa, _ = self.mkwt("fa", paths=("docs/feature.md",))
        wb, _ = self.mkwt("fb", paths=("docs/feature.md",))
        for w in (wa, wb):
            (w / "docs").mkdir(exist_ok=True)
            (w / "docs" / "feature.md").write_text(f"{w.name}\n")
        code, out = self.land(wa)
        self.assertNotEqual(code, 11, out)
        self.assertEqual(out["collisions"], [])

    def test_lost_flight_touch_is_warning(self):
        wa, _ = self.mkwt("fa")
        wb, bid = self.mkwt("fb")
        (wb / "a.py").write_text("b\n")
        f = self.flight(bid)
        f["beat"] = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        f["touched"] = ["a.py"]
        (self.tdir / "flights" / f"{bid}.json").write_text(json.dumps(f))
        (wa / "a.py").write_text("a\n")
        code, out = self.land(wa)
        self.assertNotEqual(code, 11, out)
        self.assertTrue(any(bid in w for w in out["warnings"]), out)

    def test_lost_missing_worktree_no_crash(self):
        wa, _ = self.mkwt("fa")
        wb, bid = self.mkwt("fb")
        f = self.flight(bid)
        f["touched"] = ["a.py"]
        (self.tdir / "flights" / f"{bid}.json").write_text(json.dumps(f))
        subprocess.run(["rm", "-rf", str(wb)], check=True)
        (wa / "a.py").write_text("a\n")
        code, out = self.land(wa)
        self.assertEqual(code, 0, out)
        self.assertTrue(any(bid in w for w in out["warnings"]), out)

    def test_feature_not_checked_warning(self):
        wa, _ = self.mkwt("fa", feature="塔台")
        (wa / "docs").mkdir()
        fm = wa / "docs" / "feature.md"
        fm.write_text("- [ ] 📋 塔台\n")
        _, out = self.land(wa)
        self.assertTrue(any("feature.md" in w for w in out["warnings"]), out)
        fm.write_text("- [x] 塔台\n")
        _, out = self.land(wa)
        self.assertFalse(any("feature.md" in w for w in out["warnings"]), out)

    def test_flight_missing_keys_skipped(self):
        self.takeoff()
        (self.tdir / "flights" / "bad.json").write_text('{"id": "x"}')
        r = self.run_cli(self.repo, "radar")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("bad.json", r.stderr)

    def test_on_default_branch_uses_origin_base(self):
        bare = self.repo.parent / "origin.git"
        subprocess.run(["git", "init", "-q", "--bare", str(bare)], check=True)
        git(self.repo, "remote", "add", "origin", str(bare))
        git(self.repo, "push", "-q", "origin", "main")
        self.takeoff()
        (self.repo / "c.txt").write_text("c\n")
        git(self.repo, "add", "c.txt")
        git(self.repo, "commit", "-q", "-m", "c")
        (self.repo / "a.py").write_text("y\n")
        self.assertEqual(tower.actual_changes(self.repo, "origin/main"),
                         {"a.py", "c.txt"})
        code, out = self.land(self.repo)
        self.assertEqual(code, 10)
        self.assertEqual(out["scope_extra"], ["c.txt"])

    def test_on_default_branch_no_origin_uncommitted(self):
        self.takeoff()
        (self.repo / "a.py").write_text("y\n")
        (self.repo / "x.txt").write_text("x\n")
        code, out = self.land(self.repo)
        self.assertEqual(code, 10)
        self.assertEqual(out["scope_extra"], ["x.txt"])

    def test_default_branch_fallback(self):
        self.assertEqual(tower.default_branch(self.repo), "main")


if __name__ == "__main__":
    unittest.main()
