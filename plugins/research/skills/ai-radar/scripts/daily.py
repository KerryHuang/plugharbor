#!/usr/bin/env python3
"""ai-radar 每日版的 runner（launchd 每個工作日 09:00 叫 `daily.py run`）。

模型沒有 Bash；同一階段不會同時拿到私人資料和對外管道；git、驗證、backlog 標記、報告、通知都由這支腳本做：
  前置：週末不跑、取得互斥鎖、驗證專用 worktree 身分、數待審 radar/* branch、pull blog、每週重算 work-profile
  階段 B（消化）：工具只有 Read／Edit／Write／Glob／Grep，限定 worktree；prompt 只帶挑中的那一項 backlog
    → 檢查改動路徑 → 用 main 已 commit 的 validate.py 驗 worktree → 開 radar/* branch、固定訊息 commit（關 hook）
  階段 A（蒐集）：工具只有 WebSearch／WebFetch；prompt 只帶工具名稱與當天官方發布資料
  收尾：寫報告、全部成功才寫完成標記、只在新草稿／草稿滿／失敗時通知
兩個階段都用 `--setting-sources ""`（不載入任何 settings 檔）＋`--strict-mcp-config`＋`--restricted`，
權限只有命令列的 dontAsk＋allow＋deny。

子指令：
  run         跑一次每日流程
  candidates  列出可做成草稿的候選待辦（JSON）
  plist       印出 launchd plist（install-daily.sh 用）

路徑都可用環境變數覆寫（乾跑時指到複本）：
  AI_RADAR_OUT（~/.claude/ai-radar）、RADAR_REPO（~/Work/projects/plugharbor）、
  RADAR_WORKTREE（~/Work/projects/plugharbor-radar）、RADAR_BLOG（~/Work/projects/blog）、RADAR_CLAUDE（claude）
"""
import argparse
import fcntl
import json
import os
import plistlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
DAILY_MD = HERE.parent / "references" / "daily.md"
LABEL = "com.plugharbor.ai-radar-daily"
MAX_PENDING = 3
MAX_TRIES = 3  # 一天最多讓階段 B 看幾項候選
OPEN_STATES = ("待評估", "採納", "進行中")
SKIP_MARKS = ("每日版略過", "每日草稿")
PROFILE_MAX_AGE = 7 * 86400
TIMEOUT_B = 30 * 60
TIMEOUT_A = 15 * 60
ENV_KEYS = ("AI_RADAR_OUT", "RADAR_REPO", "RADAR_WORKTREE", "RADAR_BLOG", "RADAR_CLAUDE")
NO_SETTINGS = ["--setting-sources", "", "--strict-mcp-config", "--restricted",
               "--permission-mode", "dontAsk", "--output-format", "json", "--no-session-persistence"]

# 階段 B 可以寫的範圍（也是 validate.py 外洩掃描涵蓋的範圍）；其餘一律拒絕
DRAFT_DIRS = ("plugins/", "docs/", ".claude-plugin/")
DRAFT_FILES = ("README.md", "AGENTS.md", "CLAUDE.md")
DRAFT_EXT = {".md", ".py", ".sh", ".js", ".css", ".json", ".yml", ".yaml", ".txt"}  # 同 validate.py 的 TEXT_EXT
# 權限層另外 deny 的 worktree 路徑（hook、驗證器、設定、git metadata、安裝腳本、本機黑名單）
FORBIDDEN = ("scripts/hooks/**", "scripts/ci/**", ".claude/**", ".git/**", ".git*", ".github/**",
             "setup/**", ".leak-denylist", ".private/**")
SENSITIVE_HOME = (".claude", ".ssh", ".aws", ".gnupg", ".config", ".codex", ".pi", "Library")
NAME = re.compile(r"^[A-Za-z][A-Za-z0-9._+-]*$")
RESULT_LINE = re.compile(r"^RESULT: (?:DRAFT|SKIP).*$", re.M)
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")


class Fail(Exception):
    """每日流程中止；訊息會進報告、通知與 log。"""


