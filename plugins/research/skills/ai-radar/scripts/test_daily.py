"""daily.py 測試：假 backlog、暫存 git repo、假 claude 腳本，不呼叫模型、不讀真資料。"""
import fcntl
import json
import os
import plistlib
import shutil
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("daily.py")
sys.path.insert(0, str(SCRIPT.parent))
import daily  # noqa: E402

GIT_ENV = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com"}
TODAY = "2026-11-09"  # 星期一
CI = "scripts/ci/"  # repo 根目錄的路徑（拆開寫，validate.py 的交互引用檢查才不會當成 plugin 內引用）

BACKLOG = textwrap.dedent("""\
    # 採納待辦

    | # | 來源 | 摘要 | 影響×可行性×契合度 | 狀態 | 建議交棒 | 決策備註 |
    |---|------|------|------|------|------|------|
    | 1 | a | 已駁回 | 3×3×3=27 | 駁回 | - | - |
    | 2 | b | 低分 | 1×3×2=6（原 12） | 待評估 | x | - |
    | 3 | c | 高分 A | 2×3×3=18 | 待評估 | x | - |
    | 4 | d | 高分 B | 2×3×3=18 | 採納 | x | 既有備註 |
    | 5 | e | 每日版略過過 | 3×3×3=27 | 待評估 | x | 每日版略過 2026-11-01：要實測 |
    | 6 | f | 沒分數 | - | 待評估 | x | - |
    | 7 | g | 已完成 | 3×3×3=27 | 已完成 | x | - |
    | 8 | h | 已有 branch | 3×3×2=18 | 進行中 | x | - |
    | 9 | i | 中分 | 2×2×3=12 | 待評估 | x | - |
    | 10 | j | 欄位壞掉 | 3×3×3=27 | 駁回 |
    """)

PROFILE = textwrap.dedent("""\
    # 工作模式

    ## Skill（含 slash command）

    | skill | 次數 |
    |---|---|
    | `superpowers:brainstorming` | 9 |
    | `secretco-kit:spec` | 5 |
    | `commit` | 3 |

    ## CLI

    | 指令 | 次數 |
    |---|---|
    | `git` | 9 |
    | `gh` | 3 |

    ## MCP server

    | server | 次數 |
    |---|---|
    | `secretco-hq` | 7 |
    | `linear` | 2 |
    """)

# 驗證器：import json（測 worktree 裡植入的 json.py 不會被載入）；plugins/p/BAD.md 存在就失敗
VALIDATE = textwrap.dedent("""\
    import json, sys
    from pathlib import Path
    ROOT = Path(__file__).resolve().parents[2]
    print("validate ok", json.dumps(ROOT.name))
    sys.exit(1 if (ROOT / "plugins" / "p" / "BAD.md").exists() else 0)
    """)


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True,
                          text=True, env=GIT_ENV).stdout.strip()


def make_repo(path, hook_marker):
    files = {
        f"{CI}validate.py": VALIDATE,
        "scripts/hooks/pre-commit": f"#!/bin/sh\ntouch '{hook_marker}'\n",
        ".gitignore": ".leak-denylist\n",
        "plugins/p/README.md": "# p\n",
    }
    path.mkdir(parents=True)
    git(path, "init", "-q", "-b", "main")
    for rel, text in files.items():
        (path / rel).parent.mkdir(parents=True, exist_ok=True)
        (path / rel).write_text(text, encoding="utf-8")
    (path / "scripts" / "hooks" / "pre-commit").chmod(0o755)
    git(path, "add", *files)
    git(path, "commit", "-q", "-m", "init")
    git(path, "config", "core.hooksPath", "scripts/hooks")  # 證明 runner 的 commit 不會跑 repo 的 hook
    (path / ".leak-denylist").write_text("secretco\n", encoding="utf-8")


