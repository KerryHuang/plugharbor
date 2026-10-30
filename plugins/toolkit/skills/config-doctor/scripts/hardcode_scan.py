# config-doctor：掃 skills／rules／設定裡寫死的機器值（唯讀）
# 用法：python hardcode_scan.py <目錄或檔> [...]
# 輸出：FINDING|P2|hardcode:<類別>|<檔>:<行>: <命中字串> 逐行 + SUMMARY JSON。
# 機器值應放 *.local.*（CLAUDE.local.md、settings.local.json）或 .env，這些檔不掃。命中是疑點：範例文字、測試 fixture 要逐筆判定。
from __future__ import annotations
import json
import re
import sys
from collections import Counter
from pathlib import Path

PATTERNS = {
    # 任何使用者的家目錄（不只執行者本人），含 Windows
    "home-path": r"(?:/Users|/home)/[A-Za-z0-9._-]+/|\b[A-Za-z]:\\Users\\[^\\\s]+",
    # 任何磁碟代號的 Windows 絕對路徑，以及 Git Bash 形式 /d/...
    "drive-path": r"\b[A-Za-z]:\\[A-Za-z0-9_]|(?<![\w/.~:-])/[a-z]/[A-Za-z]",
    "tmp-path": r"/private/(?:var|tmp)/|/var/folders/",
    "private-ip": r"\b(?:10\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])|192\.168|100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7]))\.\d{1,3}\.\d{1,3}\b",
    "localhost-port": r"\blocalhost:\d{2,5}\b",
    # 網域最後一段要是字母，排除「套件名@版本號」這類寫法
    "email": r"\b[\w.+-]+@(?!example\.)[\w-]+(?:\.[\w-]+)*\.[A-Za-z]{2,}\b",
}
EMAIL_ALLOW = re.compile(r"^(?:noreply|git)@", re.I)  # git@host 是 remote 位址不是信箱
SUFFIXES = {".md", ".py", ".sh", ".mjs", ".js", ".ts", ".json", ".toml", ".yml", ".yaml"}
SKIP_DIRS = {".git", "node_modules", "__pycache__", "synced", ".venv", "venv", "site-packages"}
RX = {k: re.compile(v) for k, v in PATTERNS.items()}


def skipped(f: Path) -> bool:
    return ".local." in f.name or f.name.startswith(".env") or f.suffix not in SUFFIXES


def files_under(p: Path):
    if p.is_file():
        yield p
        return
    for f in sorted(p.rglob("*")):
        if f.is_file() and not (set(f.parts) & SKIP_DIRS):
            yield f


def scan(paths: list[Path]) -> list[tuple[str, str, int, str]]:
    hits = []
    for root in paths:
        for f in files_under(root):
            if skipped(f):
                continue
            try:
                lines = f.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeDecodeError):
                continue
            for n, line in enumerate(lines, 1):
                for kind, rx in RX.items():
                    for m in rx.finditer(line):
                        if kind == "email" and EMAIL_ALLOW.match(m.group()):
                            continue
                        hits.append((kind, str(f), n, m.group()))
    return hits


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("用法：hardcode_scan.py <目錄或檔> [...]")
    hits = scan([Path(a).expanduser() for a in sys.argv[1:]])
    for kind, f, n, text in hits:
        print(f"FINDING|P2|hardcode:{kind}|{f}:{n}: {text}")
    print("SUMMARY " + json.dumps(Counter(h[0] for h in hits), ensure_ascii=False))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
