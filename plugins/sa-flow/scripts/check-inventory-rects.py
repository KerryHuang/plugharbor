#!/usr/bin/env python3
"""S2a 收件的 rect 機械檢查：inventory 的 `可標註元素` 能不能直接交給 S4 用。

用法:
    python3 check-inventory-rects.py <inventory.yml> [...] --shots <sNN-*.png> [...] [--dpr 2]

檢查三件事，任一非空 exit 1（退回該組補量，不進 S3）:
  1. 截圖沒有任何一筆 rect 的 `於:` 指向它（量都沒量）
  2. rect 不是四個數字（寫了「約」、文字描述、比例換算）
  3. rect 超出它 `於:` 那張圖的 CSS 尺寸（圖寬 ÷ dpr）——單位混用（device px）或量錯狀態；
     `於:` 指向不存在的檔也列在這裡

## 為什麼要有這支腳本

曾有 S2a 兩組的 rect 沒驗就交 S3：A 組工具列量 CSS px、對話框量 device px；
B 組 25 張只有 15 張有 rect。S4 拒產 5／21 張，主 session 回實機補拍 15 張。
呼叫端收件時只看了「銷帳三態各幾條」。

## 限制

只驗「有沒有、是不是數字、在不在圖裡」，**驗不到 rect 指錯元素**
（例如「工具列-編輯」差一顆按鈕寬，要靠 S4 先驗映射）。
解析用 regex 不用 YAML parser——歷次 inventory 的 flow map 常夾多行註記，parser 會整份放棄。
"""
import argparse
import re
import struct
import sys
from pathlib import Path

# `icon_rect:` 之類不算；`rect: [[..],[..]]` 一筆多框也要吃
RECT_RE = re.compile(r"(?<![\w])rect:\s*(\[\s*\[.*?\]\s*\]|\[[^\]]*\])")
AT_RE = re.compile(r"(?<!標)於:\s*([^\s,}]+)")
NAME_RE = re.compile(r"名稱:")
# 標籤空白區／空白可標籤區底下的 rect 是給標籤放的位置，不是標註目標
BLANK_RE = re.compile(r"空白區|空白可標籤區|側:")


def png_size(path):
    with open(path, "rb") as f:
        head = f.read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", head[16:24])


def parse(text):
    """以 `名稱:` 切條目，每個標註目標 rect 配同條目裡的 `於:`（flow 與 block 寫法都有）。"""
    names = [m.start() for m in NAME_RE.finditer(text)]
    out = []
    for m in RECT_RE.finditer(text):
        start = max((n for n in names if n < m.start()), default=0)
        if BLANK_RE.search(text, start, m.start()):
            continue
        end = min((n for n in names if n > m.start()), default=len(text))
        at = AT_RE.search(text, start, end)
        line = text.count("\n", 0, m.start()) + 1
        inner = re.findall(r"\[([^\[\]]*)\]", m.group(1))
        for raw in inner or [m.group(1)]:
            out.append((line, raw, at.group(1) if at else None))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inventory", nargs="+")
    ap.add_argument("--shots", nargs="+", required=True, help="clean 截圖（要被標註的那批）")
    ap.add_argument("--dpr", type=float, default=2)
    args = ap.parse_args()

    shots = {Path(p).name: Path(p) for p in args.shots}
    shot_dirs = {p.parent for p in shots.values()}
    hits = {name: 0 for name in shots}
    not_numeric, out_of_bounds = [], []

    for inv in args.inventory:
        for line, raw, at in parse(Path(inv).read_text(encoding="utf-8")):
            where = f"{Path(inv).name}:{line}"
            if at in hits:
                hits[at] += 1
            try:
                x, y, w, h = (float(v) for v in raw.split(","))
            except ValueError:
                not_numeric.append(f"{where}  rect: [{raw.strip()}]")
                continue
            if at is None:
                not_numeric.append(f"{where}  rect 沒有 於:")
                continue
            path = shots.get(at) or next((d / at for d in shot_dirs if (d / at).exists()), None)
            size = png_size(path) if path else None
            if size is None:
                out_of_bounds.append(f"{where}  於: {at} 找不到這張圖")
                continue
            cw, ch = size[0] / args.dpr, size[1] / args.dpr
            if x < 0 or y < 0 or x + w > cw + 1 or y + h > ch + 1:
                out_of_bounds.append(
                    f"{where}  [{raw.strip()}] 超出 {at} 的 CSS 尺寸 {cw:.0f}×{ch:.0f}")

    unmeasured = sorted(n for n, c in hits.items() if c == 0)
    sections = [("1. 截圖零 rect", unmeasured), ("2. rect 不是數字", not_numeric),
                ("3. rect 超出圖面", out_of_bounds)]
    for title, items in sections:
        print(f"{title}：{len(items)}")
        for it in items:
            print(f"   {it}")
    sys.exit(1 if any(items for _, items in sections) else 0)


if __name__ == "__main__":
    main()