@dataclass
class Config:
    out: Path
    repo: Path
    worktree: Path
    blog: Path
    claude: str

    @classmethod
    def from_env(cls):
        home = Path.home()
        env = os.environ.get
        return cls(out=Path(env("AI_RADAR_OUT", home / ".claude" / "ai-radar")).expanduser(),
                   repo=Path(env("RADAR_REPO", home / "Work" / "projects" / "plugharbor")).expanduser(),
                   worktree=Path(env("RADAR_WORKTREE", home / "Work" / "projects" / "plugharbor-radar")).expanduser(),
                   blog=Path(env("RADAR_BLOG", home / "Work" / "projects" / "blog")).expanduser(),
                   claude=env("RADAR_CLAUDE", "claude"))


@dataclass
class Candidate:
    num: int
    score: int
    status: str
    source: str
    summary: str
    handoff: str
    note: str


@dataclass
class StageResult:
    ok: bool
    text: str
    denials: list
    raw: str


# ---------- backlog ----------

def split_row(line: str):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def parse_backlog(text: str):
    items = []
    for line in text.splitlines():
        cells = split_row(line)
        if len(cells) < 7 or not cells[0].isdigit():
            continue
        m = re.search(r"=\s*(\d+)", cells[3]) or re.fullmatch(r"(\d+)", cells[3])
        if not m:
            continue
        items.append(Candidate(num=int(cells[0]), score=int(m.group(1)), status=cells[4], source=cells[1],
                               summary=cells[2], handoff=cells[5], note=cells[6]))
    return items


def candidates(text: str, taken: set, limit: int = 5):
    """open、沒被每日版處理過、也沒有 radar/*-<#> branch 的項目，分數高的先、同分 # 小的先。"""
    pool = [c for c in parse_backlog(text)
            if c.status.startswith(OPEN_STATES) and c.num not in taken
            and not any(mark in c.note for mark in SKIP_MARKS)]
    return sorted(pool, key=lambda c: (-c.score, c.num))[:limit]


def one_line(text: str, limit: int):
    text = re.sub(r"\s+", " ", text.replace("|", "／")).strip()
    return text[:limit] + ("…" if len(text) > limit else "")


def mark_backlog(path: Path, num: int, mark: str):
    """在第 num 項的決策備註最後補一段標記（只動這一格），原子寫回。"""
    lines = path.read_text(encoding="utf-8").split("\n")
    for i, line in enumerate(lines):
        cells = split_row(line)
        if len(cells) >= 7 and cells[0] == str(num):
            note = cells[-1]
            cells[-1] = mark if note in ("", "-") else f"{note}；{mark}"
            lines[i] = "| " + " | ".join(cells) + " |"
            break
    else:
        raise Fail(f"backlog 找不到 #{num}，沒有補標記")
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text("\n".join(lines), encoding="utf-8")
    os.replace(tmp, path)


# ---------- 外洩黑名單（讀主 checkout 那份 .leak-denylist，格式同 validate.py） ----------

def load_denylist(repo: Path):
    f = repo / ".leak-denylist"
    if not f.exists():
        return None
    pats = []
    for line in f.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            pats.append(re.compile(line[6:] if line.startswith("regex:") else re.escape(line), re.I))
    return pats


def leaks(text: str, deny):
    return bool(EMAIL.search(text) or "/Users/" in text or "/home/" in text
                or any(p.search(text) for p in deny or []))


# ---------- git ----------

def git(repo: Path, *args, check=True, strip=True):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8")
    if check and r.returncode != 0:
        raise Fail(f"git {' '.join(args)} 失敗：{r.stderr.strip()}")
    return r.stdout.strip() if strip else r.stdout


def radar_branches(repo: Path, unmerged=False):
    args = ["branch", "--format=%(refname:short)", *(["--no-merged", "main"] if unmerged else []),
            "--list", "radar/*"]
    return [b for b in git(repo, *args).splitlines() if b]


def branch_numbers(branches):
    return {int(m.group(1)) for b in branches if (m := re.search(r"-(\d+)$", b))}


def real(p) -> Path:
    return Path(os.path.realpath(p))


