"""work_profile.py 測試：用假 transcript fixture，不讀真資料。"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("work_profile.py")
sys.path.insert(0, str(SCRIPT.parent))
import work_profile  # noqa: E402

NOW = "2026-11-09T09:00:00Z"


def tool(tid, name, inp, ts="2026-11-08T10:00:00Z", session="s1"):
    return {"type": "assistant", "timestamp": ts, "sessionId": session, "uuid": "u-" + tid,
            "message": {"content": [{"type": "tool_use", "id": tid, "name": name, "input": inp}]}}


def user(uid, text, ts="2026-11-08T10:00:00Z", session="s1"):
    return {"type": "user", "timestamp": ts, "sessionId": session, "uuid": uid,
            "message": {"content": text}}


class CliNamesTest(unittest.TestCase):
    def names(self, cmd):
        return list(work_profile.cli_names(cmd))

    def test_pipes_env_and_builtins(self):
        self.assertEqual(self.names("FOO=1 git status && cd x; ls | grep a 2>&1 | head"),
                         ["git", "ls", "grep", "head"])

    def test_heredoc_body_ignored(self):
        cmd = "python3 - <<'EOF'\nimport json\nrm -rf /\nEOF\nwc -l x"
        self.assertEqual(self.names(cmd), ["python3", "wc"])

    def test_paths(self):
        self.assertEqual(self.names("/usr/bin/git log; ./scripts/run.sh; sudo dotnet build"),
                         ["git", "dotnet"])


class ScanTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        proj = self.tmp / "projects" / "-example-proj"
        (proj / "s1" / "subagents").mkdir(parents=True)
        records = [
            tool("t1", "Skill", {"skill": "demo:plan"}),
            tool("t2", "Bash", {"command": "git status && git diff | grep x"}),
            tool("t3", "Read", {"file_path": "/repo/a/Main.PY"}),
            tool("t4", "Edit", {"file_path": "/repo/README.md"}),
            tool("t5", "mcp__fake-server__do_it", {}),
            user("u1", "<command-name>/demo:review</command-name>"),
            tool("old", "Bash", {"command": "svn up"}, ts="2026-09-01T00:00:00Z"),  # 超出 30 天
        ]
        lines = [json.dumps(r) for r in records] + ["{壞掉的一行", "[]"]
        (proj / "s1.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
        # resume 複製的歷史（同 tool_use id）不重複計；subagent transcript 也要掃
        sub = [tool("t2", "Bash", {"command": "git status"}, session="s1"),
               tool("t9", "Write", {"file_path": "/repo/b.md"}, session="s2")]
        (proj / "s1" / "subagents" / "agent-x.jsonl").write_text(
            "\n".join(json.dumps(r) for r in sub) + "\n", encoding="utf-8")
        self.out = self.tmp / "out" / "work-profile.md"

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_counts_and_output(self):
        r = subprocess.run([sys.executable, str(SCRIPT), "--projects", str(self.tmp / "projects"),
                            "--out", str(self.out), "--now", NOW],
                           capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)
        text = self.out.read_text(encoding="utf-8")
        self.assertIn("2 個 session", text)
        self.assertIn("| `demo:plan` | 1 |", text)
        self.assertIn("| `demo:review` | 1 |", text)
        self.assertIn("| `git` | 1 |", text)   # 同一條指令兩次 git 只算一次；重複的 t2 不再計
        self.assertIn("| `grep` | 1 |", text)
        self.assertIn("| `fake-server` | 1 |", text)
        self.assertIn("| `.md` | 2 |", text)
        self.assertIn("| `.py` | 1 |", text)
        self.assertNotIn("svn", text)

    def test_empty_projects(self):
        empty = self.tmp / "empty"
        empty.mkdir()
        work_profile.main(["--projects", str(empty), "--out", str(self.out), "--now", NOW])
        self.assertIn("0 個 session", self.out.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
