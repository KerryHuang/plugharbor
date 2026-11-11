#!/usr/bin/env python3
"""功能清單（feature-checklist.md）統計：算各節與總計、列待確認與未分類，--write 改寫數字行。

用法：
  python3 feature_checklist.py [路徑]           # 印報表（預設 docs/feature-checklist.md）
  python3 feature_checklist.py [路徑] --write   # 改寫檔頭「總計：」行與各節「完成 X／共 Y。」小計
  python3 feature_checklist.py [路徑] --check   # 數字行過期就 exit 1（可放 pre-commit）
  python3 feature_checklist.py [路徑] --open    # 只列未完成項目（依節），排線用；路徑給 - 讀 stdin

格式見 ../references/feature-checklist.md。
"""
import argparse
import datetime
import re
import sys
from pathlib import Path

ITEM = re.compile(r"^\s*- \[([ xX-])\]\s*(.*)$")
SUBTOTAL = re.compile(r"^完成 \d+／共 \d+。")
SUMMARY = re.compile(r"總計：.*$")
DATE = re.compile(r"更新於 (\d{4}-\d{2}-\d{2})。")
LABELS = {"🚧": "doing", "📋": "planned", "💡": "idea"}
KEYS = ("done", "doing", "planned", "idea", "unlabeled", "dropped")


def classify(mark, rest):
    if mark in "xX":
        return "done"
    if mark == "-":
        return "dropped"
    for emoji, key in LABELS.items():
        if rest.startswith(emoji):
            return key
    return "unlabeled"


def empty():
    return dict.fromkeys(KEYS, 0)


def analyze(text):
    sections, total, pending, unlabeled = [], empty(), [], []
    current = None
    for line in text.splitlines():
        if line.startswith("## "):
            current = {"name": line[3:].strip(), "counts": empty()}
            sections.append(current)
            continue
        m = ITEM.match(line)
        if not m:
            continue
        key = classify(m.group(1), m.group(2))
        total[key] += 1
        if current is not None:
            current["counts"][key] += 1
        if "（待確認）" in line:
            pending.append(line.strip())
        if key == "unlabeled":
            unlabeled.append(line.strip())
    for c in [total] + [s["counts"] for s in sections]:
        c["total"] = sum(v for k, v in c.items() if k != "dropped")
    return {"total": total, "sections": sections, "pending": pending, "unlabeled": unlabeled}


def summary_line(r, today):
    t = r["total"]
    parts = f"進行中 {t['doing']}、已規劃 {t['planned']}、構想 {t['idea']}"
    if t["unlabeled"]:
        parts += f"、未分類 {t['unlabeled']}"
    return (f"總計：完成 {t['done']}／共 {t['total']}（另有 {t['dropped']} 項決定不做）；"
            f"{parts}；待確認 {len(r['pending'])} 項。更新於 {today}。")


def rewrite(text, today):
    r = analyze(text)
    by_name = {s["name"]: s["counts"] for s in r["sections"]}
    lines = text.split("\n")
    out, i, seen_summary = [], 0, False
    while i < len(lines):
        line = lines[i]
        if not seen_summary and SUMMARY.search(line):
            out.append(SUMMARY.sub(lambda _: summary_line(r, today), line))
            seen_summary = True
            i += 1
            continue
        out.append(line)
        if line.startswith("# ") and not seen_summary and not any(SUMMARY.search(x) for x in lines):
            out += ["", summary_line(r, today)]
            seen_summary = True
        if line.startswith("## "):
            c = by_name.get(line[3:].strip())
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if c and c["total"]:
                sub = f"完成 {c['done']}／共 {c['total']}。"
                if j < len(lines) and SUBTOTAL.match(lines[j]):
                    out += lines[i + 1:j] + [SUBTOTAL.sub(sub, lines[j])]
                    i = j + 1
                    continue
                out += ["", sub]
        i += 1
    return "\n".join(out)


def report(r):
    t = r["total"]
    print(f"完成 {t['done']}／共 {t['total']}；進行中 {t['doing']}、已規劃 {t['planned']}、"
          f"構想 {t['idea']}、未分類 {t['unlabeled']}；決定不做 {t['dropped']}")
    for s in r["sections"]:
        c = s["counts"]
        if c["total"] + c["dropped"]:
            print(f"  {s['name']}：完成 {c['done']}／共 {c['total']}")
    for title, items in (("待確認", r["pending"]), ("未分類（[ ] 沒標 🚧／📋／💡）", r["unlabeled"])):
        if items:
            print(f"{title} {len(items)} 項：")
            for x in items:
                print(f"  {x}")


def open_items(text):
    """未完成項目（🚧／📋／💡／未分類）依節列出，供排線分類用。"""
    out, header = [], None
    for line in text.splitlines():
        if line.startswith("## "):
            header = line
            continue
        m = ITEM.match(line)
        if m and m.group(1) == " ":
            if header:
                out += ["", header] if out else [header]
                header = None
            out.append(line.strip())
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("path", nargs="?", default="docs/feature-checklist.md")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--write", action="store_true")
    g.add_argument("--check", action="store_true")
    g.add_argument("--open", action="store_true", help="只列未完成項目（排線用）")
    a = ap.parse_args()
    p = Path(a.path)
    text = sys.stdin.read() if a.path == "-" else p.read_text(encoding="utf-8")
    if a.open:
        print(open_items(text))
        return 0
    report(analyze(text))
    if a.write:
        p.write_text(rewrite(text, datetime.date.today().isoformat()), encoding="utf-8")
        print(f"已更新 {p}")
    elif a.check:
        m = DATE.search(text)
        if rewrite(text, m.group(1) if m else "") != text:
            print("數字行過期：執行 --write 更新", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
