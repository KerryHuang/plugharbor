#!/usr/bin/env python3
"""plugin 共用標註器：JSON spec → 標註/合成 PNG。

用法:
    python3 annotate.py <spec.json>

使用者：`linear-illustrate`（票面示意圖）、`operation-manual`／`manual-explorer`（手冊截圖）。
Spec 格式見 `references/annotate-spec.md`（plugin 根的 references/）。

座標一律為**影像 px**。playwright `scale=css` 時影像 px == CSS px；
Chrome DevTools 在 DPR 2 的機器上截出來是 CSS px × 2，**呼叫端要自己先乘好**。

⚠ 遮罩與紅框都必須畫進像素。用 CSS 疊一層再截圖，色會被色彩管理位移
（實測輸入 #3467A9、輸出 (65,102,164)），遮罩會跟底色差一截，一眼看得出被塗過。
"""
import json
import sys
from statistics import median

from PIL import Image, ImageDraw, ImageFont

# Windows 預設 cp950：印中文會亂碼、印 emoji 直接炸 UnicodeEncodeError。
# 與 parse_foxpro.py 同一做法，腳本自己處理，不靠呼叫端設 PYTHONUTF8。
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

COLORS = {
    "red": (217, 48, 37),
    "blue": (25, 103, 210),
    "green": (24, 128, 56),
    "orange": (230, 124, 0),
    "gray": (95, 99, 104),
}

# CJK 字型 fallback 順序（PingFang.ttc 常無法被 freetype 開啟）
FONT_CANDIDATES = [
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",  # linux
    "C:/Windows/Fonts/msjh.ttc",  # Windows 微軟正黑體（繁中）
    "C:/Windows/Fonts/mingliu.ttc",  # Windows 細明體 fallback
]


def load_font(size):
    for path in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


FONT = load_font(22)
FONT_BADGE = load_font(20)


def color_of(name):
    if isinstance(name, (list, tuple)):
        return tuple(name)
    return COLORS[name]


def draw_badge(d, x, y, num, color):
    # 半徑跟字級走：寫死 16 在 font_size 44 時圓點比數字還小
    r = max(16, round(FONT_BADGE.size * 0.8))
    # 夾在畫布內：框貼邊（x0≈0）時 badge 會被切掉一半
    w, h = d.im.size
    x = min(max(x, r), w - r)
    y = min(max(y, r), h - r)
    d.ellipse([x - r, y - r, x + r, y + r], fill=color_of(color))
    d.text((x, y - 1), str(num), font=FONT_BADGE, fill="white", anchor="mm")


def draw_rect(d, box, color, width=4, dashed=False, dash=12, gap=8):
    x0, y0, x1, y1 = box
    c = color_of(color)
    if not dashed:
        d.rectangle(box, outline=c, width=width)
        return
    x = x0
    while x < x1:
        d.line([x, y0, min(x + dash, x1), y0], fill=c, width=width)
        d.line([x, y1, min(x + dash, x1), y1], fill=c, width=width)
        x += dash + gap
    y = y0
    while y < y1:
        d.line([x0, y, x0, min(y + dash, y1)], fill=c, width=width)
        d.line([x1, y, x1, min(y + dash, y1)], fill=c, width=width)
        y += dash + gap


def draw_cross(d, box, color, width=5, inset=8):
    x0, y0, x1, y1 = box
    c = color_of(color)
    d.line([x0 + inset, y0 + inset, x1 - inset, y1 - inset], fill=c, width=width)
    d.line([x0 + inset, y1 - inset, x1 - inset, y0 + inset], fill=c, width=width)