# 假 claude：從 stdin 的 prompt 讀資料，依 FAKE_MODE 模擬階段 B 改檔／略過、階段 A 輸出更新表
FAKE_CLAUDE = textwrap.dedent("""\
    #!/usr/bin/env python3
    import json, os, re, sys
    args = sys.argv[1:]
    prompt = sys.stdin.read()
    out = os.environ["FAKE_OUT"]
    stage = "a" if "WebSearch" in args[args.index("--tools") + 1] else "b"
    ctx = json.loads(re.search(r"```json\\n(.*?)\\n```", prompt, re.S).group(1))
    calls = os.path.join(out, "calls-" + stage)
    n = len(open(calls).read().splitlines()) if os.path.exists(calls) else 0
    open(calls, "a").write("x\\n")
    open(os.path.join(out, "argv-" + stage + ".json"), "w").write(json.dumps(args))
    open(os.path.join(out, "prompt-" + stage + ".txt"), "w").write(prompt)
    def done(text, err=False, code=0):
        print(json.dumps({"type": "result", "is_error": err, "result": text,
                          "permission_denials": [{"tool_name": "Bash", "tool_input": {"command": "x"}}]}))
        sys.exit(code)
    if stage == "a":
        done("| claude-code | v9 | https://example.com 2026-11-09 | 無 |")
    mode = os.environ.get("FAKE_MODE", "draft").split(",")
    mode = mode[min(n, len(mode) - 1)]
    def write(rel, text="x\\n"):
        os.makedirs(os.path.dirname(rel) or ".", exist_ok=True)
        open(rel, "a", encoding="utf-8").write(text)
    if mode == "fail":
        done("boom", err=True, code=1)
    if mode == "skip":
        done("RESULT: SKIP 要實測")
    if mode == "skip-dirty":
        write("plugins/p/left.md")
        done("RESULT: SKIP 改到一半放棄")
    {"draft": lambda: write("plugins/p/README.md", "more\\n"),
     "zh": lambda: write("plugins/p/中文檔名.md"),
     "forbidden": lambda: write("scripts/ci/" + "evil" + ".py"),
     "outside": lambda: write("notes.md"),
     "ignored": lambda: write(".leak-denylist", ""),
     "bad": lambda: write("plugins/p/BAD.md"),
     "noformat": lambda: write("plugins/p/README.md", "more\\n")}[mode]()
    done("改好了" if mode == "noformat" else "說明在前\\nRESULT: DRAFT\\n**改了什麼**：README")
    """)


