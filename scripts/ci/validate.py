#!/usr/bin/env python3
"""marketplace 內容驗證：CI 與 pre-commit 共用。只用標準函式庫。

檢查項目：
  1. 版號一致：plugin.json ＝ marketplace.json ＝ 根 README 版本欄 ＝ CHANGELOG 最新條目
  2. frontmatter：skill／agent 必有 name、description；description 不得用 `|` 區塊
  3. 交互引用：references／templates／scripts／agents 路徑與 `<plugin>:<skill>` 指向實際存在
  4. README 清單：根 README「skills 與 agents」表與實際目錄一致
  5. 外洩掃描：個人路徑、非範例 email、CGNAT（Tailscale）IP；
     另讀 repo 根目錄 `.leak-denylist`（gitignored，只存在本機）逐行比對

用法：python3 scripts/ci/validate.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLUGINS = ROOT / "plugins"
TEXT_EXT = {".md", ".py", ".sh", ".js", ".css", ".json", ".yml", ".yaml", ".txt"}
REF_DIRS = ("references", "templates", "scripts", "agents")
REF_EXT = (".md", ".py", ".sh", ".js", ".css", ".docx", ".json")
# plugin 內的 docs/ 是設計決策紀錄，保留當時的名稱，不檢查 skill 引用
REF_EXEMPT_DIRS = ("docs",)
PLACEHOLDER_STEM = re.compile(r"^(x+|foo|bar|example|sample)$", re.I)
# 已知且已在文件中說明的缺檔：{plugin 目錄: {檔名}}，每筆要附理由
KNOWN_MISSING = {
    # ui-ux-pro-max 的 CLI 與資料庫刻意未納入，README 與 SKILL.md 已註明 fallback
    "ui-ux": {"search.py"},
    # reviewer agent 內文的 YAML 範例路徑（示意用，不是真檔）
    "toolkit": {"checklist.md", "my-agent.md"},
}

errors: list[str] = []


def err(path: Path | str, msg: str) -> None:
    rel = path.relative_to(ROOT) if isinstance(path, Path) else path
    errors.append(f"{rel}: {msg}")


def text_files(base: Path):
    for f in sorted(base.rglob("*")):
        if f.is_file() and f.suffix in TEXT_EXT and ".git" not in f.parts and "__pycache__" not in f.parts:
            yield f


def frontmatter(f: Path) -> dict[str, str] | None:
    lines = f.read_text(encoding="utf-8").split("\n")
    if not lines or lines[0].strip() != "---":
        return None
    fm = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return fm
        m = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
        if m:
            fm[m.group(1)] = m.group(2).strip()
    return None


# ---------- 1. 版號一致 ----------

def check_versions(market: dict, readme: str) -> None:
    for entry in market["plugins"]:
        name, ver = entry["name"], entry.get("version")
        pdir = ROOT / entry["source"]
        pj = pdir / ".claude-plugin" / "plugin.json"
        if not pj.exists():
            err(".claude-plugin/marketplace.json", f"{name} 的 source 找不到 plugin.json")
            continue
        pver = json.loads(pj.read_text(encoding="utf-8")).get("version")
        if pver != ver:
            err(pj, f"version {pver} ≠ marketplace.json 的 {ver}")
        row = re.search(rf"^\|\s*\[{re.escape(name)}\]\([^)]*\)\s*\|\s*([^|]+?)\s*\|", readme, re.M)
        if not row:
            err("README.md", f"版本表缺 {name}")
        elif row.group(1) != pver:
            err("README.md", f"{name} 版本欄 {row.group(1)} ≠ plugin.json 的 {pver}")
        cl = pdir / "CHANGELOG.md"
        if not cl.exists():
            err(pdir, "缺 CHANGELOG.md")
            continue
        top = re.search(r"^## \[([^\]]+)\] - \d{4}-\d{2}-\d{2}", cl.read_text(encoding="utf-8"), re.M)
        if not top:
            err(cl, "找不到 `## [x.y.z] - yyyy-mm-dd` 格式的條目")
        elif top.group(1) != pver:
            err(cl, f"最新條目 {top.group(1)} ≠ plugin.json 的 {pver}（升版要同步補 CHANGELOG）")


# ---------- 2. frontmatter ----------

def check_frontmatter(pdir: Path) -> None:
    targets = [(f, "skill") for f in sorted(pdir.glob("skills/*/SKILL.md"))]
    targets += [(f, "agent") for f in sorted(pdir.glob("agents/*.md"))]
    for d in sorted(p for p in pdir.glob("skills/*") if p.is_dir()):
        if not (d / "SKILL.md").exists():
            err(d, "skill 目錄缺 SKILL.md")
    for f, kind in targets:
        fm = frontmatter(f)
        if fm is None:
            err(f, "缺 frontmatter")
            continue
        for key in ("name", "description"):
            if not fm.get(key):
                err(f, f"frontmatter 缺 `{key}`")
        if fm.get("description", "").startswith("|"):
            err(f, "description 不得用 `|` 區塊（會保留換行、破壞清單呈現），改用 `>-` 或單行")
        expect = f.parent.name if kind == "skill" else f.stem
        if fm.get("name") and fm["name"] != expect:
            err(f, f"name `{fm['name']}` 與檔名／目錄名 `{expect}` 不一致")


# ---------- 3. 交互引用 ----------

TOKEN = re.compile(r"[^\s`'\"()\[\]<>|，。、；：「」（）]+")


def resolve_ref(token: str, f: Path, pdir: Path) -> list[Path] | None:
    """回傳候選路徑；不是本 plugin 的引用（或是佔位）回 None。"""
    if any(c in token for c in "{}*<>$") and not token.startswith(("${CLAUDE_PLUGIN_ROOT}/", "${CLAUDE_SKILL_DIR}/")):
        return None
    skill_dir = next((a for a in f.parents if a.parent.name == "skills"), None)
    if token.startswith("${CLAUDE_PLUGIN_ROOT}/"):
        return [pdir / token.split("/", 1)[1]]
    if token.startswith("${CLAUDE_SKILL_DIR}/"):
        return [skill_dir / token.split("/", 1)[1]] if skill_dir else None
    if token.startswith("../"):
        return [(f.parent / token).resolve()]
    if token.startswith(REF_DIRS) or token.startswith("skills/"):
        cands = [pdir / token, f.parent / token]
        if skill_dir:
            cands.append(skill_dir / token)
        return cands
    return None


def check_refs(pdir: Path, all_plugins: dict[str, set[str]]) -> None:
    prefix_re = re.compile(rf"(?<![\w/-])({'|'.join(map(re.escape, all_plugins))}):([a-z][a-z0-9-]*)")
    for f in text_files(pdir):
        rel_parts = f.relative_to(pdir).parts
        if rel_parts[0] in REF_EXEMPT_DIRS:
            continue
        text = f.read_text(encoding="utf-8", errors="ignore")
        for token in TOKEN.findall(text):
            token = token.rstrip(".,;:")
            if not token.endswith(REF_EXT) or not any(f"{d}/" in token for d in REF_DIRS):
                continue
            if PLACEHOLDER_STEM.match(Path(token).stem):
                continue
            cands = resolve_ref(token, f, pdir)
            if Path(token).name in KNOWN_MISSING.get(pdir.name, set()):
                continue
            if cands is not None and not any(c.exists() for c in cands):
                err(f, f"引用不存在：{token}")
        for m in prefix_re.finditer(text):
            plugin, target = m.groups()
            if target not in all_plugins[plugin]:
                err(f, f"引用不存在的 skill／agent：{plugin}:{target}")


# ---------- 4. README 清單 ----------

def check_catalog(market: dict, readme: str) -> None:
    for entry in market["plugins"]:
        name = entry["name"]
        pdir = ROOT / entry["source"]
        row = re.search(rf"^\|\s*{re.escape(name)}\s*\|([^|]*)\|([^|]*)\|", readme, re.M)
        if not row:
            err("README.md", f"「skills 與 agents」表缺 {name}")
            continue
        listed_s = set(re.findall(r"`([^`]+)`", row.group(1)))
        listed_a = set(re.findall(r"`([^`]+)`", row.group(2)))
        actual_s = {p.name for p in pdir.glob("skills/*") if p.is_dir()}
        actual_a = {p.stem for p in pdir.glob("agents/*.md")}
        for kind, listed, actual in (("skill", listed_s, actual_s), ("agent", listed_a, actual_a)):
            if missing := sorted(actual - listed):
                err("README.md", f"{name} 表格漏列 {kind}：{', '.join(missing)}")
            if extra := sorted(listed - actual):
                err("README.md", f"{name} 表格列了不存在的 {kind}：{', '.join(extra)}")


# ---------- 5. 外洩掃描 ----------

PLACEHOLDER_USERS = {"example", "user", "username", "you", "yourname", "your-username", "me", "john doe", "<user>"}
PERSONAL_PATH = re.compile(r"(?:/Users/|/home/|C:(?:\\\\|\\)Users(?:\\\\|\\))([A-Za-z][\w. -]*?)(?=[\\/\"'`]|$)", re.M)
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
EMAIL_OK = re.compile(r"(@example\.(com|org|net)|@[\w.-]+\.test$|^noreply@|@users\.noreply\.github\.com$|@anthropic\.com$|^git@)", re.I)
CGNAT_IP = re.compile(r"\b100\.(6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d{1,3}\.\d{1,3}\b")


def load_denylist() -> list[re.Pattern]:
    f = ROOT / ".leak-denylist"
    if not f.exists():
        return []
    pats = []
    for line in f.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            pats.append(re.compile(line[6:] if line.startswith("regex:") else re.escape(line), re.I))
    return pats


def check_leaks() -> None:
    deny = load_denylist()
    scan_roots = [ROOT / "plugins", ROOT / "README.md", ROOT / ".claude-plugin", ROOT / ".claude", ROOT / "scripts", ROOT / "setup", ROOT / "docs", ROOT / "CLAUDE.md", ROOT / "AGENTS.md", ROOT / "LICENSE", ROOT / ".github"]
    files = []
    for r in scan_roots:
        files += [r] if r.is_file() else list(text_files(r)) if r.exists() else []
    for f in files:
        if f.name == ".leak-denylist":
            continue
        text = f.read_text(encoding="utf-8", errors="ignore")
        for lineno, line in enumerate(text.split("\n"), 1):
            for m in PERSONAL_PATH.finditer(line):
                if m.group(1).strip().lower() not in PLACEHOLDER_USERS:
                    err(f, f"L{lineno} 個人路徑：{m.group(0)}")
            for m in EMAIL.finditer(line):
                if not EMAIL_OK.search(m.group(0)):
                    err(f, f"L{lineno} 非範例 email：{m.group(0)}")
            if m := CGNAT_IP.search(line):
                err(f, f"L{lineno} 內網（CGNAT／Tailscale）IP：{m.group(0)}")
            for p in deny:
                if m := p.search(line):
                    err(f, f"L{lineno} 命中本機黑名單：{m.group(0)}")


def main() -> int:
    market = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    all_plugins = {}
    for entry in market["plugins"]:
        pdir = ROOT / entry["source"]
        all_plugins[entry["name"]] = {p.name for p in pdir.glob("skills/*") if p.is_dir()} | {
            p.stem for p in pdir.glob("agents/*.md")}

    check_versions(market, readme)
    check_catalog(market, readme)
    for entry in market["plugins"]:
        pdir = ROOT / entry["source"]
        check_frontmatter(pdir)
        check_refs(pdir, all_plugins)
    check_leaks()

    if errors:
        uniq = list(dict.fromkeys(errors))
        print(f"✗ {len(uniq)} 個問題：")
        for e in uniq:
            print(f"  - {e}")
        return 1
    print(f"✓ {len(market['plugins'])} 個 plugin 驗證通過")
    return 0


if __name__ == "__main__":
    sys.exit(main())
