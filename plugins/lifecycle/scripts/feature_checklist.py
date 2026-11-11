#!/usr/bin/env python3
"""功能清單（feature-checklist.md）統計：算各節與總計、列待確認與未分類，--write 改寫數字行。

用法：
  python3 feature_checklist.py [路徑]           # 印報表（預設 docs/feature-checklist.md）
  python3 feature_checklist.py [路徑] --write   # 改寫檔頭「總計：」行與各節「完成 X／共 Y。」小計
  python3 feature_checklist.py [路徑] --check   # 數字行過期就 exit 1（可放 pre-commit）
  python3 feature_checklist.py [路徑] --open    # 未完成項目分「可開工」「依序等待」「被擋」「未排段」四區，排線用；路徑給 - 讀 stdin
  roadmap：預設讀清單同目錄的 roadmap.md（或 ROADMAP.md），檔頭「Roadmap：[名稱](相對路徑)」或 --roadmap <檔> 可覆寫；讀其段表（欄位含「工作段」「狀態」，列序＝順序），
  可開工只取第一個未完成段（含之前）的項目、沒段號與 💡 歸未排段、段號阻擋依段狀態判斷，報表與 --check 另比對清單勾選與段狀態。

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
SEGMENT = re.compile(r"（段 ([^）\s]+)）")
ROADMAP_LINK = re.compile(r"^Roadmap：\[[^\]]*\]\(([^)#]+)", re.M)
BLOCKED = re.compile(r"⛔ 等：([^。（]+)")
DONE_STATUS = ("已上線", "已完成", "完成")
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


def item_name(rest):
    for emoji in LABELS:
        rest = rest.removeprefix(emoji)
    return SEGMENT.sub("", rest.split(" — ")[0]).strip()


def items(text):
    out, section = [], None
    for line in text.splitlines():
        if line.startswith("## "):
            section = line[3:].strip()
            continue
        m = ITEM.match(line)
        if not m:
            continue
        seg = SEGMENT.search(line)
        blk = BLOCKED.search(line)
        out.append({"line": line.strip(), "section": section, "name": item_name(m.group(2)),
                    "done": m.group(1) in "xX", "open": m.group(1) == " ",
                    "idea": m.group(2).startswith("💡"),
                    "segment": seg.group(1) if seg else None,
                    "blockers": [b.strip() for b in blk.group(1).split("、") if b.strip()] if blk else []})
    return out


def parse_roadmap(text):
    """markdown 表格中表頭含「工作段」與「狀態」者；回傳 {段號: (列序, 狀態)}，跨表依出現順序。
    同一格的多個段號共用列序；重複段號記在 "_dups"。"""
    segs, dups, cols, row = {}, [], None, 0
    for line in text.splitlines():
        if not line.strip().startswith("|"):
            cols = None
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cols is None:
            cols = (cells.index("工作段"), cells.index("狀態")) if "工作段" in cells and "狀態" in cells else ()
            continue
        if not cols or set("".join(cells)) <= set("-: "):
            continue
        for seg in re.split(r"[、,，\s]+", cells[cols[0]]):
            if seg in segs:
                dups.append(seg)
            elif seg:
                segs[seg] = (row, cells[cols[1]])
        row += 1
    segs["_dups"] = dups
    return segs


def seg_done(status):
    return status.startswith(DONE_STATUS)


def blocker_state(b, by_name, roadmap):
    """回傳 'open'（仍擋）、'resolved'（可解除）或 'unknown'（找不到目標，仍擋）。"""
    if b.startswith("裁決"):
        return "open"
    if b in by_name:
        return "resolved" if by_name[b]["done"] else "open"
    if roadmap is not None:
        if b in roadmap:
            return "resolved" if seg_done(roadmap[b][1]) else "open"
        return "unknown"
    return "open"


def deps(text, roadmap=None):
    """阻擋與同步問題：可解除的阻擋、找不到的目標、清單勾選與 roadmap 段狀態不一致。"""
    its = items(text)
    by_name = {i["name"]: i for i in its}
    resolved, unknown, drift = [], [], []
    if roadmap is not None:
        unknown += [f"roadmap 段號重複：{x}" for x in roadmap["_dups"]]
    for i in its:
        if i["open"]:
            for b in i["blockers"]:
                st = blocker_state(b, by_name, roadmap)
                if st == "resolved":
                    resolved.append(f"{i['name']}：等「{b}」已完成，可刪 ⛔")
                elif st == "unknown":
                    unknown.append(f"{i['name']}：找不到「{b}」（不是清單項名、段號或「裁決 X」）")
        if roadmap is not None and i["segment"]:
            st = roadmap.get(i["segment"])
            if st is None:
                unknown.append(f"{i['name']}：roadmap 沒有段 {i['segment']}")
            elif i["done"] and not seg_done(st[1]):
                drift.append(f"{i['name']}：清單已勾，roadmap 段 {i['segment']} 是「{st[1]}」")
            elif i["open"] and seg_done(st[1]):
                drift.append(f"{i['name']}：roadmap 段 {i['segment']} 是「{st[1]}」，清單未勾")
    return {"resolved": resolved, "unknown": unknown, "drift": drift}


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


def report_deps(d):
    for title, rows in (("可解除的阻擋", d["resolved"]), ("找不到的阻擋目標或段號", d["unknown"]),
                        ("清單與 roadmap 不同步", d["drift"])):
        if rows:
            print(f"{title} {len(rows)} 項：")
            for x in rows:
                print(f"  {x}")


def open_items(text, roadmap=None):
    """未完成項目分四區：可開工（roadmap 第一個未完成段及之前的段；沒 roadmap 時為全部非 💡）、
    依序等待（更後面的段）、被擋（附仍在等的目標）、未排段（沒段號或段號不在 roadmap，以及 💡）。"""
    its = items(text)
    by_name = {i["name"]: i for i in its}
    rows = [v for k, v in (roadmap or {}).items() if k != "_dups"]
    current = min((r for r, st in rows if not seg_done(st)), default=None)
    ready, queued, blocked, unplanned = [], [], [], []
    for n, i in enumerate(x for x in its if x["open"]):
        still = [b for b in i["blockers"] if blocker_state(b, by_name, roadmap) != "resolved"]
        if still:
            blocked.append(f"{i['line']}\n    ← 等：{'、'.join(still)}")
            continue
        line = f"{i['line']}［{i['section']}］" if i["section"] else i["line"]
        seg = roadmap.get(i["segment"]) if roadmap and i["segment"] else None
        if i["idea"] or (roadmap is not None and seg is None):
            unplanned.append(line)
        elif seg is None:
            ready.append((n, n, line))
        elif current is None or seg[0] <= current:
            ready.append((seg[0], n, line))
        else:
            queued.append((seg[0], n, line))
    out = ["## 可開工", ""] + [x for *_, x in sorted(ready)]
    for title, rows_ in (("依序等待", [x for *_, x in sorted(queued)]), ("被擋", blocked),
                         ("未排段（要排程就在 roadmap 加列，可用佔位段號）", unplanned)):
        if rows_:
            out += ["", f"## {title}", ""] + rows_
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("path", nargs="?", default="docs/feature-checklist.md")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--write", action="store_true")
    g.add_argument("--check", action="store_true")
    g.add_argument("--open", action="store_true", help="未完成項目分可開工／被擋（排線用）")
    ap.add_argument("--roadmap", type=Path, help="roadmap 檔：段表欄位含「工作段」「狀態」")
    a = ap.parse_args()
    p = Path(a.path)
    text = sys.stdin.read() if a.path == "-" else p.read_text(encoding="utf-8")
    link = ROADMAP_LINK.search(text)
    rp = a.roadmap or (p.parent / link.group(1) if link and a.path != "-" else None)
    if rp is None and a.path != "-":
        rp = next((p.parent / n for n in ("roadmap.md", "ROADMAP.md") if (p.parent / n).is_file()), None)
    if rp and not rp.is_file():
        print(f"找不到 roadmap：{rp}", file=sys.stderr)
        return 1
    roadmap = parse_roadmap(rp.read_text(encoding="utf-8")) if rp else None
    if a.open:
        print(open_items(text, roadmap))
        return 0
    report(analyze(text))
    d = deps(text, roadmap)
    report_deps(d)
    if a.write:
        p.write_text(rewrite(text, datetime.date.today().isoformat()), encoding="utf-8")
        print(f"已更新 {p}")
    elif a.check:
        m = DATE.search(text)
        if rewrite(text, m.group(1) if m else "") != text:
            print("數字行過期：執行 --write 更新", file=sys.stderr)
            return 1
        if d["unknown"] or d["drift"]:
            print("阻擋目標找不到，或清單與 roadmap 不同步：見上方清單", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
