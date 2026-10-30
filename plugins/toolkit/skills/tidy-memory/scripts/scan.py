"""掃描 auto-memory 目錄，輸出結構事實與待查證訊號（JSON）。

只陳述事實，不下判斷：過時與重複由呼叫端查證後決定。
用法：python scan.py <memory_dir>
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field, asdict
from pathlib import Path

INDEX_NAME = "MEMORY.md"
# 分層後的查詢型索引（不自動載入）。兩份都是索引，都不算 memory 檔。
INDEX_NAMES = (INDEX_NAME, "INDEX-reference.md")
INDEX_ENTRY = re.compile(r"^- \[([^\]]+)\]\(([^)]+\.md)\)", re.MULTILINE)
WIKILINK = re.compile(r"\[\[([^\]]+)\]\]")
FM_NAME = re.compile(r"^name:\s*(.+)$", re.MULTILINE)
FM_DESC = re.compile(r"^description:\s*(.+)$", re.MULTILINE)
FM_TYPE = re.compile(r"^\s*type:\s*(.+)$", re.MULTILINE)
# depends_on：本 skill 自定欄位（非官方 schema），記該則記憶的有效性繫於哪些外部可查之物。
FM_DEPENDS = re.compile(r"^\s*depends_on:\s*\[(.*?)\]\s*$", re.MULTILINE)
# originSessionId：harness 寫入，官方文件未規範。可讀不可依賴，缺值時一律歸 "(unknown)"。
FM_SESSION = re.compile(r"^\s*originSessionId:\s*(.+)$", re.MULTILINE)

VALID_TYPES = {"user", "feedback", "project", "reference"}

# 需要外部查證才能判定是否過時的訊號。命中不代表過時。
SIGNAL_PATTERNS: dict[str, re.Pattern[str]] = {
    "ticket": re.compile(r"\b(?:PM|MP|QA|FEAT)-\d+\b"),
    "pending": re.compile(r"未 ?commit|未 ?push|尚未|待做|待辦|進行中|下一棒|未完"),
    "version": re.compile(r"\bv\d+\.\d+|\.NET \d|EF Core"),
    "date": re.compile(r"20\d{2}-\d{2}-\d{2}"),
}


@dataclass
class FileInfo:
    file: str
    name: str | None = None
    description: str | None = None
    type: str | None = None
    issues: list[str] = field(default_factory=list)
    signals: dict[str, list[str]] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)
    origin_session: str = "(unknown)"
    links_to: list[str] = field(default_factory=list)


def parse_file(path: Path) -> FileInfo:
    text = path.read_text(encoding="utf-8")
    info = FileInfo(file=path.name)

    for regex, attr in ((FM_NAME, "name"), (FM_DESC, "description"), (FM_TYPE, "type")):
        match = regex.search(text)
        if match:
            setattr(info, attr, match.group(1).strip())

    # name 不檢查：檔名才是權威識別（wikilink 指向檔名），且 harness 會把 name 正規化成 ""。
    if not info.description:
        info.issues.append("frontmatter 缺 description")
    if info.type and info.type not in VALID_TYPES:
        info.issues.append(f"type '{info.type}' 不在 {sorted(VALID_TYPES)}")
    elif not info.type:
        info.issues.append("frontmatter 缺 metadata.type")

    depends_match = FM_DEPENDS.search(text)
    if depends_match:
        info.depends_on = [
            item.strip().strip('"').strip("'")
            for item in depends_match.group(1).split(",")
            if item.strip()
        ]

    session_match = FM_SESSION.search(text)
    if session_match:
        info.origin_session = session_match.group(1).strip().strip('"').strip("'")

    for label, regex in SIGNAL_PATTERNS.items():
        hits = sorted(set(regex.findall(text)))
        if hits:
            info.signals[label] = hits[:8]

    info.links_to = sorted(set(WIKILINK.findall(text)))
    return info


def main(argv: list[str]) -> int:
    # Windows 主控台預設 cp950，記憶檔含全形符號會炸
    sys.stdout.reconfigure(encoding="utf-8")

    if len(argv) != 2:
        print("用法：python scan.py <memory_dir>", file=sys.stderr)
        return 2

    root = Path(argv[1])
    if not root.is_dir():
        print(f"目錄不存在：{root}", file=sys.stderr)
        return 2

    index_entries = []
    for name in INDEX_NAMES:
        index_path = root / name
        if index_path.exists():
            index_entries += INDEX_ENTRY.findall(index_path.read_text(encoding="utf-8"))
    indexed = {target for _, target in index_entries}

    files = sorted(p for p in root.glob("*.md") if p.name not in INDEX_NAMES)
    infos = [parse_file(p) for p in files]
    stems = {p.stem for p in files}  # wikilink 以檔名為準
    present = {p.name for p in files}

    report = {
        "memory_dir": str(root),
        "counts": {"files": len(files), "index_entries": len(index_entries)},
        "index_missing_file": sorted(indexed - present),
        "orphan_files": sorted(present - indexed),
        "duplicate_index_entries": sorted(
            t for t, n in Counter(t for _, t in index_entries).items() if n > 1
        ),
        "dangling_wikilinks": sorted(
            {link for i in infos for link in i.links_to if link not in stems}
        ),
        # session → 該 session 建立的檔名。供 --session 過濾與「這輪做了什麼」查詢。
        "sessions": {
            sid: sorted(i.file for i in infos if i.origin_session == sid)
            for sid in sorted({i.origin_session for i in infos})
        },
        "files": [asdict(i) for i in infos],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
