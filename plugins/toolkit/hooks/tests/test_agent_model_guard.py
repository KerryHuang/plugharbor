"""agent-model-guard 與 hooks.json 的 fail-open 測試。

agent-model-guard：general-purpose 沒指定 model 時補 sonnet，其餘一律不動；壞輸入 fail-open。
fail-open：hooks.json 裡每條 python hook 指令，腳本檔不存在時都要 exit 0（不能擋掉 Bash／Write／Edit）。
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parents[1]
HOOK = HOOKS_DIR / "agent-model-guard.py"


def run(payload):
    p = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(payload), capture_output=True, text=True)
    return p.returncode, p.stdout


def python_hook_commands():
    data = json.loads((HOOKS_DIR / "hooks.json").read_text(encoding="utf-8"))
    cmds = [h["command"] for groups in data["hooks"].values() for g in groups for h in g["hooks"]]
    return [c for c in cmds if ".py" in c]


class AgentModelGuard(unittest.TestCase):
    def test_general_purpose_without_model_gets_sonnet(self):
        rc, out = run({"tool_name": "Agent", "tool_input": {"subagent_type": "general-purpose", "prompt": "x"}})
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out)["hookSpecificOutput"]["updatedInput"]["model"], "sonnet")

    def test_explicit_model_untouched(self):
        rc, out = run({"tool_name": "Agent", "tool_input": {"subagent_type": "general-purpose", "model": "opus"}})
        self.assertEqual((rc, out), (0, ""))

    def test_named_agent_untouched(self):
        rc, out = run({"tool_name": "Agent", "tool_input": {"subagent_type": "lifecycle:qa-runner-ui"}})
        self.assertEqual((rc, out), (0, ""))

    def test_fork_untouched(self):
        rc, out = run({"tool_name": "Agent", "tool_input": {"subagent_type": "fork"}})
        self.assertEqual((rc, out), (0, ""))

    def test_bad_stdin_fail_open(self):
        p = subprocess.run([sys.executable, str(HOOK)], input="not json", capture_output=True, text=True)
        self.assertEqual((p.returncode, p.stdout), (0, ""))


class HooksFailOpen(unittest.TestCase):
    def test_every_python_hook_is_covered(self):
        self.assertEqual(len(python_hook_commands()), 11)

    def test_commands_survive_powershell_quoting(self):
        # Windows 的 Codex 用 powershell -Command 跑 hook，內層雙引號會被吃掉；
        # 指令只能是「sh "<包裝檔>" <腳本名>」，不得有 sh -c 或第二層引號
        pattern = re.compile(r'^sh "\$\{CLAUDE_PLUGIN_ROOT\}/hooks/run-py\.sh" [\w.-]+\.py$')
        for cmd in python_hook_commands():
            with self.subTest(cmd=cmd):
                self.assertRegex(cmd, pattern)

    def test_missing_script_exits_zero(self):
        # CLAUDE_PLUGIN_ROOT 底下只有包裝檔、腳本缺檔 → 必須 exit 0 且無輸出
        with tempfile.TemporaryDirectory() as root:
            (Path(root) / "hooks").mkdir()
            shutil.copy(HOOKS_DIR / "run-py.sh", Path(root) / "hooks" / "run-py.sh")
            for cmd in python_hook_commands():
                with self.subTest(cmd=cmd):
                    resolved = cmd.replace("${CLAUDE_PLUGIN_ROOT}", root)
                    p = subprocess.run(["sh", "-c", resolved], input="{}", capture_output=True, text=True)
                    self.assertEqual((p.returncode, p.stdout), (0, ""), p.stderr)

    def test_existing_script_still_runs(self):
        # 對照組：腳本存在時照常 exec（壞輸入由腳本自己 fail-open，仍是 0）
        cmd = next(c for c in python_hook_commands() if "agent-model-guard.py" in c)
        resolved = cmd.replace("${CLAUDE_PLUGIN_ROOT}", str(HOOKS_DIR.parent))
        p = subprocess.run(["sh", "-c", resolved], input=json.dumps(
            {"tool_name": "Agent", "tool_input": {"subagent_type": "general-purpose", "prompt": "x"}}),
            capture_output=True, text=True)
        self.assertEqual(p.returncode, 0)
        self.assertIn("sonnet", p.stdout)


if __name__ == "__main__":
    unittest.main()
