"""Windows 的 Codex 只跑 hooks.json 的 commandWindows（PowerShell），PATH 上通常沒有 sh、bash 是 WSL。

每一條 hook 的 commandWindows 都由 command 套同一個樣板：自己找 Git for Windows 的 sh.exe／bash.exe，
找不到就 exit 0（fail-open，同 run-py.sh）。做法照 sdlc plugin 已在 Windows 驗證過的 codex-hooks.json。
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parents[1]
REPO = HOOKS_DIR.parents[2]


def hook_entries():
    data = json.loads((HOOKS_DIR / "hooks.json").read_text(encoding="utf-8"))
    return [h for groups in data["hooks"].values() for g in groups for h in g["hooks"]]


def windows_command(command):
    """hooks.json 的 commandWindows 樣板（相容 Windows PowerShell 5.1）。

    先把 stdin／stdout 設成 UTF-8（預設 cp950 會把中文轉壞），讀完 stdin；依序找 Git for Windows 的
    sh.exe（bash 腳本找 bash.exe）：git 所在目錄上兩層的 bin、ProgramFiles、LOCALAPPDATA。
    找不到一律 exit 0：guard 類在 Codex 另有 tool-policy.mjs 擋 git 紅線，這裡擋住會讓每個 Bash 都不能跑。
    """
    shell, path, args = command.split('"')
    exe = {"sh ": "sh.exe", "bash ": "bash.exe"}[shell]
    script = path.rsplit("/", 1)[1]
    return (
        "$u=New-Object Text.UTF8Encoding $false; [Console]::InputEncoding=$u; [Console]::OutputEncoding=$u; $OutputEncoding=$u; "
        "$in=[Console]::In.ReadToEnd(); "
        "$sh=$null; foreach ($c in @($(try { Join-Path (Split-Path (Split-Path (Get-Command git -ErrorAction Stop).Source)) "
        f"'bin\\{exe}' }} catch {{ '' }}), \"$env:ProgramFiles\\Git\\bin\\{exe}\", \"$env:LOCALAPPDATA\\Programs\\Git\\bin\\{exe}\")) "
        "{ if ($c -and (Test-Path $c)) { $sh=$c; break } }; "
        "if (-not $sh) { exit 0 }; "
        f'$in | & $sh "$env:CLAUDE_PLUGIN_ROOT/hooks/{script}"{args}; exit $LASTEXITCODE'
    )


class WindowsCommand(unittest.TestCase):
    def test_every_hook_has_windows_command(self):
        for h in hook_entries():
            with self.subTest(cmd=h["command"]):
                self.assertEqual(h.get("commandWindows"), windows_command(h["command"]))

    def test_commands_single_quote_level(self):
        # 樣板靠 split('"') 拆出腳本與參數：command 只能有一層雙引號
        for h in hook_entries():
            with self.subTest(cmd=h["command"]):
                self.assertRegex(h["command"], r'^(sh|bash) "\$\{CLAUDE_PLUGIN_ROOT\}/hooks/[\w.-]+\.sh"( [\w.-]+)?$')

    def test_bash_scripts_use_git_bash(self):
        # 裸 bash 在 Windows 會解析成 WSL 的 /bin/bash，讀不到 C:/ 路徑
        for h in hook_entries():
            if h["command"].startswith("bash "):
                with self.subTest(cmd=h["command"]):
                    self.assertIn("bin\\bash.exe", h["commandWindows"])
                    self.assertNotIn("sh.exe", h["commandWindows"].replace("bash.exe", ""))


class LineEndings(unittest.TestCase):
    """Windows clone 預設 core.autocrlf=true：run-py.sh 變 CRLF 後 `S=...\\r` 找不到腳本，所有 hook 靜默不跑。"""

    def test_gitattributes_forces_lf_for_sh(self):
        attrs = (REPO / ".gitattributes").read_text(encoding="utf-8").split("\n")
        self.assertIn("*.sh text eol=lf", attrs)

    def test_hook_scripts_have_no_cr(self):
        for f in HOOKS_DIR.glob("*.sh"):
            with self.subTest(f=f.name):
                self.assertNotIn(b"\r", f.read_bytes())


@unittest.skipUnless(sys.platform == "win32", "commandWindows 只在 Windows 實跑")
class WindowsRun(unittest.TestCase):
    """用 Windows PowerShell 5.1 與 pwsh 7（有裝的話）實跑 commandWindows。"""

    shells = [s for s in (shutil.which("powershell"), shutil.which("pwsh")) if s]

    def run_cmd(self, shell, script, payload, env_extra=None):
        # Windows 的環境變數名稱不分大小寫；覆寫一律用大寫，免得子程序拿到兩份
        env = {k.upper(): v for k, v in os.environ.items()}
        env["CLAUDE_PLUGIN_ROOT"] = str(HOOKS_DIR.parent)
        env.update(env_extra or {})
        return subprocess.run([shell, "-NoProfile", "-Command", script], input=json.dumps(payload).encode("utf-8"),
                              capture_output=True, env=env, timeout=60)

    def agent_guard_cmd(self):
        return next(h["commandWindows"] for h in hook_entries() if "agent-model-guard.py" in h["command"])

    def test_python_hook_runs(self):
        self.assertTrue(self.shells, "找不到 powershell 或 pwsh")
        payload = {"tool_name": "Agent", "tool_input": {"subagent_type": "general-purpose", "prompt": "中文"}}
        for shell in self.shells:
            with self.subTest(shell=shell):
                p = self.run_cmd(shell, self.agent_guard_cmd(), payload)
                self.assertEqual(p.returncode, 0, p.stderr.decode("utf-8", "replace"))
                self.assertIn(b"sonnet", p.stdout)

    def test_notification_exits_zero(self):
        cmd = next(h["commandWindows"] for h in hook_entries() if h["command"].endswith("notification.sh\""))
        for shell in self.shells:
            with self.subTest(shell=shell):
                p = self.run_cmd(shell, cmd, {"stop_hook_active": True}, {"HC_TERMINAL_ID": "test"})
                self.assertEqual(p.returncode, 0, p.stderr.decode("utf-8", "replace"))

    def test_missing_sh_fails_open(self):
        # Windows 會替每個新程序重設 ProgramFiles，從外面覆寫不了，所以把候選路徑換成不存在的目錄
        system = os.environ.get("SystemRoot", r"C:\Windows")
        nowhere = {"PATH": f"{system}\\System32;{system}\\System32\\WindowsPowerShell\\v1.0"}
        script = self.agent_guard_cmd().replace("\\Git\\bin\\", "\\NoSuchGit\\bin\\")
        self.assertNotEqual(script, self.agent_guard_cmd())
        for shell in self.shells:
            with self.subTest(shell=shell):
                p = self.run_cmd(shell, script, {"tool_name": "Agent", "tool_input": {}}, nowhere)
                self.assertEqual((p.returncode, p.stdout), (0, b""), p.stderr)


if __name__ == "__main__":
    unittest.main()
