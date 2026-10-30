#!/usr/bin/env python3
"""決策傳播比對：decisions.md 的每條 D-xxx 是否已回寫到該出現的規格文件 §D。

用法：
    python3 check-decision-propagation.py <功能目錄> [--json]

規則（任一不成立即列為 CRITICAL，退出碼 1）：
  R1  正文引用了「本階段」D-xxx 的文件，其 §D 決策紀錄必須列出該 D。
      （上游階段的 D 在下游正文被引用是正常的 ref，不算；只抓本階段拍板卻沒進 §D 的）
  R2  decisions.md 中「階段」為 FRD／SAD／BFS／FFS 的 D，必須出現在該階段文件的 §D。
  R3  「階段」為 dev-readiness／verifying-specs／CR 的 D（回寫型決策），
      必須出現在至少一份規格文件的 §D——回寫了正文卻沒列 §D 是最常見的漏。
  R4  decisions.md 的 D 編號必須連號無斷、無重號。
  R5  decisions.md「狀態」為暫定的 D，在規格正文每次引用都要寫成「（暫定，D-xxx 待確認）」；
      狀態為定案的 D，正文不得殘留這個暫定標記。decisions.md 沒有「狀態」欄（舊鏈）時整條跳過。
  R6  文件資訊表的「| 版本 | x.y |」必須等於檔尾 <!-- CHANGELOG --> 表的最高版本。
      任一邊找不到就跳過該文件。

不做的事：不比對決策內容是否被正確落實（那是 verifying-specs 各維度 agent 的工作），
只比對「編號有沒有傳播」。這是機械閘門，不是語意檢查。

緣起：立下「決策回寫的掃描義務」後，某案 verifying-specs --cross
首輪 9 CRITICAL 仍有 7 筆屬「BFS 階段決策未回寫 SAD」——
規則寫在散文裡擋不住人，改成腳本。
"""
import json
import re
import sys
from pathlib import Path

# Windows 預設 cp950：印中文會亂碼、印 emoji 直接炸 UnicodeEncodeError。
# 與 parse_foxpro.py 同一做法，腳本自己處理，不靠呼叫端設 PYTHONUTF8。
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

DOC_PATTERNS = {
    "FRD": "*_需求文件.md",
    "SAD": "*_系統分析文件.md",
    "BFS": "*_後端功能規格書.md",
    "FFS": "*_前端功能規格書.md",
}
STAGE_TO_DOC = {
    "frd": "FRD", "requirement": "FRD", "需求": "FRD", "分析": "FRD",
    "sad": "SAD", "system-analysis": "SAD",
    "bfs": "BFS", "specify-backend": "BFS",
    "ffs": "FFS", "specify-frontend": "FFS",
}
WRITEBACK_STAGES = ("dev-readiness", "verifying-specs", "cr", "回寫")
D_RE = re.compile(r"\bD-(\d{3})\b")
PROVISIONAL_RE = re.compile(r"暫定[，,]\s*D-(\d{3})\s*待確認")
CHANGELOG_RE = re.compile(r"<!-- CHANGELOG -->(.*?)<!-- /CHANGELOG -->", re.S)
# 文件資訊表的版本列；CHANGELOG 表頭「| 版本 | Ticket |」不是數字，不會命中
HEADER_VER_RE = re.compile(r"^\|\s*\**版本\**\s*\|\s*v?(\d+(?:\.\d+)*)\s*\|", re.M)
CHANGELOG_VER_RE = re.compile(r"^\|\s*v?(\d+(?:\.\d+)+)\s*\|", re.M)


def find_doc(feature_dir: Path, pattern: str):
    hits = [p for p in feature_dir.glob(pattern) if "附錄" not in p.name]
    return hits[0] if hits else None


