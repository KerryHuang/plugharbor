#!/usr/bin/env python3
"""ai-radar 每日版的編排腳本（launchd 每個工作日 09:00 叫 `daily.py run`）。

確定性的步驟都在這裡做，模型只負責「消化一項待辦＋少量蒐集＋寫報告」，權限白名單才能壓到最小：
  前置：準備專用 worktree、數待審 radar/* branch、pull blog、每週重算 work-profile、排出候選待辦
  執行：claude -p --model sonnet --permission-mode dontAsk --allowedTools <白名單>
  收尾：新草稿跑 validate.py、worktree 切回 detached main、只在新草稿／草稿滿／失敗時通知

子指令：
  run         跑一次每日流程
  candidates  列出可做成草稿的候選待辦（JSON）
  plist       印出 launchd plist（install-daily.sh 用）

路徑都可用環境變數覆寫（乾跑時指到複本）：
  AI_RADAR_OUT（~/.claude/ai-radar）、RADAR_REPO（~/Work/projects/plugharbor）、
  RADAR_WORKTREE（~/Work/projects/plugharbor-radar）、RADAR_BLOG（~/Work/projects/blog）、RADAR_CLAUDE（claude）
"""
import argparse
import json
import os
import plistlib
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
DAILY_MD = HERE.parent / "references" / "daily.md"
BACKLOG_RULES = HERE.parents[2] / "references" / "adoption-backlog.md"
LABEL = "com.plugharbor.ai-radar-daily"
MAX_PENDING = 3
OPEN_STATES = ("待評估", "採納", "進行中")
SKIP_MARKS = ("每日版略過", "每日草稿")
PROFILE_MAX_AGE = 7 * 86400
CLAUDE_TIMEOUT = 60 * 60
ENV_KEYS = ("AI_RADAR_OUT", "RADAR_REPO", "RADAR_WORKTREE", "RADAR_BLOG", "RADAR_CLAUDE")


class Fail(Exception):
    """每日流程中止；訊息會進通知與 log。"""


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
    summary: str
    handoff: str
    note: str = field(repr=False)


# ---------- backlog ----------

def parse_backlog(text: str):
    items = []
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 7 or not cells[0].isdigit():
            continue
        m = re.search(r"=\s*(\d+)", cells[3]) or re.fullmatch(r"(\d+)", cells[3])
        if not m:
            continue
        items.append(Candidate(num=int(cells[0]), score=int(m.group(1)), status=cells[4],
                               summary=cells[2], handoff=cells[5], note=cells[6]))
    return items


def candidates(text: str, taken: set, limit: int = 5):
    """open、沒被每日版處理過、也沒有 radar/*-<#> branch 的項目，分數高的先、同分 # 小的先。"""
    pool = [c for c in parse_backlog(text)
            if c.status.startswith(OPEN_STATES) and c.num not in taken
            and not any(mark in c.note for mark in SKIP_MARKS)]
    return sorted(pool, key=lambda c: (-c.score, c.num))[:limit]


# ---------- git ----------

def git(repo: Path, *args, check=True):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8")
    if check and r.returncode != 0:
        raise Fail(f"git {' '.join(args)} 失敗：{r.stderr.strip()}")
    return r.stdout.strip()


def radar_branches(repo: Path, unmerged=False):
    args = ["branch", "--format=%(refname:short)", *(["--no-merged", "main"] if unmerged else []),
            "--list", "radar/*"]
    return [b for b in git(repo, *args).splitlines() if b]


def branch_numbers(branches):
    return {int(m.group(1)) for b in branches if (m := re.search(r"-(\d+)$", b))}


def prepare_worktree(cfg: Config):
    if not cfg.worktree.exists():
        git(cfg.repo, "worktree", "add", "--detach", str(cfg.worktree), "main")
        return
    if git(cfg.worktree, "status", "--porcelain"):
        raise Fail(f"專用 worktree 有未 commit 的改動，先處理：{cfg.worktree}")
    git(cfg.worktree, "switch", "--detach", "main")


# ---------- claude ----------

def allowed_tools(cfg: Config):
    def scoped(path: Path):
        p = "/" + str(path).lstrip("/")  # 權限規則的 //絕對路徑；Edit 規則涵蓋所有寫檔工具（含 Write）
        return [f"Edit(/{p}/**)"]
    return ["Read", "Glob", "Grep", "WebSearch", "WebFetch", *scoped(cfg.out), *scoped(cfg.worktree),
            "Bash(git status:*)", "Bash(git diff:*)", "Bash(git log:*)",
            "Bash(git switch -c radar/*)", "Bash(git add:*)", "Bash(git commit:*)"]


DISALLOWED = ["Bash(git push:*)"]


def claude_cmd(cfg: Config, prompt: str):
    # 不載入 user 層設定：user 的 Stop hook 會每天跳通知、SessionStart 注入的流程（如先 brainstorming 問人）
    # 會讓無人值守的執行卡住；只留 worktree 的專案層設定（repo 慣例），權限全靠 dontAsk＋白名單
    cmd = [cfg.claude, "-p", prompt, "--model", "sonnet", "--permission-mode", "dontAsk",
           "--setting-sources", "project,local", "--strict-mcp-config", "--allowedTools", *allowed_tools(cfg), "--disallowedTools", *DISALLOWED,
           "--add-dir", str(cfg.out)]
    if cfg.blog.is_dir():
        cmd += ["--add-dir", str(cfg.blog)]
    return cmd


