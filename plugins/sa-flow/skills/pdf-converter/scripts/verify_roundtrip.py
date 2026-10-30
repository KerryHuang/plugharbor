# -*- coding: utf-8 -*-
"""回轉驗證器 — pdf-converter skill 的確定性驗證階段。

Word 模式（docx → PDF 回轉，三軸比對）：
  python verify_roundtrip.py word --original a.pdf --docx b.docx --outdir verify/
  python verify_roundtrip.py word ... --text-mode report-only   # 範本模式（{佔位符}與原值不同屬預期）

Excel 模式（逐儲存格值比對）：
  python verify_roundtrip.py excel --layout layout.json --xlsx b.xlsx --outdir verify/

門檻（見 references/verify-thresholds.md）：
  文字一致率 100%（硬）；版面座標偏差 ≤2mm、視覺差異率 <3%（軟，超標交 reviewer 判定）。
"""
import argparse
import difflib
import json
import re
import sys
from pathlib import Path

import fitz
import numpy as np

PT_TO_MM = 25.4 / 72.0
TEXT_HARD = 1.0
OFFSET_SOFT_MM = 2.0
VISUAL_SOFT = 0.03
PIXEL_DIFF_THRESHOLD = 40  # 灰階差 > 此值視為相異像素
DOWNSAMPLE = 4  # 比對前降採樣倍率：150dpi ÷ 4 ≈ 0.68mm 粒度，容忍 1~2px 渲染微移（與版面軸 2mm 容差同級）


def docx_to_pdf(docx_path: str, pdf_out: str):
    import win32com.client
    word = win32com.client.Dispatch("Word.Application")
    word.Visible = False
    try:
        doc = word.Documents.Open(str(Path(docx_path).resolve()))
        doc.ExportAsFixedFormat(str(Path(pdf_out).resolve()), 17)  # 17 = wdExportFormatPDF
        doc.Close(False)
    finally:
        word.Quit()


def norm_text(s: str) -> str:
    return re.sub(r"\s+", "", s)


def pdf_text(doc: fitz.Document) -> str:
    return norm_text("".join(p.get_text("text") for p in doc))


def compare_text(orig: fitz.Document, rt: fitz.Document) -> dict:
    a, b = pdf_text(orig), pdf_text(rt)
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    missing, extra = [], []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("delete", "replace"):
            missing.append(a[i1:i2])
        if tag in ("insert", "replace"):
            extra.append(b[j1:j2])
    ratio = sm.ratio()
    return {
        "orig_chars": len(a), "roundtrip_chars": len(b),
        "ratio": round(ratio, 4),
        "missing": missing[:50], "extra": extra[:50],
        "pass": ratio >= TEXT_HARD,
    }


def page_spans(page: fitz.Page) -> list:
    out = []
    for b in page.get_text("dict")["blocks"]:
        if b["type"] != 0:
            continue
        for line in b["lines"]:
            for span in line["spans"]:
                raw = span["text"]
                if not raw.strip():
                    continue
                # 前導/尾隨空白依等寬近似自 bbox 修剪，避免「含空白 span vs 純文字 span」
                # 配對時中心點假偏移（右對齊數值欄常見）
                x0, y0, x1, y1 = span["bbox"]
                n = len(raw)
                lead = n - len(raw.lstrip())
                trail = n - len(raw.rstrip())
                if n and (lead or trail):
                    cw = (x1 - x0) / n
                    x0 += lead * cw
                    x1 -= trail * cw
                out.append((norm_text(raw), (x0, y0, x1, y1)))
    return out


def compare_layout(orig: fitz.Document, rt: fitz.Document) -> dict:
    """以「頁內唯一文字」為錨點比對 span 中心點偏差（mm）。"""
    page_pairs = min(len(orig), len(rt))
    offsets = []
    per_page = []
    for i in range(page_pairs):
        a, b = page_spans(orig[i]), page_spans(rt[i])
        a_map, b_map = {}, {}
        for txt, bbox in a:
            a_map[txt] = None if txt in a_map else bbox  # 重複文字剔除
        for txt, bbox in b:
            b_map[txt] = None if txt in b_map else bbox
        matched, page_off = 0, []
        for txt, bbox in a_map.items():
            if bbox is None or b_map.get(txt) is None:
                continue
            bb = b_map[txt]
            dx = ((bbox[0] + bbox[2]) - (bb[0] + bb[2])) / 2 * PT_TO_MM
            dy = ((bbox[1] + bbox[3]) - (bb[1] + bb[3])) / 2 * PT_TO_MM
            off = (dx * dx + dy * dy) ** 0.5
            page_off.append(off)
            matched += 1
        offsets.extend(page_off)
        per_page.append({"page": i + 1, "anchors": matched,
                         "max_offset_mm": round(max(page_off), 2) if page_off else None})
    max_off = round(max(offsets), 2) if offsets else None
    mean_off = round(sum(offsets) / len(offsets), 2) if offsets else None
    return {
        "page_count_match": len(orig) == len(rt),
        "orig_pages": len(orig), "roundtrip_pages": len(rt),
        "anchor_count": len(offsets),
        "max_offset_mm": max_off, "mean_offset_mm": mean_off,
        "per_page": per_page,
        "pass": len(orig) == len(rt) and (max_off is None or max_off <= OFFSET_SOFT_MM),
    }


