# -*- coding: utf-8 -*-
"""PDF 版面萃取器 — pdf-converter skill 的確定性萃取階段。

用法：
  python pdf_extract.py <pdf路徑> --probe                 # 來源盤點（文字層/字型/表格/圖片）
  python pdf_extract.py <pdf路徑> --out layout.json       # 完整萃取 layout.json
  python pdf_extract.py <pdf路徑> --out layout.json --images-dir imgs/  # 併出圖片
  python pdf_extract.py <pdf路徑> --render-dir pages/ --dpi 150         # 頁面渲染成 PNG（掃描檔降級用）

輸出座標單位一律 pt（1pt = 1/72 inch；mm = pt * 25.4 / 72）。
"""
import argparse
import base64
import json
import sys
from pathlib import Path

import fitz  # PyMuPDF

PT_TO_MM = 25.4 / 72.0


def open_doc(path: str) -> fitz.Document:
    doc = fitz.open(path)
    if doc.needs_pass:
        print(json.dumps({"error": "encrypted", "message": "PDF 已加密，請先解密再轉換"},
                         ensure_ascii=False))
        sys.exit(2)
    return doc


def probe(doc: fitz.Document) -> dict:
    pages = []
    fonts = set()
    for page in doc:
        text = page.get_text("text").strip()
        tables = page.find_tables()
        for f in page.get_fonts(full=True):
            fonts.add(f[3])  # basefont name
        pages.append({
            "page": page.number + 1,
            "size_pt": [round(page.rect.width, 2), round(page.rect.height, 2)],
            "rotation": page.rotation,
            "text_chars": len(text),
            "has_text_layer": len(text) >= 10,
            "table_count": len(tables.tables),
            "image_count": len(page.get_images()),
        })
    scanned = [p["page"] for p in pages if not p["has_text_layer"]]
    return {
        "page_count": len(pages),
        "fonts": sorted(fonts),
        "pages": pages,
        "scanned_pages": scanned,
        "verdict": "scanned" if scanned and len(scanned) == len(pages)
                   else ("partial_scanned" if scanned else "text_layer_ok"),
    }


def extract_tables(page: fitz.Page) -> list:
    result = []
    for t in page.find_tables():
        cells = []
        data = t.extract()
        for ri, row in enumerate(t.rows):
            for ci, cell_bbox in enumerate(row.cells):
                if cell_bbox is None:
                    continue
                text = data[ri][ci] if ri < len(data) and ci < len(data[ri]) else None
                cells.append({
                    "row": ri, "col": ci,
                    "bbox": [round(v, 2) for v in cell_bbox],
                    "text": (text or "").strip() if text else "",
                })
        result.append({
            "bbox": [round(v, 2) for v in t.bbox],
            "row_count": t.row_count, "col_count": t.col_count,
            "cells": cells,
        })
    return result


def extract_drawings(page: fitz.Page) -> list:
    """線條/框線摘要：只留有筆畫的水平/垂直線與矩形，供還原邊框樣式。"""
    out = []
    for d in page.get_drawings():
        for item in d["items"]:
            kind = item[0]
            if kind == "l":
                p1, p2 = item[1], item[2]
                if abs(p1.x - p2.x) < 0.5 or abs(p1.y - p2.y) < 0.5:  # 水平或垂直
                    out.append({
                        "type": "line",
                        "from": [round(p1.x, 2), round(p1.y, 2)],
                        "to": [round(p2.x, 2), round(p2.y, 2)],
                        "width": round(d.get("width") or 0, 2),
                    })
            elif kind == "re":
                r = item[1]
                out.append({
                    "type": "rect",
                    "bbox": [round(v, 2) for v in (r.x0, r.y0, r.x1, r.y1)],
                    "width": round(d.get("width") or 0, 2),
                    "fill": bool(d.get("fill")),
                })
    return out


def extract(doc: fitz.Document, images_dir: str | None) -> dict:
    layout = {"page_count": len(doc), "unit": "pt", "pages": []}
    for page in doc:
        blocks = []
        for b in page.get_text("dict")["blocks"]:
            if b["type"] != 0:
                continue
            for line in b["lines"]:
                for span in line["spans"]:
                    text = span["text"]
                    if not text.strip():
                        continue
                    blocks.append({
                        "text": text,
                        "bbox": [round(v, 2) for v in span["bbox"]],
                        "font": span["font"],
                        "size": round(span["size"], 2),
                        "bold": bool(span["flags"] & 16),
                        "italic": bool(span["flags"] & 2),
                        "color": f"#{span['color']:06x}",
                    })
        images = []
        if images_dir:
            Path(images_dir).mkdir(parents=True, exist_ok=True)
            for i, info in enumerate(page.get_image_info(xrefs=True)):
                xref = info.get("xref", 0)
                if not xref:
                    continue
                pix = fitz.Pixmap(doc, xref)
                if pix.n - pix.alpha >= 4:
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                fname = f"p{page.number + 1}_img{i}.png"
                pix.save(str(Path(images_dir) / fname))
                images.append({"file": fname,
                               "bbox": [round(v, 2) for v in info["bbox"]]})
        layout["pages"].append({
            "page": page.number + 1,
            "size_pt": [round(page.rect.width, 2), round(page.rect.height, 2)],
            "size_mm": [round(page.rect.width * PT_TO_MM, 1),
                        round(page.rect.height * PT_TO_MM, 1)],
            "spans": blocks,
            "tables": extract_tables(page),
            "drawings": extract_drawings(page),
            "images": images,
        })
    return layout


def render(doc: fitz.Document, out_dir: str, dpi: int) -> list:
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    files = []
    for page in doc:
        pix = page.get_pixmap(dpi=dpi)
        f = str(Path(out_dir) / f"page{page.number + 1}.png")
        pix.save(f)
        files.append(f)
    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--out", help="layout.json 輸出路徑")
    ap.add_argument("--images-dir", help="圖片輸出目錄")
    ap.add_argument("--render-dir", help="頁面 PNG 渲染輸出目錄")
    ap.add_argument("--dpi", type=int, default=150)
    args = ap.parse_args()

    doc = open_doc(args.pdf)
    if args.probe:
        print(json.dumps(probe(doc), ensure_ascii=False, indent=2))
        return
    if args.render_dir:
        files = render(doc, args.render_dir, args.dpi)
        print(json.dumps({"rendered": files}, ensure_ascii=False))
        return
    layout = extract(doc, args.images_dir)
    out = args.out or (str(Path(args.pdf).with_suffix("")) + "_layout.json")
    Path(out).write_text(json.dumps(layout, ensure_ascii=False, indent=1),
                         encoding="utf-8")
    total = sum(len(p["spans"]) for p in layout["pages"])
    print(json.dumps({"out": out, "pages": layout["page_count"],
                      "total_spans": total}, ensure_ascii=False))


if __name__ == "__main__":
    main()