def build_prompt(ctx: dict):
    return (f"你是 ai-radar 每日版的背景執行（launchd 觸發，沒有人在看）。讀 {DAILY_MD} 並照做；"
            "白名單外的動作或需要人決定的事一律停下、寫進報告，不要等人回答。\n"
            "今天的執行背景（由 daily.py 準備）：\n```json\n"
            + json.dumps(ctx, ensure_ascii=False, indent=2) + "\n```\n")


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
        return None, f"沒有 blog repo（{cfg.blog}），改上網查官方 changelog"
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
    return None, (note + "；" if note else "") + f"今天沒有 tech-snapshot（{snap.name}），改上網查官方 changelog"


def last_daily(out: Path, today: str):
    olds = sorted(p.name for p in out.glob("*-daily.md") if p.name < f"{today}-daily.md")
    return olds[-1][:10] if olds else None


def run(args):
    cfg = Config.from_env()
    today = date.today().isoformat()
    report = cfg.out / f"{today}-daily.md"
    if report.exists():
        print(f"今天已跑過：{report}")
        return 0
    (cfg.out / "logs").mkdir(parents=True, exist_ok=True)
    logfile = cfg.out / "logs" / f"{today}-daily.log"

    def log(msg):
        with logfile.open("a", encoding="utf-8") as fh:
            fh.write(msg.rstrip() + "\n")

    try:
        prepare_worktree(cfg)
        pending = radar_branches(cfg.repo, unmerged=True)
        before = set(radar_branches(cfg.repo))
        snapshot, blog_note = pull_blog(cfg, today, args.no_pull, log)
        profile = refresh_profile(cfg, log)
        backlog = cfg.out / "adoption-backlog.md"
        full = len(pending) >= MAX_PENDING
        cands = []
        if not full and backlog.exists():
            cands = [asdict(c) for c in candidates(backlog.read_text(encoding="utf-8"), branch_numbers(before))]
            for c in cands:
                c.pop("note")
        ctx = {"date": today, "report": str(report), "out_dir": str(cfg.out), "backlog": str(backlog),
               "backlog_rules": str(BACKLOG_RULES), "work_profile": str(profile), "worktree": str(cfg.worktree), "main_repo": str(cfg.repo),
               "pending_drafts": pending, "drafts_full": full, "max_pending": MAX_PENDING,
               "candidates": cands, "tech_snapshot": snapshot, "blog_note": blog_note,
               "last_daily_report": last_daily(cfg.out, today)}
        log(f"== {today} context ==\n{json.dumps(ctx, ensure_ascii=False, indent=2)}")
        with logfile.open("a", encoding="utf-8") as fh:
            try:
                r = subprocess.run(claude_cmd(cfg, build_prompt(ctx)), cwd=cfg.worktree, stdout=fh,
                                   stderr=subprocess.STDOUT, timeout=CLAUDE_TIMEOUT)
            except subprocess.TimeoutExpired:
                raise Fail(f"claude 超過 {CLAUDE_TIMEOUT // 60} 分鐘沒結束")
        new = sorted(set(radar_branches(cfg.repo)) - before)
        if not report.exists():
            raise Fail(f"claude 結束（exit {r.returncode}）但沒有產出報告")
        post = []
        for b in new:
            v = subprocess.run([sys.executable, str(Path("scripts", "ci", "validate.py"))], cwd=cfg.worktree,
                               capture_output=True, text=True, encoding="utf-8")
            tail = "\n".join((v.stdout + v.stderr).strip().splitlines()[-15:])
            post.append(f"### `{b}` 的 validate.py：{'通過' if v.returncode == 0 else '失敗'}\n\n```\n{tail}\n```\n")
        dirty = git(cfg.worktree, "status", "--porcelain")
        if dirty:
            post.append(f"### ⚠ worktree 留有未 commit 的改動（沒有丟棄，請手動處理）\n\n```\n{dirty}\n```\n")
        else:
            git(cfg.worktree, "switch", "--detach", "main")  # 讓 radar branch 能在主 checkout 切過去審
        if post:
            with report.open("a", encoding="utf-8") as fh:
                fh.write("\n## 收尾檢查（daily.py）\n\n" + "\n".join(post))
        if r.returncode != 0 or dirty:
            raise Fail(f"claude exit {r.returncode}" + ("、worktree 有殘留改動" if dirty else "") + f"，看 {report.name}")
        if new:
            notify(f"新草稿 {', '.join(new)} 待審，看 {report.name}", not args.no_notify)
        elif full:
            notify(f"待審草稿已滿 {MAX_PENDING} 個，先審再出新草稿", not args.no_notify)
        log("done")
        return 0
    except Fail as e:
        log(f"FAIL: {e}")
        notify(f"執行失敗：{e}", not args.no_notify)
        return 1
    except Exception as e:  # 任何意外都要通知，不能靜默失敗
        log(f"ERROR: {e!r}")
        notify(f"執行失敗（{type(e).__name__}），看 logs/{logfile.name}", not args.no_notify)
        raise


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
