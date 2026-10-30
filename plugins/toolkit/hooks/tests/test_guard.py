"""guard hook 測試：每條 guard 都要證明能抓到它記錄的錯，且不誤擋常見的正常指令。

三層 guard：plugin 層（本 plugin 的 guards/）→ user 層（~/.claude/guards）→ 專案層（<專案>/.claude/guards），
同名檔由後讀的覆寫。測試一律用 tmp_path 組出三層，不碰真的 HOME。
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[2]
HOOK = PLUGIN / "hooks" / "guard.py"

# 專案層的假規則：擋寫入內容裡的某個假字串
FAKE_RULE = (
    "---\ntool: Write, Edit, MultiEdit\npattern: 'FORBIDDEN_TOKEN'\naction: deny\n"
    "evidence: 測試用假規則\n---\n不要寫這個字串。\n"
)


def make_env(tmp: Path, *, plugin=True, project_files=None):
    """在 tmp 下建 home / project 目錄，回傳 subprocess 用的 env。"""
    home, project = tmp / "home", tmp / "project"
    (home / ".claude").mkdir(parents=True, exist_ok=True)
    (project / ".claude" / "guards").mkdir(parents=True, exist_ok=True)
    for name, text in (project_files or {}).items():
        (project / ".claude" / "guards" / name).write_bytes(text.encode("utf-8"))
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PLUGIN_ROOT"}
    env.update(HOME=str(home), USERPROFILE=str(home), CLAUDE_PROJECT_DIR=str(project))
    if plugin:
        env["CLAUDE_PLUGIN_ROOT"] = str(PLUGIN)
    return env


@pytest.fixture(scope="module")
def env():
    tmp = Path(tempfile.mkdtemp())
    e = make_env(tmp, project_files={"fake-token.md": FAKE_RULE})
    yield e
    shutil.rmtree(tmp)


def run(env, tool, **inp):
    r = subprocess.run([sys.executable, str(HOOK)], input=json.dumps({"tool_name": tool, "tool_input": inp}),
                       capture_output=True, text=True, encoding="utf-8", env=env)
    assert r.returncode == 0, r.stderr
    assert "略過" not in r.stderr, r.stderr
    return json.loads(r.stdout)["hookSpecificOutput"]["permissionDecision"] if r.stdout else None


@pytest.mark.parametrize("cmd", [
    "git add -A", "git add .", "git add --all", "cd repo && git add -A && git commit -m x",
    "git add src/a.ts .", "git status; git add -A",
])
def test_git_add_all_denied(env, cmd):
    assert run(env, "Bash", command=cmd) == "deny"


@pytest.mark.parametrize("cmd", [
    "git add src/a.ts docs/tasks.md", "git add .claude/rules/x.md", "git add ./src/a.ts",
    "git commit -m 'docs: ban git add -A in rules'", "git status --short", "grep -n 'git add .' README.md",
])
def test_normal_commands_pass(env, cmd):
    assert run(env, "Bash", command=cmd) is None


@pytest.mark.parametrize("cmd", [
    "git push --force origin main", "git push -f origin feat/site", "git push --force-with-lease",
    "git reset --hard HEAD~1", "git clean -fd", "git clean -xdf", "git fetch && git reset --hard origin/main",
])
def test_destructive_asks(env, cmd):
    assert run(env, "Bash", command=cmd) == "ask"


@pytest.mark.parametrize("cmd", ["git push origin main feat/site", "git reset --soft HEAD~1", "git clean -n",
                                 "git reset HEAD file.ts"])
def test_safe_git_passes(env, cmd):
    assert run(env, "Bash", command=cmd) is None


def test_deny_wins_over_ask(env):
    assert run(env, "Bash", command="git add -A && git push -f") == "deny"


def test_project_rule_blocked_in_write_and_edit(env):
    assert run(env, "Write", file_path="x.py", content="X = 'FORBIDDEN_TOKEN'") == "deny"
    assert run(env, "Edit", file_path="x.py", old_string="a", new_string="to: FORBIDDEN_TOKEN") == "deny"
    assert run(env, "MultiEdit", file_path="x.py", edits=[{"old_string": "a", "new_string": "FORBIDDEN_TOKEN"}]) == "deny"


def test_project_rule_text_without_token_passes(env):
    assert run(env, "Write", file_path="AGENTS.md", content="forbidden token 的說明文字") is None


def test_project_guard_only_in_its_project(env):
    other = {**env, "CLAUDE_PROJECT_DIR": "/nonexistent"}
    assert run(other, "Write", file_path="x", content="FORBIDDEN_TOKEN") is None


def test_bad_stdin_fails_open(env):
    r = subprocess.run([sys.executable, str(HOOK)], input="not json", capture_output=True, text=True, env=env)
    assert r.returncode == 0 and r.stdout == ""


def test_guard_without_evidence_is_skipped(env, tmp_path):
    d = tmp_path / ".claude" / "guards"
    d.mkdir(parents=True)
    (d / "x.md").write_text("---\ntool: Bash\npattern: 'ls'\naction: deny\n---\n修法\n", encoding="utf-8")
    r = subprocess.run([sys.executable, str(HOOK)], input=json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls"}}),
                       capture_output=True, text=True, encoding="utf-8", env={**env, "CLAUDE_PROJECT_DIR": str(tmp_path)})
    assert r.stdout == "" and "格式不完整" in r.stderr


# ---- 分層 ----

def test_plugin_guards_apply_without_home(tmp_path):
    """HOME 和專案都沒有 guards，只有 plugin 層：全量 add 仍要被擋。"""
    e = make_env(tmp_path)
    assert not (Path(e["HOME"]) / ".claude" / "guards").exists()
    assert run(e, "Bash", command="git add -A") == "deny"


def test_project_guard_overrides_same_name(tmp_path):
    """專案層同名檔放寬規則（只擋 --all，且降為 ask）後，以專案層為準。"""
    relaxed = (
        "---\ntool: Bash\npattern: 'git\\s+add\\s+--all'\naction: ask\n"
        "evidence: 專案自訂放寬\n---\n專案層說明\n"
    )
    e = make_env(tmp_path, project_files={"git-add-all.md": relaxed})
    assert run(e, "Bash", command="git add -A") is None
    assert run(e, "Bash", command="git add --all") == "ask"


def test_user_layer_overrides_plugin_layer(tmp_path):
    e = make_env(tmp_path)
    ug = Path(e["HOME"]) / ".claude" / "guards"
    ug.mkdir(parents=True)
    (ug / "git-add-all.md").write_text(
        "---\ntool: Bash\npattern: 'NEVER_MATCHES_XYZ'\naction: deny\nevidence: user 放寬\n---\n說明\n", encoding="utf-8")
    assert run(e, "Bash", command="git add -A") is None


def test_crlf_guard_file_parses(tmp_path):
    """規則檔存成 CRLF（Windows checkout）時，decide 結果要和 LF 相同。"""
    crlf = FAKE_RULE.replace("\n", "\r\n")
    e = make_env(tmp_path, project_files={"fake-token.md": crlf})
    assert run(e, "Write", file_path="x", content="FORBIDDEN_TOKEN") == "deny"
    assert run(e, "Write", file_path="x", content="ok") is None


def test_plugin_guards_with_crlf_copy(tmp_path):
    """plugin 層的 guards 被轉成 CRLF 時一樣能載入。"""
    fake_root = tmp_path / "plugin"
    (fake_root / "guards").mkdir(parents=True)
    for f in (PLUGIN / "guards").glob("*.md"):
        (fake_root / "guards" / f.name).write_bytes(f.read_bytes().replace(b"\n", b"\r\n"))
    e = {**make_env(tmp_path), "CLAUDE_PLUGIN_ROOT": str(fake_root)}
    assert run(e, "Bash", command="git add -A") == "deny"
    assert run(e, "Bash", command="git reset --hard") == "ask"
