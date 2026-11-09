"""daily.py 測試：假 backlog、暫存 git repo、假 claude 腳本，不呼叫模型、不讀真資料。"""
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
from datetime import date
from pathlib import Path

SCRIPT = Path(__file__).with_name("daily.py")
sys.path.insert(0, str(SCRIPT.parent))
import daily  # noqa: E402

GIT_ENV = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com"}
TODAY = date.today().isoformat()

BACKLOG = textwrap.dedent("""\
    # 採納待辦

    | # | 來源 | 摘要 | 影響×可行性×契合度 | 狀態 | 建議交棒 | 決策備註 |
    |---|------|------|------|------|------|------|
    | 1 | a | 已駁回 | 3×3×3=27 | 駁回 | - | - |
    | 2 | b | 低分 | 1×3×2=6（原 12） | 待評估 | x | - |
    | 3 | c | 高分 A | 2×3×3=18 | 待評估 | x | - |
    | 4 | d | 高分 B | 2×3×3=18 | 採納 | x | - |
    | 5 | e | 每日版略過過 | 3×3×3=27 | 待評估 | x | 每日版略過 2026-11-01：要實測 |
    | 6 | f | 沒分數 | - | 待評估 | x | - |
    | 7 | g | 已完成 | 3×3×3=27 | 已完成 | x | - |
    | 8 | h | 已有 branch | 3×3×2=18 | 進行中 | x | - |
    | 9 | i | 中分 | 2×2×3=12 | 待評估 | x | - |
    | 10 | j | 欄位壞掉 | 3×3×3=27 | 駁回 |
    """)


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True,
                          text=True, env=GIT_ENV).stdout.strip()


def make_repo(path):
    path.mkdir(parents=True)
    git(path, "init", "-q", "-b", "main")
    (path / "scripts" / "ci").mkdir(parents=True)
    (path / "scripts" / "ci" / "validate.py").write_text("print('validate ok')\n", encoding="utf-8")
    (path / ".gitignore").write_text("", encoding="utf-8")
    git(path, "add", str(Path("scripts", "ci", "validate.py")), ".gitignore")
    git(path, "commit", "-q", "-m", "init")


# 假 claude：從 prompt 的 JSON 讀背景，照 daily.md 的流程開 branch、commit、寫報告
FAKE_CLAUDE = textwrap.dedent("""\
    #!/usr/bin/env python3
    import json, os, re, subprocess, sys
    args = sys.argv[1:]
    prompt = args[args.index("-p") + 1]
    ctx = json.loads(re.search(r"```json\\n(.*?)\\n```", prompt, re.S).group(1))
    open(os.path.join(ctx["out_dir"], "argv.json"), "w", encoding="utf-8").write(json.dumps(args))
    mode = os.environ.get("FAKE_MODE", "draft")
    if mode == "fail":
        sys.exit(3)
    lines = ["# ai-radar 每日 — " + ctx["date"], "drafts_full=" + str(ctx["drafts_full"])]
    if mode == "draft" and not ctx["drafts_full"]:
        c = ctx["candidates"][0]
        b = "radar/%s-%d" % (ctx["date"], c["num"])
        subprocess.run(["git", "switch", "-q", "-c", b], check=True)
        open("draft.md", "w", encoding="utf-8").write("draft\\n")
        subprocess.run(["git", "add", "draft.md"], check=True)
        subprocess.run(["git", "commit", "-q", "-m", "draft"], check=True)
        lines.append("branch=" + b)
    if mode == "dirty":
        open("left.md", "w", encoding="utf-8").write("x\\n")
    open(ctx["report"], "w", encoding="utf-8").write("\\n".join(lines) + "\\n")
    """)


class BacklogTest(unittest.TestCase):
    def test_candidates_order_and_filters(self):
        got = [c.num for c in daily.candidates(BACKLOG, taken={8})]
        self.assertEqual(got, [3, 4, 9, 2])

    def test_limit(self):
        self.assertEqual(len(daily.candidates(BACKLOG, set(), limit=2)), 2)

    def test_branch_numbers(self):
        self.assertEqual(daily.branch_numbers(["radar/2026-11-09-8", "radar/x", "radar/2026-11-10-12"]), {8, 12})


