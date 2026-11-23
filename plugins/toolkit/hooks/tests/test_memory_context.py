"""memory-context 測試：非 Claude 的 CLI 開場唯讀注入 Claude auto-memory 索引；Claude 自己、找不到索引時靜默。"""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / "memory-context.py"


class MemoryContext(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp(prefix="mem"))
        self.proj = self.home / "work" / "my-proj"
        (self.proj / "sub").mkdir(parents=True)
        slug = re.sub(r"[^A-Za-z0-9]", "-", str(self.proj.resolve()))
        self.mem = self.home / ".claude" / "projects" / slug / "memory"
        self.mem.mkdir(parents=True)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.home, ignore_errors=True)

    def run_hook(self, payload):
        env = dict(os.environ, HOME=str(self.home), USERPROFILE=str(self.home))
        return subprocess.run([sys.executable, str(HOOK)], env=env, input=json.dumps(payload).encode("utf-8"),
                              capture_output=True, timeout=10)

    def context(self, p):
        self.assertEqual(p.returncode, 0, p.stderr)
        return json.loads(p.stdout.decode("utf-8"))["hookSpecificOutput"]["additionalContext"]

    def test_injects_index_from_subdirectory(self):
        (self.mem / "MEMORY.md").write_text("# Memory Index\n- [甲](a.md) — 乙\n", encoding="utf-8")
        ctx = self.context(self.run_hook({"cwd": str(self.proj / "sub"), "transcript_path": str(self.home / ".codex" / "s.jsonl")}))
        self.assertIn("- [甲](a.md) — 乙", ctx)
        self.assertIn("唯讀", ctx)
        self.assertIn("不要新增、修改或刪除", ctx)

    def test_agy_uses_workspace_paths_and_inject_steps(self):
        (self.mem / "MEMORY.md").write_text("- [甲](a.md)\n", encoding="utf-8")
        p = self.run_hook({"conversationId": "c1", "workspacePaths": [str(self.proj)],
                           "transcriptPath": str(self.home / ".gemini" / "t.jsonl")})
        self.assertEqual(p.returncode, 0, p.stderr)
        steps = json.loads(p.stdout.decode("utf-8"))["injectSteps"]
        self.assertIn("- [甲](a.md)", steps[0]["systemMessage"]["systemMessage"])

    def test_truncates_to_200_lines(self):
        (self.mem / "MEMORY.md").write_text("".join(f"line{i}\n" for i in range(300)), encoding="utf-8")
        ctx = self.context(self.run_hook({"cwd": str(self.proj)}))
        self.assertIn("line199", ctx)
        self.assertNotIn("line200", ctx)

    def test_silent_under_claude(self):
        (self.mem / "MEMORY.md").write_text("- x\n", encoding="utf-8")
        p = self.run_hook({"cwd": str(self.proj), "transcript_path": str(self.home / ".claude" / "projects" / "a" / "b.jsonl")})
        self.assertEqual((p.returncode, p.stdout), (0, b""))

    def test_silent_without_index_or_bad_input(self):
        p = self.run_hook({"cwd": str(self.proj)})
        self.assertEqual((p.returncode, p.stdout), (0, b""))
        env = dict(os.environ, HOME=str(self.home), USERPROFILE=str(self.home))
        p = subprocess.run([sys.executable, str(HOOK)], env=env, input=b"not json", capture_output=True, timeout=10)
        self.assertEqual((p.returncode, p.stdout), (0, b""))


if __name__ == "__main__":
    unittest.main()