class BacklogTest(unittest.TestCase):
    def test_candidates_order_and_filters(self):
        self.assertEqual([c.num for c in daily.candidates(BACKLOG, taken={8})], [3, 4, 9, 2])

    def test_limit(self):
        self.assertEqual(len(daily.candidates(BACKLOG, set(), limit=2)), 2)

    def test_branch_numbers(self):
        self.assertEqual(daily.branch_numbers(["radar/2026-11-09-8", "radar/x", "radar/2026-11-10-12"]), {8, 12})

    def test_mark_backlog_only_touches_note_cell(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "b.md"
            p.write_text(BACKLOG, encoding="utf-8")
            daily.mark_backlog(p, 3, "每日版略過 2026-11-09：x")
            daily.mark_backlog(p, 4, "每日草稿 radar/2026-11-09-4（2026-11-09）")
            items = {c.num: c for c in daily.parse_backlog(p.read_text(encoding="utf-8"))}
            self.assertEqual(items[3].note, "每日版略過 2026-11-09：x")
            self.assertEqual(items[4].note, "既有備註；每日草稿 radar/2026-11-09-4（2026-11-09）")
            self.assertEqual(items[4].status, "採納")
            self.assertEqual(daily.candidates(p.read_text(encoding="utf-8"), set())[0].num, 8)


class ClaudeArgsTest(unittest.TestCase):
    """權限邊界：runner 組出的 claude 參數。"""

    def setUp(self):
        self.cfg = daily.Config(out=Path("/h/.claude/ai-radar"), repo=Path("/h/r"), worktree=Path("/h/wt"),
                                blog=Path("/h/blog"), claude="claude")
        self.b = daily.cmd_b(self.cfg, Path("/h/wt"))
        self.a = daily.cmd_a(self.cfg)

    @staticmethod
    def opt(cmd, name):
        i = cmd.index(name) + 1
        vals = []
        while i < len(cmd) and not cmd[i].startswith("--"):
            vals.append(cmd[i])
            i += 1
        return vals

    def test_common_no_settings_no_bypass(self):
        for cmd in (self.a, self.b):
            self.assertEqual(self.opt(cmd, "--setting-sources"), [""])
            self.assertIn("--strict-mcp-config", cmd)
            self.assertIn("--restricted", cmd)
            self.assertEqual(self.opt(cmd, "--permission-mode"), ["dontAsk"])
            self.assertEqual(self.opt(cmd, "--model"), ["sonnet"])
            self.assertFalse([x for x in cmd if "dangerously" in x or x == "bypassPermissions"])
            self.assertNotIn("--settings", cmd)
            self.assertNotIn("--add-dir", cmd)

    def test_no_bash_anywhere(self):
        for cmd in (self.a, self.b):
            tools = self.opt(cmd, "--tools")[0].split(",")
            self.assertNotIn("Bash", tools)
            self.assertFalse([t for t in self.opt(cmd, "--allowedTools") if t.startswith("Bash")])
            self.assertIn("Bash", self.opt(cmd, "--disallowedTools"))

    def test_stage_a_web_only(self):
        self.assertEqual(self.opt(self.a, "--tools"), ["WebSearch,WebFetch"])
        self.assertEqual(sorted(self.opt(self.a, "--allowedTools")), ["WebFetch", "WebSearch"])
        for t in ("Read", "Edit", "Write", "Glob", "Grep"):
            self.assertIn(t, self.opt(self.a, "--disallowedTools"))

    def test_stage_b_no_web_scoped_to_worktree(self):
        self.assertEqual(self.opt(self.b, "--tools"), ["Read,Edit,Write,Glob,Grep"])
        allowed = self.opt(self.b, "--allowedTools")
        self.assertIn("Read(//h/wt/**)", allowed)
        self.assertIn("Edit(//h/wt/**)", allowed)
        self.assertFalse([t for t in allowed if t.startswith(("Web", "Write"))])
        self.assertFalse([t for t in allowed if t in ("Read", "Edit")])  # 沒有不限路徑的讀寫
        deny = self.opt(self.b, "--disallowedTools")
        self.assertIn("WebSearch", deny)
        self.assertIn("WebFetch", deny)
        for f in ("scripts/hooks/**", "scripts/ci/**", ".claude/**", ".git*", ".git/**", ".github/**",
                  "setup/**", ".leak-denylist"):
            self.assertIn(f"Edit(//h/wt/{f})", deny)
        home = daily.real(Path.home())
        for p in (home / ".claude", home / ".ssh", Path("/h/.claude/ai-radar"), Path("/h/r"), Path("/h/blog")):
            self.assertIn(f"Read(/{p}/**)", deny)
            self.assertIn(f"Edit(/{p}/**)", deny)

    def test_draft_path_allowlist(self):
        ok = ["plugins/p/README.md", "plugins/p/中文.md", "docs/x.md", ".claude-plugin/marketplace.json", "README.md"]
        bad = [f"{CI}validate.py", "scripts/hooks/pre-commit", ".claude/settings.json", ".github/w.yml",
               "setup/install.sh", "notes.md", ".gitignore", "plugins/p/x.bin", ".leak-denylist"]
        self.assertTrue(all(daily.path_allowed(p) for p in ok))
        self.assertFalse([p for p in bad if daily.path_allowed(p)])

    def test_profile_tools_filters_denylist(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "wp.md"
            p.write_text(PROFILE, encoding="utf-8")
            import re
            tools = daily.profile_tools(p, [re.compile("secretco", re.I)])
            self.assertEqual(tools["plugins"], ["superpowers"])
            self.assertEqual(tools["mcp"], ["linear"])
            self.assertEqual(tools["cli"], ["git", "gh"])
            no_list = daily.profile_tools(p, None)
            self.assertEqual((no_list["plugins"], no_list["mcp"]), ([], []))

    def test_plist(self):
        data = plistlib.loads(daily.make_plist("/usr/bin/python3", "/usr/bin:/bin", "/tmp/x.log",
                                               {"RADAR_REPO": "/r"}).encode("utf-8"))
        self.assertEqual(data["Label"], daily.LABEL)
        self.assertEqual(data["ProgramArguments"][-1], "run")
        self.assertEqual(sorted(d["Weekday"] for d in data["StartCalendarInterval"]), [1, 2, 3, 4, 5])
        self.assertTrue(all(d["Hour"] == 9 and d["Minute"] == 0 for d in data["StartCalendarInterval"]))
        self.assertEqual(data["EnvironmentVariables"]["RADAR_REPO"], "/r")


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.marker = self.tmp / "HOOK-RAN"
        self.repo = self.tmp / "repo"
        make_repo(self.repo, self.marker)
        self.out = self.tmp / "out"
        self.out.mkdir()
        (self.out / "adoption-backlog.md").write_text(BACKLOG, encoding="utf-8")
        (self.out / "work-profile.md").write_text(PROFILE, encoding="utf-8")  # 夠新，不會去掃真 transcript
        fake = self.tmp / "fake-claude"
        fake.write_text(FAKE_CLAUDE, encoding="utf-8")
        fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
        self.wt = self.tmp / "wt"
        self.env = {**GIT_ENV, "AI_RADAR_OUT": str(self.out), "RADAR_REPO": str(self.repo),
                    "RADAR_WORKTREE": str(self.wt), "RADAR_BLOG": str(self.tmp / "no-blog"),
                    "RADAR_CLAUDE": str(fake), "FAKE_OUT": str(self.out)}

    def tearDown(self):
        subprocess.run(["git", "-C", str(self.repo), "worktree", "remove", "--force", str(self.wt)],
                       capture_output=True)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def cfg(self, **kw):
        base = dict(out=self.out, repo=self.repo, worktree=self.wt, blog=self.tmp / "no-blog", claude="x")
        return daily.Config(**{**base, **kw})


class WorktreeIdentityTest(Fixture):
    def test_valid_worktree(self):
        git(self.repo, "worktree", "add", "-q", "--detach", str(self.wt), "main")
        self.assertEqual(daily.verify_worktree(self.cfg()), daily.real(self.wt))

    def test_rejects_main_checkout_symlink_subdir_and_other_repo(self):
        link = self.tmp / "link"
        link.symlink_to(self.repo)
        other = self.tmp / "other"
        make_repo(other, self.tmp / "m2")
        for wt in (self.repo, link, self.repo / "plugins", other):
            with self.subTest(wt=wt.name), self.assertRaises(daily.Fail):
                daily.verify_worktree(self.cfg(worktree=wt))

    def test_rejects_unregistered_worktree_of_other_repo(self):
        other = self.tmp / "other"
        make_repo(other, self.tmp / "m2")
        git(other, "worktree", "add", "-q", "--detach", str(self.wt), "main")
        with self.assertRaises(daily.Fail):
            daily.verify_worktree(self.cfg())
        git(other, "worktree", "remove", "--force", str(self.wt))

    def test_validate_runs_trusted_main_copy(self):
        git(self.repo, "worktree", "add", "-q", "--detach", str(self.wt), "main")
        (self.wt / "scripts" / "ci" / "validate.py").write_text("print('TAMPERED')\n", encoding="utf-8")
        (self.wt / "scripts" / "ci" / "json.py").write_text("print('PLANTED')\n", encoding="utf-8")
        v = daily.run_validate(self.cfg(), daily.real(self.wt))
        self.assertEqual(v.returncode, 0, v.stderr)
        self.assertIn('validate ok "wt"', v.stdout)  # ROOT 指向 worktree
        self.assertNotIn("TAMPERED", v.stdout + v.stderr)
        self.assertNotIn("PLANTED", v.stdout + v.stderr)


class RunTest(Fixture):
    def run_daily(self, mode="draft", *extra):
        return subprocess.run([sys.executable, str(SCRIPT), "run", "--no-notify", "--no-pull", "--today", TODAY,
                               *extra], capture_output=True, text=True, encoding="utf-8",
                              env={**self.env, "FAKE_MODE": mode})

    def report(self):
        return (self.out / f"{TODAY}-daily.md").read_text(encoding="utf-8")

    def done(self):
        return (self.out / "logs" / f"{TODAY}-daily.done").exists()

    def branches(self):
        return git(self.repo, "branch", "--list", "radar/*", "--format=%(refname:short)").split()

    def assert_clean_detached(self):
        self.assertEqual(git(self.wt, "status", "--porcelain", "--untracked-files=all", "--ignored"), "")
        self.assertEqual(git(self.wt, "rev-parse", "HEAD"), git(self.repo, "rev-parse", "main"))

    def test_draft_flow(self):
        r = self.run_daily()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        branch = f"radar/{TODAY}-3"
        self.assertEqual(self.branches(), [branch])
        self.assertEqual(git(self.repo, "log", "-1", "--format=%s", branch), "radar: #3 高分 A")
        self.assertEqual(git(self.repo, "diff", "--name-only", f"main...{branch}"), "plugins/p/README.md")
        self.assertFalse(self.marker.exists(), "commit 不能跑 repo 的 hook")
        self.assertIn("新草稿", r.stdout)
        text = self.report()
        self.assertIn("validate.py：通過", text)
        self.assertIn("**改了什麼**：README", text)
        self.assertNotIn("RESULT:", text)
        self.assertIn("| claude-code | v9 |", text)
        self.assertIn("被權限擋下的工具呼叫：2 次", text)
        self.assert_clean_detached()
        self.assertIn(f"每日草稿 {branch}", (self.out / "adoption-backlog.md").read_text(encoding="utf-8"))
        self.assertTrue(self.done())
        # 階段 B 的 prompt 只有挑中的那一項；階段 A 的 prompt 沒有 backlog、沒有黑名單命中的名稱
        pb = (self.out / "prompt-b.txt").read_text(encoding="utf-8")
        self.assertIn("高分 A", pb)
        self.assertNotIn("高分 B", pb)
        pa = (self.out / "prompt-a.txt").read_text(encoding="utf-8")
        self.assertNotIn("高分", pa)
        self.assertNotIn("secretco", pa)
        self.assertNotIn(str(self.out), pa)
        self.assertIn('"linear"', pa)
        # 同一天再跑不重做
        again = self.run_daily()
        self.assertIn("今天已跑完", again.stdout)

    def test_chinese_filename_committed(self):
        r = self.run_daily("zh")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        files = git(self.repo, "-c", "core.quotePath=false", "diff", "--name-only", f"main...radar/{TODAY}-3")
        self.assertEqual(files, "plugins/p/中文檔名.md")

    def test_skip_then_draft_marks_backlog(self):
        r = self.run_daily("skip-dirty,draft")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.branches(), [f"radar/{TODAY}-4"])
        backlog = (self.out / "adoption-backlog.md").read_text(encoding="utf-8")
        self.assertIn(f"每日版略過 {TODAY}：改到一半放棄", backlog)
        self.assertIn("#3：改到一半放棄", self.report())
        self.assertFalse((self.wt / "plugins" / "p" / "left.md").exists())

    def test_all_skipped_no_notify(self):
        r = self.run_daily("skip")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(len((self.out / "calls-b").read_text().splitlines()), daily.MAX_TRIES)
        self.assertNotIn("[notify]", r.stdout)
        self.assertIn("今日沒有草稿", self.report())
        self.assertTrue(self.done())

    def assert_failed_and_discarded(self, r, needle):
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("執行失敗", r.stdout)
        self.assertIn(needle, self.report())
        self.assertIn("❌", self.report())
        self.assertEqual(self.branches(), [])
        self.assertFalse(self.done())
        self.assert_clean_detached()

    def test_forbidden_path_discarded(self):
        self.assert_failed_and_discarded(self.run_daily("forbidden"), f"{CI}evil.py")

    def test_path_outside_allowlist_discarded(self):
        self.assert_failed_and_discarded(self.run_daily("outside"), "notes.md")

    def test_new_ignored_file_discarded(self):
        self.assert_failed_and_discarded(self.run_daily("ignored"), ".leak-denylist")

    def test_validate_failure_is_failure(self):
        r = self.run_daily("bad")
        self.assert_failed_and_discarded(r, "沒通過 validate.py")
        self.assertIn("validate.py：失敗", self.report())

    def test_unformatted_result_is_failure(self):
        self.assert_failed_and_discarded(self.run_daily("noformat"), "沒有照格式")

    def test_claude_error_is_failure(self):
        self.assert_failed_and_discarded(self.run_daily("fail"), "claude 回報錯誤")

    def test_failed_report_kept_and_rerun_allowed(self):
        self.run_daily("forbidden")
        r = self.run_daily("draft")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        kept = list(self.out.glob(f"{TODAY}-daily.failed-*.md"))
        self.assertEqual(len(kept), 1)
        self.assertIn(f"{CI}evil.py", kept[0].read_text(encoding="utf-8"))
        self.assertTrue(self.done())

    def test_dirty_worktree_blocks(self):
        git(self.repo, "worktree", "add", "-q", "--detach", str(self.wt), "main")
        (self.wt / "manual.md").write_text("x", encoding="utf-8")
        r = self.run_daily()
        self.assertEqual(r.returncode, 1)
        self.assertIn("未 commit", self.report())
        self.assertTrue((self.wt / "manual.md").exists())  # 人留下的改動不丟

    def test_rejects_main_checkout_as_worktree(self):
        r = subprocess.run([sys.executable, str(SCRIPT), "run", "--no-notify", "--no-pull", "--today", TODAY],
                           capture_output=True, text=True, encoding="utf-8",
                           env={**self.env, "RADAR_WORKTREE": str(self.repo)})
        self.assertEqual(r.returncode, 1)
        self.assertEqual(git(self.repo, "rev-parse", "--abbrev-ref", "HEAD"), "main")  # 主 checkout 沒被切走
        self.assertFalse((self.out / "calls-b").exists())

    def test_drafts_full(self):
        for i in range(3):
            b = f"radar/2026-01-0{i + 1}-{90 + i}"
            git(self.repo, "switch", "-q", "-c", b)
            (self.repo / f"f{i}").write_text("x", encoding="utf-8")
            git(self.repo, "add", f"f{i}")
            git(self.repo, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", f"f{i}")
            git(self.repo, "switch", "-q", "main")
        r = self.run_daily()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("待審草稿已滿 3 個", self.report())
        self.assertIn("已滿", r.stdout)
        self.assertFalse((self.out / "calls-b").exists())
        self.assertTrue((self.out / "calls-a").exists())

    def test_weekend_skipped(self):
        r = subprocess.run([sys.executable, str(SCRIPT), "run", "--no-notify", "--today", "2026-11-07"],
                           capture_output=True, text=True, encoding="utf-8", env=self.env)
        self.assertEqual(r.returncode, 0)
        self.assertIn("週末", r.stdout)
        self.assertFalse((self.out / "calls-a").exists())

    def test_lock_blocks_concurrent_run(self):
        (self.out / "logs").mkdir()
        with (self.out / "logs" / "daily.lock").open("w") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            r = self.run_daily()
        self.assertEqual(r.returncode, 0)
        self.assertIn("另一個 daily.py 正在執行", r.stdout)
        self.assertFalse((self.out / "calls-a").exists())
        self.assertFalse(self.wt.exists())


@unittest.skipUnless(sys.platform == "darwin", "launchd 只在 macOS")
class InstallTest(unittest.TestCase):
    def test_failed_render_keeps_old_plist(self):
        with tempfile.TemporaryDirectory() as home:
            dest = Path(home) / "Library" / "LaunchAgents" / f"{daily.LABEL}.plist"
            dest.parent.mkdir(parents=True)
            dest.write_text("OLD", encoding="utf-8")
            r = subprocess.run(["bash", str(SCRIPT.with_name("install-daily.sh"))], capture_output=True, text=True,
                               env={**os.environ, "HOME": home, "RADAR_CLAUDE": "no-such-claude-cli"})
            self.assertNotEqual(r.returncode, 0)
            self.assertEqual(dest.read_text(encoding="utf-8"), "OLD")
            self.assertEqual(list(dest.parent.iterdir()), [dest])  # 暫存檔也清掉


if __name__ == "__main__":
    unittest.main()