def sample_color(img, box, margin=6):
    """從遮罩框四周取樣底色中位數——遮出來才跟背景同色。

    box 是要蓋掉的區域；取樣點在它上下各 margin px 的帶狀區，避開框內內容。
    """
    x0, y0, x1, y1 = [int(v) for v in box]
    px = img.load()
    pts = []
    for y in (max(0, y0 - margin), min(img.height - 1, y1 + margin)):
        for x in range(max(0, x0), min(img.width, x1), max(1, (x1 - x0) // 20 or 1)):
            pts.append(px[x, y])
    if not pts:
        return (255, 255, 255)
    return tuple(int(median([p[i] for p in pts])) for i in range(3))


def draw_mask(img, d, box, color=None):
    """實心遮罩。color 省略時自動取樣框四周底色。"""
    fill = color_of(color) if color is not None else sample_color(img, box)
    d.rectangle([int(v) for v in box], fill=fill)


def draw_label(d, box, text, color="red", side="right", pad=10):
    """標籤貼在框旁邊。side: right|left|below|above。"""
    x0, y0, x1, y1 = box
    c = color_of(color)
    tw = d.textlength(text, font=FONT)
    th = FONT.size + 8
    if side == "right":
        tx, ty = x1 + pad, y0 + (y1 - y0 - th) / 2
    elif side == "left":
        tx, ty = x0 - pad - tw - 16, y0 + (y1 - y0 - th) / 2
    elif side == "above":
        tx, ty = x0, y0 - pad - th
    else:
        tx, ty = x0, y1 + pad
    d.rectangle([tx, ty, tx + tw + 16, ty + th], fill=c)
    d.text((tx + 8, ty + 4), text, font=FONT, fill="white")


def apply_composite(base, comp):
    """裁掉 base 在 cut_y 之下的部分，插入另一張圖的裁切區塊，回傳新畫布。

    comp: {cut_y, gap, insert: {src, crop: [x0,y0,x1,y1]}, x, bottom_margin}
    """
    src = Image.open(comp["insert"]["src"]).convert("RGB")
    crop = src.crop(tuple(comp["insert"]["crop"]))
    cut_y = comp["cut_y"]
    gap = comp.get("gap", 10)
    x = comp.get("x", comp["insert"]["crop"][0])
    bottom = comp.get("bottom_margin", 30)
    new_h = cut_y + gap + crop.height + bottom
    canvas = Image.new("RGB", (base.width, new_h), "white")
    canvas.paste(base.crop((0, 0, base.width, cut_y)), (0, 0))
    canvas.paste(crop, (x, cut_y + gap))
    return canvas


def add_legend(img, lines):
    # 行高、圓點、文字起點都跟字級走：寫死 34px 在 font_size 44 時各行文字互相疊壓
    r = max(16, round(FONT_BADGE.size * 0.8))
    line_h = max(34, FONT.size + 16, 2 * r + 8)
    band_h = 26 + line_h * len(lines)
    canvas = Image.new("RGB", (img.width, img.height + band_h), "white")
    canvas.paste(img, (0, 0))
    d = ImageDraw.Draw(canvas)
    d.line([0, img.height, img.width, img.height], fill=(200, 200, 200), width=2)
    y = img.height + 14
    for line in lines:
        cy = y + line_h / 2
        draw_badge(d, 18 + r, cy, line["num"], line["color"])
        d.text((18 + 2 * r + 12, cy), line["text"], font=FONT, fill=(30, 30, 30), anchor="lm")
        y += line_h
    return canvas


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    with open(sys.argv[1], encoding="utf-8") as f:
        spec = json.load(f)

    # DPR 2 截圖（影像 px = CSS px × 2）字級要跟著放大，spec 可帶 font_size 覆寫預設 22
    global FONT, FONT_BADGE
    if spec.get("font_size"):
        FONT = load_font(int(spec["font_size"]))
        FONT_BADGE = load_font(int(spec["font_size"]) - 2)

    img = Image.open(spec["base"]).convert("RGB")
    if "composite" in spec:
        img = apply_composite(img, spec["composite"])

    d = ImageDraw.Draw(img)
    for op in spec.get("ops", []):
        kind = op["op"]
        if kind == "rect":
            draw_rect(d, op["box"], op["color"], op.get("width", 4), op.get("dashed", False))
        elif kind == "mask":
            draw_mask(img, d, op["box"], op.get("color"))
        elif kind == "label":
            draw_label(d, op["box"], op["text"], op.get("color", "red"), op.get("side", "right"))
        elif kind == "cross":
            draw_cross(d, op["box"], op["color"], op.get("width", 5))
        elif kind == "badge":
            draw_badge(d, op["at"][0], op["at"][1], op["num"], op["color"])
        else:
            sys.exit(f"unknown op: {kind}")

    if spec.get("legend"):
        img = add_legend(img, spec["legend"])

    img.save(spec["output"])
    print(f"saved: {spec['output']} ({img.width}x{img.height})")


if __name__ == "__main__":
    main()