def section_d_ids(text: str) -> set:
    """取 `## D.` 決策紀錄章到下一個 `## ` 之間出現的 D 編號。"""
    m = re.search(r"^## D\.[^\n]*\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    if not m:
        return set()
    return set(D_RE.findall(m.group(1)))


def body_text(text: str) -> str:
    """§D 章與 CHANGELOG 以外的全文（含 §0、附錄引用）。挖掉的部分換成等量空行，行號與原檔一致。

    CHANGELOG 只挖到 `<!-- /CHANGELOG -->`：有些規格把它放在檔頭，挖到檔尾會把整份正文一起丟掉。
    """
    blank = lambda m: "\n" * m.group(0).count("\n")
    without_d = re.sub(r"^## D\.[^\n]*\n.*?(?=^## |\Z)", blank, text, flags=re.S | re.M)
    return re.sub(r"<!-- CHANGELOG -->(?:.*?<!-- /CHANGELOG -->|.*)", blank, without_d, flags=re.S)


def body_ids(text: str) -> set:
    return set(D_RE.findall(body_text(text)))


def provisional_gaps(body: str, status_of: dict) -> list:
    """R5：回傳 [(id, 原檔行號, 問題)]。暫定 D 的裸引用、定案 D 殘留的暫定標記。"""
    gaps = []
    for no, line in enumerate(body.splitlines(), 1):
        marked = PROVISIONAL_RE.findall(line)
        for did in set(D_RE.findall(line)):
            status = status_of.get(did)
            if status == "暫定" and D_RE.findall(line).count(did) > marked.count(did):
                gaps.append((did, no, "暫定決策：正文引用未帶「（暫定，D-xxx 待確認）」"))
            elif status == "定案" and did in marked:
                gaps.append((did, no, "已定案：正文仍殘留暫定標記"))
    return gaps


def version_mismatch(text: str):
    """R6：回傳 (文件資訊版本, CHANGELOG 最高版本)；一致或任一邊缺就回 None。"""
    m = CHANGELOG_RE.search(text)
    header = HEADER_VER_RE.search(CHANGELOG_RE.sub("", text))
    if not m or not header:
        return None
    rows = CHANGELOG_VER_RE.findall(m.group(1))
    if not rows:
        return None
    as_tuple = lambda v: tuple(int(x) for x in v.split("."))
    latest = max(rows, key=as_tuple)
    return None if as_tuple(header.group(1)) == as_tuple(latest) else (header.group(1), latest)


def parse_decisions(text: str):
    """回傳 [(id, stage, status)]，只取決策表列（`| D-xxx |` 起頭）。

    欄位位置依表頭定位；沒有表頭時沿用舊順序（# | 決策 | 選定 | 否決 | 依據 | 拍板 | 階段 | 日期）。
    沒有「狀態」欄時 status 為 None（舊鏈，R5 跳過）；有欄但空白視為定案。
    """
    stage_col, status_col = 6, None
    rows = []
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if line.startswith("| #"):
            stage_col = cells.index("階段") if "階段" in cells else stage_col
            status_col = cells.index("狀態") if "狀態" in cells else None
            continue
        if not line.startswith("| D-") or len(cells) <= stage_col:
            continue
        did = cells[0].replace("D-", "")
        status = None
        if status_col is not None:
            raw = cells[status_col] if len(cells) > status_col else ""
            status = "暫定" if raw.startswith("暫定") else "定案"
        rows.append((did, cells[stage_col].lower(), status))
    return rows


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    feature_dir = Path(argv[1]).expanduser().resolve()
    as_json = "--json" in argv
    dec_path = feature_dir / "decisions.md"
    if not dec_path.exists():
        print(f"decisions.md 不存在：{dec_path}")
        return 2

    docs = {}
    for key, pat in DOC_PATTERNS.items():
        p = find_doc(feature_dir, pat)
        if p:
            t = p.read_text(encoding="utf-8")
            docs[key] = {"path": p.name, "sectionD": section_d_ids(t), "body": body_ids(t),
                         "bodyText": body_text(t), "version": version_mismatch(t)}

    decisions = parse_decisions(dec_path.read_text(encoding="utf-8"))
    findings = []

    # R4 連號
    ids = sorted(int(d) for d, _, _ in decisions)
    if ids:
        missing = sorted(set(range(1, ids[-1] + 1)) - set(ids))
        dups = sorted({i for i in ids if ids.count(i) > 1})
        if missing:
            findings.append({"rule": "R4", "id": None, "doc": "decisions.md",
                             "msg": f"D 編號斷號：{['D-%03d' % i for i in missing]}"})
        if dups:
            findings.append({"rule": "R4", "id": None, "doc": "decisions.md",
                             "msg": f"D 編號重號：{['D-%03d' % i for i in dups]}"})

    # R1 本階段引用必列
    stage_of = {did: STAGE_TO_DOC.get(stage) for did, stage, _ in decisions}
    for key, d in docs.items():
        for did in sorted(d["body"] - d["sectionD"]):
            if stage_of.get(did) == key:
                findings.append({"rule": "R1", "id": f"D-{did}", "doc": d["path"],
                                 "msg": "本階段決策：正文引用但 §D 未列"})

    # R2 / R3 階段傳播
    all_section_ids = set().union(*(d["sectionD"] for d in docs.values())) if docs else set()
    for did, stage, _ in decisions:
        target = STAGE_TO_DOC.get(stage)
        if target:
            if target in docs and did not in docs[target]["sectionD"]:
                findings.append({"rule": "R2", "id": f"D-{did}", "doc": docs[target]["path"],
                                 "msg": f"階段={stage} 但該文件 §D 未列"})
        elif any(s in stage for s in WRITEBACK_STAGES):
            if did not in all_section_ids:
                findings.append({"rule": "R3", "id": f"D-{did}", "doc": "（任一規格文件）",
                                 "msg": f"回寫型決策（階段={stage}）未出現在任何文件 §D"})

    # R5 暫定標記（舊鏈沒有狀態欄就跳過）
    status_of = {did: status for did, _, status in decisions if status}
    if status_of:
        for key, d in docs.items():
            for did, no, msg in provisional_gaps(d["bodyText"], status_of):
                findings.append({"rule": "R5", "id": f"D-{did}", "doc": f"{d['path']}（第 {no} 行）",
                                 "msg": msg})

    # R6 文件資訊版本＝CHANGELOG 最高版本
    for key, d in docs.items():
        if d["version"]:
            header, latest = d["version"]
            findings.append({"rule": "R6", "id": None, "doc": d["path"],
                             "msg": f"文件資訊版本 {header} ≠ CHANGELOG 最高版本 {latest}"})

    summary = {"feature_dir": str(feature_dir), "docs": {k: v["path"] for k, v in docs.items()},
               "decisions": len(decisions), "critical": len(findings), "findings": findings}
    if as_json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"決策傳播比對：{feature_dir.name}｜文件 {len(docs)} 份｜決策 {len(decisions)} 條｜CRITICAL {len(findings)}")
        for f in findings:
            print(f"  [{f['rule']}] {f['id'] or '-':<6} {f['doc']}：{f['msg']}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
