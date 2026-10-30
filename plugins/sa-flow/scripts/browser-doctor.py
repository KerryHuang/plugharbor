#!/usr/bin/env python
"""browser-doctor：瀏覽器 agent 起手檢查（設計 §4.2）。
  python browser-doctor.py [--host claude|codex|both]
stdout 單行 OK / FAIL <原因>；exit 0 / 1。順便清殘留暫存 profile 與孤兒 MCP server。
"""
import argparse, json, os, pathlib, re, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8")

STD_CLAUDE = '"command": "npx", "args": ["-y", "chrome-devtools-mcp@latest", "--isolated", "--viewport", "1680x1000"]（Windows: "command": "cmd", "args": ["/c", "npx", ...]）'
STD_CODEX = 'codex mcp add chrome-devtools -- npx -y chrome-devtools-mcp@latest --isolated --viewport 1680x1000（Git Bash 前加 MSYS_NO_PATHCONV=1）'

def _check(args, std):
    if args == "MISSING":
        return f"chrome-devtools 未註冊。標準：{std}"
    if not any(a.startswith("chrome-devtools-mcp") for a in args):
        return f"chrome-devtools 註冊不是 chrome-devtools-mcp。標準：{std}"
    if "--isolated" not in args:
        return f"chrome-devtools 註冊缺 --isolated（現為 {' '.join(args)}）。標準：{std}"
    return None

def check_claude_args(args): return _check(args, STD_CLAUDE)
def check_codex_args(args): return _check(args, STD_CODEX)

def version_ok(v, floor=(1, 8, 0)):
    m = re.match(r"(\d+)\.(\d+)\.(\d+)", v or "")
    return bool(m) and tuple(int(x) for x in m.groups()) >= floor

def stale_profiles(tmp_dir, live_dirs):
    live = {os.path.normcase(str(pathlib.Path(d).resolve())) for d in live_dirs}
    return sorted(p for p in pathlib.Path(tmp_dir).glob("puppeteer_dev_chrome_profile-*")
                  if p.is_dir() and os.path.normcase(str(p.resolve())) not in live)

def orphan_server_pids(ps_lines):
    out = []
    for line in ps_lines:
        parts = line.strip().split(None, 2)
        if len(parts) < 3: continue
        pid, ppid, cmd = parts
        if ppid == "1" and "chrome-devtools-mcp" in cmd and "npm exec" not in cmd:
            out.append(int(pid))
    return out

# ---- 以下是有副作用的部分，測試不碰 ----
def _claude_args():
    p = pathlib.Path.home() / ".claude.json"
    if not p.exists():
        return None
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return d.get("mcpServers", {}).get("chrome-devtools", {}).get("args") or "MISSING"
    except Exception:
        return "MISSING"

def _codex_args():
    p = pathlib.Path.home() / ".codex" / "config.toml"
    if not p.exists():
        return None
    try:
        txt = p.read_text(encoding="utf-8")
    except Exception:
        return "MISSING"
    m = re.search(r"\[mcp_servers\.chrome-devtools\](.*?)(?=\n\[|\Z)", txt, re.S)
    if not m: return "MISSING"
    a = re.search(r"args\s*=\s*\[(.*?)\]", m.group(1), re.S)
    return re.findall(r'"([^"]*)"', a.group(1)) if a else "MISSING"

def _pkg_version():
    try:
        r = subprocess.run(["npx", "-y", "chrome-devtools-mcp@latest", "--version"], capture_output=True, text=True, errors="replace", timeout=120, shell=(os.name == "nt"))
        return (r.stdout.strip().splitlines() or [""])[-1]
    except Exception:
        return ""

def parse_user_data_dirs(text):
    pairs = re.findall(r'--user-data-dir=(?:"([^"]+)"|(\S+))', text)
    dirs = [a or b for a, b in pairs]
    return [d for d in dirs if "puppeteer_dev_chrome_profile-" in d]

def _live_profile_dirs():
    if os.name == "nt":
        cmd = ["powershell", "-NoProfile", "-Command",
               "Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | % { $_.CommandLine }"]
    else:
        cmd = ["ps", "-eo", "command"]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, errors="replace", timeout=30).stdout
    except Exception:
        return set()
    return {os.path.normcase(str(pathlib.Path(d).resolve())) for d in parse_user_data_dirs(out)}

def _ps_lines():
    if os.name == "nt": return []   # Windows 沒有 PPID=1 孤兒語意
    try:
        return subprocess.run(["ps", "-eo", "pid,ppid,command"], capture_output=True, text=True, errors="replace", timeout=30).stdout.splitlines()[1:]
    except Exception:
        return []

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--host", choices=["claude", "codex", "both"], default="both")
    host = ap.parse_args().host
    problems = []
    claude_a = _claude_args() if host in ("claude", "both") else None
    codex_a = _codex_args() if host in ("codex", "both") else None
    if host == "both" and claude_a is None and codex_a is None:
        problems.append("找不到 ~/.claude.json 與 ~/.codex/config.toml，至少要註冊一邊")
    else:
        if host in ("claude", "both"):
            if claude_a is None:
                if host == "claude":
                    problems.append("找不到 ~/.claude.json 的 mcpServers.chrome-devtools")
            else:
                problems.append(check_claude_args(claude_a))
        if host in ("codex", "both"):
            if codex_a is None:
                if host == "codex":
                    problems.append("找不到 ~/.codex/config.toml 的 [mcp_servers.chrome-devtools]")
            else:
                problems.append(check_codex_args(codex_a))
    v = _pkg_version()
    if not version_ok(v): problems.append(f"chrome-devtools-mcp 版本 {v or '未知'} < 1.8.0（pageId 必填自 1.8.0 起）")
    problems = [p for p in problems if p]
    # 清理（不影響 OK/FAIL）
    removed = 0
    for d in stale_profiles(tempfile.gettempdir(), _live_profile_dirs()):
        shutil.rmtree(d, ignore_errors=True); removed += 1
    killed = 0
    for pid in orphan_server_pids(_ps_lines()):
        try: os.kill(pid, 9); killed += 1
        except Exception: pass
    note = f"（清除殘留 profile {removed}、孤兒 server {killed}）"
    if problems:
        print("FAIL " + "；".join(problems) + note); sys.exit(1)
    print("OK " + note); sys.exit(0)

if __name__ == "__main__":
    main()