def compare_visual(orig: fitz.Document, rt: fitz.Document, outdir: Path, dpi: int) -> dict:
    per_page = []
    for i in range(min(len(orig), len(rt))):
        pa = orig[i].get_pixmap(dpi=dpi)
        pb = rt[i].get_pixmap(dpi=dpi)
        ia = np.frombuffer(pa.samples, dtype=np.uint8).reshape(pa.h, pa.w, pa.n)[:, :, :3]
        ib = np.frombuffer(pb.samples, dtype=np.uint8).reshape(pb.h, pb.w, pb.n)[:, :, :3]
        h, w = max(ia.shape[0], ib.shape[0]), max(ia.shape[1], ib.shape[1])
        ca = np.full((h, w, 3), 255, np.uint8); ca[:ia.shape[0], :ia.shape[1]] = ia
        cb = np.full((h, w, 3), 255, np.uint8); cb[:ib.shape[0], :ib.shape[1]] = ib
        ga = ca.mean(axis=2); gb = cb.mean(axis=2)
        # 降採樣（box 平均）後比對：量的是版面級一致性，不罰渲染 hinting 的 1px 微移
        s = DOWNSAMPLE
        hh, ww = (ga.shape[0] // s) * s, (ga.shape[1] // s) * s
        da = ga[:hh, :ww].reshape(hh // s, s, ww // s, s).mean(axis=(1, 3))
        db = gb[:hh, :ww].reshape(hh // s, s, ww // s, s).mean(axis=(1, 3))
        diff_small = np.abs(da - db) > PIXEL_DIFF_THRESHOLD
        content_small = (da < 250) | (db < 250)  # 只以有內容的區域為分母
        denom = int(content_small.sum()) or 1
        ratio = float(diff_small.sum()) / denom
        diff_mask = np.kron(diff_small, np.ones((s, s), dtype=bool))
        full_mask = np.zeros(ga.shape, dtype=bool)
        full_mask[:diff_mask.shape[0], :diff_mask.shape[1]] = diff_mask
        overlay = ca.copy()
        overlay[full_mask] = [255, 0, 0]
        from PIL import Image
        f = outdir / f"diff_page{i + 1}.png"
        Image.fromarray(overlay).save(str(f))
        per_page.append({"page": i + 1, "diff_ratio": round(ratio, 4),
                         "diff_png": str(f)})
    worst = max((p["diff_ratio"] for p in per_page), default=0.0)
    return {"per_page": per_page, "worst_diff_ratio": worst,
            "pass": worst < VISUAL_SOFT}


def run_word(args) -> dict:
    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)
    rt_pdf = outdir / (Path(args.docx).stem + "_roundtrip.pdf")
    docx_to_pdf(args.docx, str(rt_pdf))
    orig, rt = fitz.open(args.original), fitz.open(str(rt_pdf))
    text = compare_text(orig, rt)
    if args.text_mode == "report-only":
        text["pass"] = None  # 範本模式：僅回報不判定
    layout = compare_layout(orig, rt)
    visual = compare_visual(orig, rt, outdir, args.dpi)
    hard_ok = text["pass"] is not False
    soft_ok = layout["pass"] and visual["pass"]
    return {
        "mode": "word", "roundtrip_pdf": str(rt_pdf),
        "text": text, "layout": layout, "visual": visual,
        "verdict": "pass" if hard_ok and soft_ok
                   else ("soft_fail" if hard_ok else "hard_fail"),
    }


def run_excel(args) -> dict:
    import openpyxl
    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)
    layout = json.loads(Path(args.layout).read_text(encoding="utf-8"))
    wb = openpyxl.load_workbook(args.xlsx, data_only=False)
    xlsx_cells = set()
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for c in row:
                if c.value is not None and str(c.value).strip():
                    xlsx_cells.add(norm_text(str(c.value)))
    expected, missing = [], []
    for pg in layout["pages"]:
        for t in pg["tables"]:
            for cell in t["cells"]:
                if cell["text"]:
                    expected.append(cell["text"])
    for txt in expected:
        n = norm_text(txt)
        if n and not any(n in x or x in n for x in xlsx_cells):
            missing.append(txt)
    total = len([t for t in expected if norm_text(t)])
    ok = len(missing) == 0
    return {
        "mode": "excel", "expected_cells": total,
        "missing": missing[:100], "missing_count": len(missing),
        "verdict": "pass" if ok else "hard_fail",
    }


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("word")
    w.add_argument("--original", required=True)
    w.add_argument("--docx", required=True)
    w.add_argument("--outdir", required=True)
    w.add_argument("--dpi", type=int, default=150)
    w.add_argument("--text-mode", choices=["strict", "report-only"], default="strict")
    e = sub.add_parser("excel")
    e.add_argument("--layout", required=True)
    e.add_argument("--xlsx", required=True)
    e.add_argument("--outdir", required=True)
    args = ap.parse_args()

    report = run_word(args) if args.cmd == "word" else run_excel(args)
    out = Path(args.outdir) / "verify-report.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"report": str(out), "verdict": report["verdict"],
                      **{k: report[k].get("pass") for k in ("text", "layout", "visual")
                         if isinstance(report.get(k), dict)}},
                     ensure_ascii=False))
    sys.exit(0 if report["verdict"] == "pass" else 1)


if __name__ == "__main__":
    main()