def verify_worktree(cfg: Config):
    """worktree 必須是 cfg.repo 註冊過的 linked worktree，不是主 checkout、也不在它裡面。回傳實體路徑。"""
    repo, wt = real(cfg.repo), real(cfg.worktree)
    if wt == repo or repo in wt.parents or wt in repo.parents:
        raise Fail(f"專用 worktree 不能是主 checkout 或在它裡面／外面包住它：{wt}")
    top = real(git(wt, "rev-parse", "--show-toplevel"))
    if top != wt:
        raise Fail(f"{wt} 不是 worktree 根目錄（根目錄是 {top}）")
    common = real(git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir"))
    if real(git(wt, "rev-parse", "--path-format=absolute", "--git-common-dir")) != common:
        raise Fail(f"{wt} 不屬於 {repo} 這個 repo")
    if real(git(wt, "rev-parse", "--path-format=absolute", "--git-dir")) == common:
        raise Fail(f"{wt} 是主 checkout，不是 linked worktree")
    listed = {real(line[9:]) for line in git(repo, "worktree", "list", "--porcelain").splitlines()
              if line.startswith("worktree ")}
    if wt not in listed:
        raise Fail(f"{wt} 沒有登記在 {repo} 的 worktree 清單")
    return wt


def prepare_worktree(cfg: Config):
    if not cfg.worktree.exists():
        git(cfg.repo, "worktree", "add", "--detach", str(cfg.worktree), "main")
    wt = verify_worktree(cfg)
    if git(wt, "status", "--porcelain", "--untracked-files=all"):
        raise Fail(f"專用 worktree 有未 commit 的改動，先處理：{wt}")
    git(wt, "switch", "-q", "--detach", "main")
    return wt


def status_entries(wt: Path):
    """回傳 (改動／新增的路徑, 被 ignore 的路徑)；用 -z 才不會被中文檔名的跳脫與引號干擾。"""
    out = git(wt, "status", "--porcelain=v1", "-z", "--untracked-files=all", "--ignored=matching", strip=False)
    changed, ignored = [], set()
    parts = out.split("\0")
    i = 0
    while i < len(parts):
        entry = parts[i]
        i += 1
        if not entry:
            continue
        code, path = entry[:2], entry[3:]
        if code == "!!":
            ignored.add(path)
            continue
        if code[0] in "RC":
            i += 1  # 下一段是舊路徑
        changed.append((code, path))
    return changed, ignored


def path_allowed(path: str):
    return (path.startswith(DRAFT_DIRS) or path in DRAFT_FILES) and Path(path).suffix in DRAFT_EXT


def discard(wt: Path, new_ignored):
    git(wt, "reset", "-q", "--hard", "HEAD")
    git(wt, "clean", "-fdq")
    for p in new_ignored:
        target = wt / p
        if wt in real(target).parents:
            shutil.rmtree(target) if target.is_dir() else target.unlink(missing_ok=True)


def run_validate(cfg: Config, wt: Path):
    """用 main 已 commit 的 validate.py 原始碼驗 worktree：不執行 worktree 裡的任何檔，sys.path 也不含 worktree。"""
    src = git(cfg.repo, "show", "main:scripts/ci/validate.py", strip=False)
    target = wt / "scripts" / "ci" / "validate.py"  # 只當 __file__，讓 validate.py 的 ROOT 指向 worktree
    code = ("import sys; p = sys.argv[1]; src = sys.stdin.read(); "
            "exec(compile(src, p, 'exec'), {'__name__': '__main__', '__file__': p})")
    return subprocess.run([sys.executable, "-I", "-c", code, str(target)], input=src, cwd=wt,
                          capture_output=True, text=True, encoding="utf-8")


def commit_draft(cfg: Config, wt: Path, branch: str, paths, message: str):
    git(wt, "switch", "-q", "-c", branch)
    git(wt, "add", "--", *paths)
    staged = [p for p in git(wt, "diff", "--cached", "--name-only", "-z", strip=False).split("\0") if p]
    if sorted(staged) != sorted(paths):
        raise Fail(f"暫存區和預期不符：{staged}")
    subprocess.run(["git", "-C", str(wt), "-c", "core.hooksPath=/dev/null", "commit", "-q", "--no-gpg-sign",
                    "-m", message], check=True, capture_output=True)
    git(wt, "switch", "-q", "--detach", "main")


# ---------- claude ----------

def stage_text(name: str):
    """取 daily.md 裡 <!-- stage-X --> … <!-- /stage-X --> 之間的指示。"""
    text = DAILY_MD.read_text(encoding="utf-8")
    m = re.search(rf"<!-- stage-{name} -->\n(.*?)<!-- /stage-{name} -->", text, re.S)
    if not m:
        raise Fail(f"{DAILY_MD.name} 缺少 stage-{name} 段落")
    return m.group(1).strip()


def build_prompt(stage: str, ctx: dict):
    return (stage_text(stage) + "\n\n## 今天的資料（由 runner 準備）\n\n```json\n"
            + json.dumps(ctx, ensure_ascii=False, indent=2) + "\n```\n")


def rule(tool: str, path: Path, sub: str = "**"):
    return f"{tool}(/{'/' + str(path).lstrip('/')}/{sub})"  # 權限規則的絕對路徑寫成 //abs/path


def sensitive_paths(cfg: Config):
    home = real(Path.home())
    return [home / d for d in SENSITIVE_HOME] + [real(cfg.out), real(cfg.repo), real(cfg.blog)]


def cmd_b(cfg: Config, wt: Path):
    deny = ["Bash", "WebSearch", "WebFetch"]
    deny += [rule("Edit", wt, f) for f in FORBIDDEN]
    for p in sensitive_paths(cfg):
        deny += [rule("Read", p), rule("Edit", p)]
    return [cfg.claude, "-p", "--model", "sonnet", *NO_SETTINGS,
            "--tools", "Read,Edit,Write,Glob,Grep",
            "--allowedTools", rule("Read", wt), rule("Edit", wt), "Glob", "Grep",
            "--disallowedTools", *deny]


def cmd_a(cfg: Config):
    return [cfg.claude, "-p", "--model", "sonnet", *NO_SETTINGS,
            "--tools", "WebSearch,WebFetch",
            "--allowedTools", "WebSearch", "WebFetch",
            "--disallowedTools", "Bash", "Read", "Edit", "Write", "Glob", "Grep"]


def call_claude(cmd, prompt: str, cwd: Path, timeout: int, logfile: Path):
    try:
        r = subprocess.run(cmd, input=prompt, cwd=cwd, capture_output=True, text=True, encoding="utf-8",
                           timeout=timeout)
    except subprocess.TimeoutExpired:
        raise Fail(f"claude 超過 {timeout // 60} 分鐘沒結束")
    logfile.write_text(r.stdout + ("\n--- stderr ---\n" + r.stderr if r.stderr else ""), encoding="utf-8")
    try:
        data = json.loads(r.stdout)
    except json.JSONDecodeError:
        raise Fail(f"claude exit {r.returncode}，輸出不是 JSON，看 {logfile.name}")
    ok = r.returncode == 0 and not data.get("is_error")
    return StageResult(ok=ok, text=(data.get("result") or "").strip(), denials=data.get("permission_denials") or [],
                       raw=r.stdout)


# ---------- 蒐集階段的輸入 ----------

def profile_tools(profile: Path, deny):
    """從 work-profile 取工具名稱：plugin 名（skill 的冒號前）、CLI、MCP server；黑名單命中的不給。"""
    sections, cur = {}, None
    for line in profile.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            cur = line[3:].split("（")[0].strip()
            sections[cur] = []
        elif cur and (m := re.match(r"\|\s*`([^`]+)`\s*\|", line)):
            sections[cur].append(m.group(1))
    plugins = sorted({s.split(":")[0] for s in sections.get("Skill", []) if ":" in s})
    groups = {"plugins": plugins, "cli": sections.get("CLI", [])[:20], "mcp": sections.get("MCP server", [])}
    if deny is None:  # 沒有黑名單就只給 CLI：plugin 與 MCP 名稱最可能帶公司或專案名
        groups["plugins"], groups["mcp"] = [], []
    clean = {k: [n for n in v if NAME.match(n) and not leaks(n, deny)] for k, v in groups.items()}
    clean["always"] = ["claude-code"]
    return clean


def snapshot_items(path):
    if not path:
        return None
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    off = data.get("official") or {}
    keep = ("company", "repo", "title", "url", "time", "version")
    return {"items": [{k: it.get(k) for k in keep} for it in off.get("items", [])],
            "unavailable": off.get("unavailable", [])}


# ---------- 通知 ----------

def notify(message: str, enabled=True):
    print(f"[notify] {message}")
    if not enabled or sys.platform != "darwin":
        return
    esc = message.replace("\\", "\\\\").replace('"', '\\"')
    subprocess.run(["osascript", "-e",
                    f'display notification "{esc}" with title "ai-radar 每日" sound name "Glass"'],
                   capture_output=True)


# ---------- run ----------

def refresh_profile(cfg: Config, log):
    profile = cfg.out / "work-profile.md"
    if profile.exists() and time.time() - profile.stat().st_mtime < PROFILE_MAX_AGE:
        return profile
    sys.path.insert(0, str(HERE))
    import work_profile
    work_profile.main(["--out", str(profile)])
    log(f"work-profile 已重算：{profile}")
    return profile


def pull_blog(cfg: Config, today: str, no_pull: bool, log):
    if not (cfg.blog / ".git").exists():
        return None, f"沒有 blog repo（{cfg.blog.name}）"
    note = None
    if not no_pull:
        r = subprocess.run(["git", "-C", str(cfg.blog), "pull", "--ff-only", "-q"],
                           capture_output=True, text=True, encoding="utf-8")
        if r.returncode != 0:
            note = f"blog git pull 失敗（用本機現有資料）：{r.stderr.strip()}"
            log(note)
    snap = cfg.blog / "data" / "tech-snapshots" / f"{today}.json"
    if snap.exists():
        return str(snap), note
    return None, (note + "；" if note else "") + f"今天沒有 tech-snapshot（{snap.name}）"


def last_daily(out: Path, today: str):
    olds = sorted(p.name[:10] for p in (out / "logs").glob("*-daily.done") if p.name[:10] < today)
    return olds[-1] if olds else None


def digest(cfg: Config, wt: Path, cands, today: str, logs: Path, rep: dict, log):
    """階段 B：依序讓模型看候選（最多 MAX_TRIES 項），第一個做成草稿的就 commit。"""
    backlog = cfg.out / "adoption-backlog.md"
    deny = load_denylist(cfg.repo)
    _, baseline = status_entries(wt)
    for c in cands[:MAX_TRIES]:
        ctx = {"date": today, "item": asdict(c)}
        res = call_claude(cmd_b(cfg, wt), build_prompt("b", ctx), wt, TIMEOUT_B, logs / f"{today}-B{c.num}.json")
        rep["denials"] += [f"B #{c.num}：{json.dumps(d, ensure_ascii=False)[:200]}" for d in res.denials]
        changed, ignored = status_entries(wt)
        new_ignored = ignored - baseline
        m = RESULT_LINE.search(res.text)
        first = m.group(0).strip() if m else ""
        note = RESULT_LINE.sub("", res.text, count=1).strip()
        log(f"B #{c.num}: ok={res.ok} first={first!r} changed={changed} new_ignored={sorted(new_ignored)}")
        if not res.ok:
            discard(wt, new_ignored)
            raise Fail(f"階段 B（#{c.num}）claude 回報錯誤，改動已丟棄")
        bad = [p for _, p in changed if not path_allowed(p)] + sorted(new_ignored)
        if bad:
            discard(wt, new_ignored)
            raise Fail(f"階段 B（#{c.num}）改到不允許的路徑，改動已丟棄：{', '.join(bad)}")
        if first.startswith("RESULT: SKIP"):
            reason = one_line(first[len("RESULT: SKIP"):].lstrip(" ：:—-"), 80) or "（沒寫理由）"
            if changed:
                discard(wt, new_ignored)
            mark_backlog(backlog, c.num, f"每日版略過 {today}：{reason}")
            rep["skipped"].append(f"#{c.num}：{reason}")
            continue
        if not first.startswith("RESULT: DRAFT") or not changed:
            discard(wt, new_ignored)
            raise Fail(f"階段 B（#{c.num}）沒有照格式回報或沒有改動：{first[:80]!r}")
        v = run_validate(cfg, wt)
        tail = "\n".join((v.stdout + v.stderr).strip().splitlines()[-15:])
        rep["validate"] = f"{'通過' if v.returncode == 0 else '失敗'}\n\n```\n{tail}\n```"
        if v.returncode != 0:
            discard(wt, new_ignored)
            raise Fail(f"#{c.num} 的草稿沒通過 validate.py，改動已丟棄、沒有 commit")
        branch = f"radar/{today}-{c.num}"
        summary = one_line(c.summary, 60)
        message = f"radar: #{c.num} {summary}" if not leaks(summary, deny) else f"radar: #{c.num}"
        paths = [p for _, p in changed]
        commit_draft(cfg, wt, branch, paths, message)
        mark_backlog(backlog, c.num, f"每日草稿 {branch}（{today}）")
        rep["draft"] = {"branch": branch, "cand": c, "note": note,
                        "stat": git(cfg.repo, "diff", "--stat", f"main...{branch}")}
        return branch
    return None


def collect(cfg: Config, profile: Path, snapshot, today: str, logs: Path, rep: dict):
    """階段 A：只上網、不碰本機檔；輸入只有工具名稱與公開的官方發布資料。"""
    ctx = {"date": today, "since": last_daily(cfg.out, today), "tools": profile_tools(profile, load_denylist(cfg.repo)),
           "tech_snapshot": snapshot_items(snapshot)}
    with tempfile.TemporaryDirectory(prefix="ai-radar-a-") as empty:
        res = call_claude(cmd_a(cfg), build_prompt("a", ctx), Path(empty), TIMEOUT_A, logs / f"{today}-A.json")
    rep["denials"] += [f"A：{json.dumps(d, ensure_ascii=False)[:200]}" for d in res.denials]
    if not res.ok:
        raise Fail("階段 A（蒐集）claude 回報錯誤")
    rep["updates"] = res.text[:6000] or "（模型沒有輸出）"


def render_report(today: str, rep: dict, error):
    out = [f"# ai-radar 每日 — {today}", ""]
    if error:
        out += [f"> ❌ 執行失敗：{error}", ""]
    if rep.get("full"):
        out += [f"> ⚠ 待審草稿已滿 {MAX_PENDING} 個，先審：{'、'.join(rep['pending'])}", ""]
    out += ["## 今日草稿", ""]
    d = rep.get("draft")
    if d:
        c, b = d["cand"], d["branch"]
        out += [f"- branch：`{b}`（backlog #{c.num}，{c.score} 分：{one_line(c.summary, 80)}）",
                "- 審查與合併（在 plugharbor 主 checkout）：",
                f"  `git diff main...{b}` → 同意就 `git merge --no-ff {b}`、`git push`；不要就 `git branch -D {b}`",
                f"- 合併後到 backlog 把 #{c.num} 的狀態改成已完成（或你判斷的狀態）", "",
                "```", d["stat"], "```", "", "### 模型的說明", "", d["note"] or "（沒有）", ""]
    else:
        out += ["今日沒有草稿。" + ("" if rep.get("skipped") else "（沒有可看的候選）"), ""]
    if rep.get("skipped"):
        out += ["略過：", *[f"- {s}" for s in rep["skipped"]], ""]
    out += ["## 官方更新（最多 3 條）", "", rep.get("updates") or "（沒有執行到蒐集）", "",
            "## 收尾檢查（runner）", ""]
    if rep.get("validate"):
        out += [f"- validate.py：{rep['validate']}", ""]
    out += [f"- 被權限擋下的工具呼叫：{len(rep['denials'])} 次", *[f"  - {x}" for x in rep["denials"]],
            f"- tech-snapshot：{rep.get('snapshot') or rep.get('blog_note') or '無'}", ""]
    return "\n".join(out)


def run(args):
    cfg = Config.from_env()
    today_d = date.fromisoformat(args.today) if args.today else date.today()
    today = today_d.isoformat()
    if today_d.weekday() >= 5 and not args.weekend:
        print(f"{today} 是週末，不跑（launchd 睡眠補跑也會落到這裡）")
        return 0
    logs = cfg.out / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    lock = (logs / "daily.lock").open("w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("另一個 daily.py 正在執行，這次不跑")
        return 0
    done = logs / f"{today}-daily.done"
    report = cfg.out / f"{today}-daily.md"
    if done.exists():
        print(f"今天已跑完：{report}")
        return 0
    if report.exists():  # 上一次失敗留下的報告：保留供診斷，改名後重跑
        report.rename(report.with_name(f"{today}-daily.failed-{datetime.now():%H%M%S}.md"))
    logfile = logs / f"{today}-daily.log"

    def log(msg):
        with logfile.open("a", encoding="utf-8") as fh:
            fh.write(msg.rstrip() + "\n")

    rep = {"denials": [], "skipped": []}
    error = None
    try:
        wt = prepare_worktree(cfg)
        rep["pending"] = radar_branches(cfg.repo, unmerged=True)
        rep["full"] = len(rep["pending"]) >= MAX_PENDING
        snapshot, rep["blog_note"] = pull_blog(cfg, today, args.no_pull, log)
        rep["snapshot"] = Path(snapshot).name if snapshot else None
        profile = refresh_profile(cfg, log)
        backlog = cfg.out / "adoption-backlog.md"
        if not rep["full"] and backlog.exists():
            taken = branch_numbers(radar_branches(cfg.repo))
            digest(cfg, wt, candidates(backlog.read_text(encoding="utf-8"), taken), today, logs, rep, log)
        collect(cfg, profile, snapshot, today, logs, rep)
    except Fail as e:
        error = str(e)
    except Exception as e:  # 任何意外都要進報告與通知，不能靜默失敗
        error = f"{type(e).__name__}: {e}"
    report.write_text(render_report(today, rep, error), encoding="utf-8")
    log(f"FAIL: {error}" if error else "done")
    if error:
        notify(f"執行失敗：{one_line(error, 120)}", not args.no_notify)
        return 1
    done.write_text(datetime.now().isoformat(timespec="seconds") + "\n", encoding="utf-8")
    if rep.get("draft"):
        notify(f"新草稿 {rep['draft']['branch']} 待審，看 {report.name}", not args.no_notify)
    elif rep["full"]:
        notify(f"待審草稿已滿 {MAX_PENDING} 個，先審再出新草稿", not args.no_notify)
    return 0


def make_plist(python: str, path_env: str, log: str, env: dict):
    return plistlib.dumps({
        "Label": LABEL,
        "ProgramArguments": [python, str(Path(__file__).resolve()), "run"],
        "StartCalendarInterval": [{"Weekday": d, "Hour": 9, "Minute": 0} for d in range(1, 6)],
        "EnvironmentVariables": {"PATH": path_env, "PYTHONUTF8": "1", **env},
        "StandardOutPath": log,
        "StandardErrorPath": log,
        "RunAtLoad": False,
    }).decode("utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--no-pull", action="store_true", help="不 git pull blog（乾跑用）")
    r.add_argument("--no-notify", action="store_true")
    r.add_argument("--weekend", action="store_true", help="週末也跑（手動補跑用）")
    r.add_argument("--today", help="測試用：指定日期（YYYY-MM-DD）")
    c = sub.add_parser("candidates")
    c.add_argument("--backlog", required=True)
    c.add_argument("--repo", help="有給就排除已有 radar/*-<#> branch 的項目")
    c.add_argument("--limit", type=int, default=5)
    p = sub.add_parser("plist")
    p.add_argument("--python", required=True)
    p.add_argument("--path", required=True, help="launchd 的 PATH（要含 claude、git 所在目錄）")
    p.add_argument("--log", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "run":
        return run(a)
    if a.cmd == "candidates":
        taken = branch_numbers(radar_branches(Path(a.repo))) if a.repo else set()
        text = Path(a.backlog).read_text(encoding="utf-8")
        print(json.dumps([asdict(x) for x in candidates(text, taken, a.limit)], ensure_ascii=False, indent=2))
        return 0
    env = {k: os.environ[k] for k in ENV_KEYS if os.environ.get(k)}
    sys.stdout.write(make_plist(a.python, a.path, a.log, env))
    return 0


if __name__ == "__main__":
    sys.exit(main())