class ConfigTest(unittest.TestCase):
    def setUp(self):
        self.cfg = daily.Config(out=Path("/h/.claude/ai-radar"), repo=Path("/h/r"), worktree=Path("/h/wt"),
                                blog=Path("/nonexistent-blog"), claude="claude")

    def test_allowed_tools_scoped_and_no_push(self):
        tools = daily.allowed_tools(self.cfg)
        self.assertIn("Edit(//h/.claude/ai-radar/**)", tools)
        self.assertIn("Edit(//h/wt/**)", tools)
        self.assertFalse([t for t in tools if "push" in t or t == "Bash" or t.startswith("Bash(*")])
        cmd = daily.claude_cmd(self.cfg, "hi")
        self.assertIn("dontAsk", cmd)
        self.assertEqual(cmd[cmd.index("--setting-sources") + 1], "project,local")
        self.assertNotIn("--dangerously-skip-permissions", cmd)
        self.assertEqual(cmd[cmd.index("--model") + 1], "sonnet")
        self.assertEqual(cmd[cmd.index("--disallowedTools") + 1], "Bash(git push:*)")

    def test_plist(self):
        data = plistlib.loads(daily.make_plist("/usr/bin/python3", "/usr/bin:/bin", "/tmp/x.log",
                                               {"RADAR_REPO": "/r"}).encode("utf-8"))
        self.assertEqual(data["Label"], daily.LABEL)
        self.assertEqual(data["ProgramArguments"][-1], "run")
        self.assertEqual(sorted(d["Weekday"] for d in data["StartCalendarInterval"]), [1, 2, 3, 4, 5])
        self.assertTrue(all(d["Hour"] == 9 and d["Minute"] == 0 for d in data["StartCalendarInterval"]))
        self.assertEqual(data["EnvironmentVariables"]["RADAR_REPO"], "/r")


class RunTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.repo = self.tmp / "repo"
        make_repo(self.repo)
        self.out = self.tmp / "out"
        self.out.mkdir()
        (self.out / "adoption-backlog.md").write_text(BACKLOG, encoding="utf-8")
        (self.out / "work-profile.md").write_text("# 工作模式\n", encoding="utf-8")  # 夠新，不會去掃真 transcript
        fake = self.tmp / "fake-claude"
        fake.write_text(FAKE_CLAUDE, encoding="utf-8")
        fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
        self.wt = self.tmp / "wt"
        self.env = {**GIT_ENV, "AI_RADAR_OUT": str(self.out), "RADAR_REPO": str(self.repo),
                    "RADAR_WORKTREE": str(self.wt), "RADAR_BLOG": str(self.tmp / "no-blog"),
                    "RADAR_CLAUDE": str(fake)}

    def tearDown(self):
        subprocess.run(["git", "-C", str(self.repo), "worktree", "remove", "--force", str(self.wt)],
                       capture_output=True)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_daily(self, mode="draft"):
        return subprocess.run([sys.executable, str(SCRIPT), "run", "--no-notify", "--no-pull"],
                              capture_output=True, text=True, encoding="utf-8",
                              env={**self.env, "FAKE_MODE": mode})

    def report(self):
        return (self.out / f"{TODAY}-daily.md").read_text(encoding="utf-8")

    def test_draft_flow(self):
        r = self.run_daily()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        branch = f"radar/{TODAY}-3"
        self.assertEqual(git(self.repo, "branch", "--list", "radar/*", "--format=%(refname:short)"), branch)
        self.assertIn("新草稿", r.stdout)
        text = self.report()
        self.assertIn("validate.py：通過", text)
        self.assertIn("validate ok", text)
        # 收尾切回 detached main，主 checkout 才能 switch 到草稿 branch
        self.assertEqual(git(self.wt, "rev-parse", "HEAD"), git(self.repo, "rev-parse", "main"))
        argv = json.loads((self.out / "argv.json").read_text(encoding="utf-8"))
        self.assertIn("Bash(git push:*)", argv)
        # 同一天再跑不重做
        again = self.run_daily()
        self.assertIn("今天已跑過", again.stdout)

    def test_drafts_full(self):
        for i in range(3):
            git(self.repo, "branch", f"radar/2026-01-0{i + 1}-{90 + i}")
            git(self.repo, "switch", "-q", f"radar/2026-01-0{i + 1}-{90 + i}")
            (self.repo / f"f{i}").write_text("x", encoding="utf-8")
            git(self.repo, "add", f"f{i}")
            git(self.repo, "commit", "-q", "-m", f"f{i}")
            git(self.repo, "switch", "-q", "main")
        r = self.run_daily()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("drafts_full=True", self.report())
        self.assertIn("已滿", r.stdout)

    def test_claude_failure_notifies_and_leaves_no_report(self):
        r = self.run_daily("fail")
        self.assertEqual(r.returncode, 1)
        self.assertIn("執行失敗", r.stdout)
        self.assertFalse((self.out / f"{TODAY}-daily.md").exists())
        self.assertIn("FAIL", (self.out / "logs" / f"{TODAY}-daily.log").read_text(encoding="utf-8"))

    def test_dirty_worktree_reported_not_discarded(self):
        r = self.run_daily("dirty")
        self.assertEqual(r.returncode, 1)
        self.assertIn("left.md", self.report())
        self.assertTrue((self.wt / "left.md").exists())
        # 下一次跑會先擋下，不在髒的 worktree 上開草稿
        (self.out / f"{TODAY}-daily.md").unlink()
        r2 = self.run_daily()
        self.assertEqual(r2.returncode, 1)
        self.assertIn("未 commit", r2.stdout)


if __name__ == "__main__":
    unittest.main()
