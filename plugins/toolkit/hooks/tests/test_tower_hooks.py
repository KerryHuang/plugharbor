"""tower hooks 測試：心跳／改動追蹤（tower-track）、進 main 前核對（tower-landing）、開場摘要（tower-context）。

一律用 tmp repo、HOME 指向 tmp；不碰真的家目錄或 repo。
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
HOOKS = PLUGIN / "hooks"
TOWER = PLUGIN / "skills" / "tower" / "scripts" / "tower.py"
RUN_PY = HOOKS / "run-py.sh"


def git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


class HookTest(unittest.TestCase):
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
        self.base = base

    # ---- helpers ----

    def env(self, **extra):
        e = {k: v for k, v in os.environ.items()
             if k not in ("AGENT_DISPATCH_UNATTENDED", "CLAUDE_PLUGIN_ROOT")}
        e.update(HOME=str(self.home), USERPROFILE=str(self.home))
        e.update(extra)
        return e

    def run_cli(self, cwd, *args):
        r = subprocess.run([sys.executable, str(TOWER), *args], cwd=cwd, env=self.env(),
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r

    def takeoff(self, cwd=None, goal="g", paths=("a.py",), *extra):
        r = self.run_cli(cwd or self.repo, "takeoff", "--goal", goal, "--paths", *paths, *extra)
        return json.loads(r.stdout)["id"]

    def mkwt(self, name, branch=None, paths=("a.py",)):
        wt = self.base / name
        git(self.repo, "worktree", "add", "-q", "-b", branch or name, str(wt))
        return wt, self.takeoff(wt, name, paths)

    def flight(self, fid):
        return json.loads((self.tdir / "flights" / f"{fid}.json").read_text())

    def set_flight(self, fid, **kv):
        f = self.flight(fid)
        f.update(kv)
        (self.tdir / "flights" / f"{fid}.json").write_text(json.dumps(f))

    def hook(self, name, payload, cwd=None, raw=None, env=None, shell=False):
        cwd = str(cwd or self.repo)
        if isinstance(payload, dict):
            payload = dict({"cwd": cwd}, **payload)
        data = raw if raw is not None else json.dumps(payload)
        cmd = (["sh", str(RUN_PY), name] if shell else [sys.executable, str(HOOKS / name)])
        return subprocess.run(cmd, input=data, cwd=cwd, env=env or self.env(),
                              capture_output=True, text=True, encoding="utf-8")

    def landing(self, command, cwd=None, env=None):
        r = self.hook("tower-landing.py", {
            "hook_event_name": "PreToolUse", "tool_name": "Bash",
            "tool_input": {"command": command}}, cwd=cwd, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)["hookSpecificOutput"] if r.stdout.strip() else None

    def track(self, event, cwd=None, **payload):
        r = self.hook("tower-track.py", dict({"hook_event_name": event}, **payload), cwd=cwd)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r

    def old_beat(self, fid):
        old = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat(timespec="seconds")
        self.set_flight(fid, beat=old)
        return old

    def dirty_extra(self, wt):
        (wt / "x.txt").write_text("y\n")


class LandingTest(HookTest):
    def test_commit_on_main_triggers(self):
        self.takeoff()
        self.dirty_extra(self.repo)
        out = self.landing("git commit -m x")
        self.assertEqual(out["hookEventName"], "PreToolUse")
        self.assertEqual(out["permissionDecision"], "deny")
        self.assertIn("override --kind scope --reason", out["permissionDecisionReason"])
        self.assertIn("x.txt", out["permissionDecisionReason"])

    def test_branch_commit_not_checked(self):
        wt, _ = self.mkwt("fa", branch="feat/x")
        self.dirty_extra(wt)
        self.assertIsNone(self.landing("git commit -m x", cwd=wt))

    def test_merge_into_main_triggers(self):
        self._collide()
        self.assertEqual(self.landing("git merge feat/x")["permissionDecision"], "ask")

    def test_rebase_on_main_triggers(self):
        self._collide()
        self.assertEqual(self.landing("git rebase origin/main")["permissionDecision"], "ask")

    def test_sync_on_main_ignores_scope_extra(self):
        self.takeoff()
        self.dirty_extra(self.repo)
        self.assertIsNone(self.landing("git merge origin/main"))
        self.assertIsNone(self.landing("git rebase origin/main"))
        self.assertEqual(self.landing("git commit -m x")["permissionDecision"], "deny")
        self.assertEqual(self.landing("git push origin main")["permissionDecision"], "deny")

    def test_merge_feature_from_flighted_main_checks_feature_flight(self):
        main_id = self.takeoff()
        wt, fid = self.mkwt("fa", branch="feat/x")
        self.dirty_extra(wt)
        for cmd in ("git merge feat/x", "git rebase main feat/x", "git push origin feat/x:main"):
            out = self.landing(cmd)
            self.assertEqual(out["permissionDecision"], "deny", cmd)
            self.assertIn(fid, out["permissionDecisionReason"], cmd)
            self.assertIn(f"--id {fid}", out["permissionDecisionReason"], cmd)
            self.assertNotIn(main_id, out["permissionDecisionReason"], cmd)

    def test_merge_unflighted_branch_from_flighted_main_checks_own_flight(self):
        self.takeoff()
        self.dirty_extra(self.repo)
        # 併入無航班的本地分支視為落地，照常核對自己的航班；只同步遠端預設分支才免
        self.assertEqual(self.landing("git merge feat/other")["permissionDecision"], "deny")
        self.assertIsNone(self.landing("git rebase origin/main"))
        self.assertEqual(self.landing("git push origin feat/other:main")["permissionDecision"], "deny")

    def _branch(self, name, files):
        git(self.repo, "checkout", "-q", "-b", name)
        for f, text in files.items():
            (self.repo / f).parent.mkdir(parents=True, exist_ok=True)
            (self.repo / f).write_text(text)
            git(self.repo, "add", f)
        git(self.repo, "commit", "-q", "-m", name)
        git(self.repo, "checkout", "-q", "main")

    def test_checkout_main_then_merge_is_landing(self):
        git(self.repo, "checkout", "-q", "-b", "feat/x")
        self.takeoff()
        self.dirty_extra(self.repo)
        for cmd in ("git checkout main && git merge feat/x", "git switch main && git merge feat/x",
                    "git checkout main; git rebase feat/x", "git checkout main && git commit -m x"):
            self.assertEqual(self.landing(cmd)["permissionDecision"], "deny", cmd)
        self.assertIsNone(self.landing("git merge main"))

    def test_checkout_other_branch_then_commit_not_landing(self):
        self.takeoff()
        self.dirty_extra(self.repo)
        git(self.repo, "branch", "feat/y")
        self.assertIsNone(self.landing("git checkout feat/y && git commit -m x"))
        self.assertIsNone(self.landing("git switch feat/y && git commit -m x"))
        # 不是既有分支名（檔案、新分支、-- 路徑、.）不改變分支
        for cmd in ("git checkout a.py && git commit -m x", "git checkout -b feat/z && git commit -m x",
                    "git checkout -- a.py && git commit -m x", "git checkout . && git commit -m x"):
            self.assertEqual(self.landing(cmd)["permissionDecision"], "deny", cmd)

    def test_merge_local_branch_on_main_is_not_sync(self):
        self.takeoff(self.repo, "docs", ("docs/**",))
        self._branch("temp-patch", {"src/core.py": "x\n"})
        out = self.landing("git merge temp-patch")
        self.assertEqual(out["permissionDecision"], "deny")
        self.assertIn("src/core.py", out["permissionDecisionReason"])
        self.assertEqual(self.landing("git rebase temp-patch")["permissionDecision"], "deny")
        # 範圍內的分支不擋
        self._branch("docs-fix", {"docs/a.md": "x\n"})
        self.assertIsNone(self.landing("git merge docs-fix"))

    def test_value_options_are_not_refs(self):
        self.takeoff(self.repo, "docs", ("docs/**",))
        self._branch("temp-patch", {"src/core.py": "x\n"})
        self.dirty_extra(self.repo)  # 同步免擋範圍：有範圍外檔也要靜默（帶值選項的值不能被當成 ref）
        for cmd in ("git merge -m sync origin/main", "git merge -m 'sync up' origin/main",
                    "git merge -X theirs origin/main", "git merge -s ours origin/main",
                    "git merge --message=sync origin/main", "git merge -msync origin/main",
                    "git merge -F msg.txt origin/main", "git rebase -X theirs origin/main",
                    "git rebase --onto origin/main origin/main"):
            self.assertIsNone(self.landing(cmd), cmd)
        for cmd in ("git merge -m x temp-patch", "git merge -X theirs temp-patch",
                    "git rebase --onto origin/main main temp-patch"):
            self.assertEqual(self.landing(cmd)["permissionDecision"], "deny", cmd)

    def test_push_value_options_skipped(self):
        self.takeoff(self.repo, "docs", ("docs/**",))
        self.dirty_extra(self.repo)
        self.assertIsNone(self.landing("git push -o ci.skip origin feat/x"))
        self.assertEqual(self.landing("git push -o ci.skip origin main")["permissionDecision"], "deny")

    def test_sync_forms_still_exempt(self):
        self.takeoff(self.repo, "docs", ("docs/**",))
        self.dirty_extra(self.repo)
        for cmd in ("git merge origin/main", "git rebase origin/main", "git rebase", "git merge --ff-only",
                    "git merge --ff-only origin/main", "git merge FETCH_HEAD", "git merge @{u}",
                    "git merge @{upstream}", "git rebase remotes/origin/main", "git merge main"):
            self.assertIsNone(self.landing(cmd), cmd)

    def test_merge_feature_from_unflighted_main_checks_feature_flight(self):
        wt, fid = self.mkwt("fa", branch="feat/x")
        self.dirty_extra(wt)
        out = self.landing("git merge --ff-only feat/x")
        self.assertEqual(out["permissionDecision"], "deny")
        self.assertIn(fid, out["permissionDecisionReason"])
        self.assertIn(f"--id {fid}", out["permissionDecisionReason"])
        self.assertEqual(self.landing("git rebase main feat/x")["permissionDecision"], "deny")
        self.assertEqual(self.landing("git push origin feat/x:main")["permissionDecision"], "deny")
        self.assertIsNone(self.landing("git push origin feat/x"))
        self.assertIsNone(self.landing("git merge feat/other"))

    def test_merge_on_branch_not_checked(self):
        wt, _ = self.mkwt("fa", branch="feat/x")
        self.dirty_extra(wt)
        self.assertIsNone(self.landing("git merge main", cwd=wt))
        self.assertIsNone(self.landing("git rebase main", cwd=wt))

    def test_push_default_triggers(self):
        self.takeoff()
        self.dirty_extra(self.repo)
        self.assertEqual(self.landing("git push origin main")["permissionDecision"], "deny")
        self.assertEqual(self.landing("git push")["permissionDecision"], "deny")
        self.assertEqual(self.landing("git push -u origin HEAD:main")["permissionDecision"], "deny")

    def test_push_default_from_feature_branch_triggers(self):
        wt, _ = self.mkwt("fa", branch="feat/x")
        self.dirty_extra(wt)
        self.assertEqual(self.landing("git push origin main", cwd=wt)["permissionDecision"], "deny")
        self.assertIsNone(self.landing("git push origin feat/x", cwd=wt))
        self.assertIsNone(self.landing("git push", cwd=wt))

    def test_push_non_default_not_checked(self):
        self.takeoff()
        self.dirty_extra(self.repo)
        self.assertIsNone(self.landing("git push origin feat/x"))

    def test_compound_command_and_git_dash_c(self):
        self.takeoff()
        self.dirty_extra(self.repo)
        self.assertEqual(self.landing("git add a.py && git commit -m x")["permissionDecision"], "deny")
        other = self.base / "elsewhere"
        other.mkdir()
        self.assertEqual(self.landing(f"git -C {self.repo} commit -m x", cwd=other)["permissionDecision"], "deny")

    def test_cd_into_main_from_feature_worktree_triggers(self):
        self.takeoff()
        self.dirty_extra(self.repo)
        wt, _ = self.mkwt("fa", branch="feat/x")
        self.assertIsNone(self.landing("git commit -m x", cwd=wt))
        self.assertEqual(self.landing(f"cd {self.repo} && git commit -m x", cwd=wt)["permissionDecision"], "deny")
        self.assertEqual(self.landing("cd ../repo && git commit -m x", cwd=wt)["permissionDecision"], "deny")
        self.assertEqual(self.landing("cd .. && cd repo && git commit -m x", cwd=wt)["permissionDecision"], "deny")

    def test_cd_subshell_and_trailing_paren(self):
        self.takeoff()
        self.dirty_extra(self.repo)
        wt, _ = self.mkwt("fa", branch="feat/x")
        self.assertEqual(self.landing(f"(cd {self.repo} && git commit -m y)", cwd=wt)["permissionDecision"], "deny")

    def test_cd_into_feature_worktree_judged_by_its_branch(self):
        self.takeoff()
        self.dirty_extra(self.repo)
        wt, _ = self.mkwt("fa", branch="feat/x")
        self.assertIsNone(self.landing(f"cd {wt} && git commit -m x"))
        self.assertIsNone(self.landing(f"cd {wt}; git commit -m x"))

    def test_git_dash_c_stacks_on_cd_and_expands_tilde(self):
        self.takeoff()
        self.dirty_extra(self.repo)
        (self.home / "proj").symlink_to(self.repo)
        other = self.base / "elsewhere"
        other.mkdir()
        self.assertEqual(self.landing("git -C ~/proj commit -m x", cwd=other)["permissionDecision"], "deny")
        self.assertEqual(self.landing("cd ~ && git -C proj commit -m x", cwd=other)["permissionDecision"], "deny")
        self.assertEqual(self.landing("cd ~/proj && git commit -m x", cwd=other)["permissionDecision"], "deny")

    def test_non_landing_commands_silent(self):
        self.takeoff()
        self.dirty_extra(self.repo)
        for c in ("git status", "git log --oneline", "ls", "echo git commit", "git branch -d x"):
            self.assertIsNone(self.landing(c), c)

    def _collide(self, mode_args=()):
        fid = self.takeoff(self.repo, "main", ("a.py",), *mode_args)
        wb, _ = self.mkwt("fb")
        (wb / "a.py").write_text("b\n")
        (self.repo / "a.py").write_text("a\n")
        return fid

    def test_collision_asks_when_attended(self):
        self._collide()
        out = self.landing("git commit -m x")
        self.assertEqual(out["permissionDecision"], "ask")
        self.assertIn("a.py", out["permissionDecisionReason"])

    def test_collision_denies_when_unattended_env(self):
        self._collide()
        out = self.landing("git commit -m x", env=self.env(AGENT_DISPATCH_UNATTENDED="1"))
        self.assertEqual(out["permissionDecision"], "deny")
        self.assertIn("排隊", out["permissionDecisionReason"])

    def test_collision_denies_when_flight_unattended(self):
        fid = self._collide(("--mode", "unattended"))
        out = self.landing("git commit -m x")
        self.assertEqual(out["permissionDecision"], "deny")
        self.assertIn("排隊", out["permissionDecisionReason"])
        self.assertIn(self.landing_other_id(fid), out["permissionDecisionReason"])

    def landing_other_id(self, mine):
        return next(p.stem for p in (self.tdir / "flights").glob("*.json") if p.stem != mine)

    def test_behind_denies_with_rebase_hint(self):
        wa, _ = self.mkwt("fa", branch="feat/x")
        (self.repo / "m.txt").write_text("m\n")
        git(self.repo, "add", "m.txt")
        git(self.repo, "commit", "-q", "-m", "m")
        out = self.landing("git push origin main", cwd=wa)
        self.assertEqual(out["permissionDecision"], "deny")
        self.assertIn("rebase", out["permissionDecisionReason"])

    def test_warnings_surface_without_blocking(self):
        self.takeoff(self.repo, "g", ("a.py",), "--feature", "F-1")
        (self.repo / "docs").mkdir()
        (self.repo / "docs" / "feature.md").write_text("- [ ] F-1 做某事\n")
        (self.repo / "a.py").write_text("y\n")
        out = self.landing("git commit -m x")
        self.assertNotIn("permissionDecision", out)
        self.assertIn("F-1", out["additionalContext"])

    def test_no_flight_no_block(self):
        self.dirty_extra(self.repo)
        for c in ("git commit -m x", "git merge feat/x", "git push origin main"):
            self.assertIsNone(self.landing(c), c)

    def test_clean_land_silent(self):
        self.takeoff()
        (self.repo / "a.py").write_text("y\n")
        self.assertIsNone(self.landing("git commit -am x"))


class TrackTest(HookTest):
    def run_track_inproc(self, payload, before_write):
        """in-process 跑 tower-track.main；find_flight 回傳後呼叫 before_write，模擬讀寫之間檔案被改。"""
        import importlib.util
        import io
        from unittest import mock
        sys.path.insert(0, str(TOWER.parent))
        import tower
        spec = importlib.util.spec_from_file_location("tower_track_hook", HOOKS / "tower-track.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        real = tower.find_flight

        def racing(tdir, root):
            f = real(tdir, root)
            before_write(f)
            return f

        stdin = io.TextIOWrapper(io.BytesIO(json.dumps(payload).encode("utf-8")), encoding="utf-8")
        stdout = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
        with mock.patch.object(tower, "find_flight", racing), mock.patch.object(sys, "stdin", stdin), \
                mock.patch.object(sys, "stdout", stdout), mock.patch.object(sys, "stderr", sys.stderr):
            mod.main()

    def test_released_flight_not_resurrected(self):
        fid = self.takeoff()
        path = self.tdir / "flights" / f"{fid}.json"
        self.run_track_inproc({"hook_event_name": "PreToolUse", "cwd": str(self.repo)},
                              lambda f: path.unlink())
        self.assertFalse(path.exists())

    def test_released_flight_not_resurrected_by_touch(self):
        fid = self.takeoff()
        path = self.tdir / "flights" / f"{fid}.json"
        self.run_track_inproc({"hook_event_name": "PostToolUse", "cwd": str(self.repo),
                               "tool_name": "Write", "tool_input": {"file_path": str(self.repo / "a.py")}},
                              lambda f: path.unlink())
        self.assertFalse(path.exists())

    def test_landed_flight_not_flipped_back(self):
        fid = self.takeoff()
        self.run_track_inproc(
            {"hook_event_name": "PreToolUse", "cwd": str(self.repo)},
            lambda f: self.set_flight(fid, state="landed"))
        self.assertEqual(self.flight(fid)["state"], "landed")

    def test_beat_updates_for_each_event(self):
        fid = self.takeoff()
        for ev, extra in (("PreToolUse", {"tool_name": "Bash", "tool_input": {"command": "ls"}}),
                          ("UserPromptSubmit", {"prompt": "hi"})):
            old = self.old_beat(fid)
            r = self.track(ev, **extra)
            self.assertEqual(r.stdout, "")
            self.assertGreater(self.flight(fid)["beat"], old, ev)

    def test_beat_from_subdir_and_worktree(self):
        fid = self.takeoff()
        sub = self.repo / "pkg" / "deep"
        sub.mkdir(parents=True)
        old = self.old_beat(fid)
        self.track("PreToolUse", cwd=sub, tool_name="Read", tool_input={})
        self.assertGreater(self.flight(fid)["beat"], old)
        wt, wid = self.mkwt("fb")
        old = self.old_beat(wid)
        self.track("PreToolUse", cwd=wt, tool_name="Read", tool_input={})
        self.assertGreater(self.flight(wid)["beat"], old)
        self.assertEqual(self.flight(fid)["touched"], [])

    def test_beat_spawns_no_git(self):
        fid = self.takeoff()
        wt, wid = self.mkwt("fb")
        fake = self.base / "fakebin"
        fake.mkdir()
        marker = self.base / "git-called"
        (fake / "git").write_text(f"#!/bin/sh\ntouch {marker}\nexit 1\n")
        (fake / "git").chmod(0o755)
        env = self.env(PATH=f"{fake}{os.pathsep}{os.environ['PATH']}")
        for cwd, f in ((self.repo, fid), (wt, wid)):
            old = self.old_beat(f)
            r = self.hook("tower-track.py", {"hook_event_name": "PreToolUse", "tool_name": "Bash",
                                              "tool_input": {}}, cwd=cwd, env=env)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertGreater(self.flight(f)["beat"], old)
        self.assertFalse(marker.exists())

    def test_beat_ignores_non_flying_and_other_worktree(self):
        fid = self.takeoff()
        self.set_flight(fid, state="landed")
        old = self.old_beat(fid)
        self.track("PreToolUse", tool_name="Read", tool_input={})
        self.assertEqual(self.flight(fid)["beat"], old)

    def test_touch_records_and_warns(self):
        a = self.takeoff()
        self.run_cli(self.repo, "beat", "--touched", "a.py")
        wb, b = self.mkwt("fb", paths=("b.py",))
        r = self.track("PostToolUse", cwd=wb, tool_name="Write",
                       tool_input={"file_path": str(wb / "a.py")})
        self.assertEqual(self.flight(b)["touched"], ["a.py"])
        out = json.loads(r.stdout)["hookSpecificOutput"]
        self.assertEqual(out["hookEventName"], "PostToolUse")
        self.assertIn(a, out["additionalContext"])
        self.assertNotIn("\n", out["additionalContext"])
        # 再改同一檔：已記錄過，不重複提醒也不重複記錄
        r = self.track("PostToolUse", cwd=wb, tool_name="Edit",
                       tool_input={"file_path": str(wb / "a.py")})
        self.assertEqual(r.stdout, "")
        self.assertEqual(self.flight(b)["touched"], ["a.py"])

    def test_touch_no_overlap_silent(self):
        self.takeoff()
        wb, b = self.mkwt("fb", paths=("b.py",))
        r = self.track("PostToolUse", cwd=wb, tool_name="Write",
                       tool_input={"file_path": str(wb / "sub" / "b.py")})
        self.assertEqual(r.stdout, "")
        self.assertEqual(self.flight(b)["touched"], ["sub/b.py"])

    def test_touch_outside_repo_file_not_recorded(self):
        fid = self.takeoff()
        old = self.old_beat(fid)
        self.track("PostToolUse", tool_name="Write", tool_input={"file_path": str(self.base / "o.txt")})
        f = self.flight(fid)
        self.assertEqual(f["touched"], [])
        self.assertGreater(f["beat"], old)

    def test_touch_lost_flight_not_warned(self):
        a = self.takeoff()
        self.run_cli(self.repo, "beat", "--touched", "a.py")
        self.old_beat(a)
        self.set_flight(a, beat=(datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(timespec="seconds"))
        wb, _ = self.mkwt("fb", paths=("b.py",))
        r = self.track("PostToolUse", cwd=wb, tool_name="Write", tool_input={"file_path": str(wb / "a.py")})
        self.assertEqual(r.stdout, "")

    def test_fail_open(self):
        fid = self.takeoff()
        (self.tdir / "flights" / "bad.json").write_text("{not json")
        for raw in ("", "{oops", "[]", "null"):
            for name in ("tower-track.py", "tower-landing.py", "tower-context.py"):
                r = self.hook(name, None, raw=raw)
                self.assertEqual((r.returncode, r.stdout), (0, ""), (name, raw))
        # 損毀航班檔不影響心跳
        old = self.old_beat(fid)
        self.track("PreToolUse", tool_name="Read", tool_input={})
        self.assertGreater(self.flight(fid)["beat"], old)

    def test_beat_fast(self):
        self.takeoff()
        payload = {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": "ls"},
                   "cwd": str(self.repo)}
        data = json.dumps(payload)
        env = self.env()
        cmd = [sys.executable, str(HOOKS / "tower-track.py")]
        base = [sys.executable, "-c", "pass"]

        def avg(cmd, data, n=100):
            t = time.perf_counter()
            for _ in range(n):
                subprocess.run(cmd, input=data, cwd=self.repo, env=env, capture_output=True, text=True)
            return (time.perf_counter() - t) / n * 1000

        beat = avg(cmd, data)
        floor = avg(base, "")
        touch_payload = json.dumps(dict(payload, hook_event_name="PostToolUse", tool_name="Write",
                                        tool_input={"file_path": str(self.repo / "a.py")}))
        touch = avg(cmd, touch_payload, 20)
        shell = avg(["sh", str(RUN_PY), "tower-track.py"], data, 20)
        print(f"\nTOWER_LATENCY beat_avg_ms={beat:.1f} (100 runs) touch_avg_ms={touch:.1f} (20 runs) "
              f"via_run-py.sh_beat_avg_ms={shell:.1f} (20 runs) python_bare_floor_ms={floor:.1f}")


class RegistrationTest(unittest.TestCase):
    def test_hooks_json_registers_tower_hooks(self):
        hooks = json.loads((HOOKS / "hooks.json").read_text(encoding="utf-8"))["hooks"]

        def reg(event):
            return {(g["matcher"], h["command"].rsplit(" ", 1)[1], h["timeout"])
                    for g in hooks[event] for h in g["hooks"]}

        self.assertIn((".*", "tower-track.py", 15), reg("PreToolUse"))
        self.assertIn(("Bash", "tower-landing.py", 15), reg("PreToolUse"))
        self.assertIn(("", "tower-track.py", 15), reg("UserPromptSubmit"))
        self.assertIn(("Edit|Write|MultiEdit", "tower-track.py", 15), reg("PostToolUse"))
        self.assertIn(("", "tower-context.py", 15), reg("SessionStart"))


class OutsideRepoTest(HookTest):
    def test_outside_git_repo_silent(self):
        outside = self.base / "plain"
        outside.mkdir()
        payloads = {
            "tower-track.py": {"hook_event_name": "PreToolUse", "tool_name": "Read", "tool_input": {}},
            "tower-landing.py": {"hook_event_name": "PreToolUse", "tool_name": "Bash",
                                 "tool_input": {"command": "git commit -m x"}},
            "tower-context.py": {"hook_event_name": "SessionStart", "source": "startup"},
        }
        for name, p in payloads.items():
            r = self.hook(name, p, cwd=outside)
            self.assertEqual((r.returncode, r.stdout), (0, ""), (name, r.stderr))
        r = self.hook("tower-track.py", {"hook_event_name": "PostToolUse", "tool_name": "Write",
                                          "tool_input": {"file_path": str(outside / "f")}}, cwd=outside)
        self.assertEqual((r.returncode, r.stdout), (0, ""))


class ContextTest(HookTest):
    def start(self, cwd=None):
        r = self.hook("tower-context.py", {"hook_event_name": "SessionStart", "source": "startup"}, cwd=cwd)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r

    def test_session_start_summary(self):
        self.takeoff(self.repo, "改登入流程")
        self.mkwt("fb")
        r = self.start()
        out = json.loads(r.stdout)["hookSpecificOutput"]
        self.assertEqual(out["hookEventName"], "SessionStart")
        line = out["additionalContext"]
        self.assertIn("2 班", line)
        self.assertNotIn("\n", line)
        self.assertLessEqual(len(line), 120)

    def test_session_start_long_goals_truncated(self):
        self.takeoff(self.repo, "很長的目標" * 20)
        for i in range(1, 4):
            self.mkwt(f"w{i}")
        line = json.loads(self.start().stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("4 班", line)
        self.assertLessEqual(len(line), 120)

    def test_session_start_excludes_lost(self):
        self.takeoff(self.repo, "活的")
        _, lost = self.mkwt("fb")
        self.set_flight(lost, beat=(datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(timespec="seconds"))
        line = json.loads(self.start().stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("1 班", line)
        self.assertNotIn("2 班", line)
        self.set_flight(self.takeoff_id_of_main(), beat=(datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(timespec="seconds"))
        self.assertEqual(self.start().stdout, "")

    def takeoff_id_of_main(self):
        return next(f["id"] for f in map(lambda p: json.loads(p.read_text()), (self.tdir / "flights").glob("*.json"))
                    if f["worktree"] == str(self.repo))

    def test_session_start_no_flights_empty(self):
        self.assertEqual(self.start().stdout, "")

    def test_session_start_ignores_landed(self):
        fid = self.takeoff()
        self.set_flight(fid, state="landed")
        self.assertEqual(self.start().stdout, "")

    def test_runs_via_run_py_sh(self):
        self.takeoff()
        r = self.hook("tower-context.py", {"hook_event_name": "SessionStart"}, shell=True)
        self.assertIn("1 班", r.stdout)


if __name__ == "__main__":
    unittest.main()
