#!/usr/bin/env python3
"""check-inventory-rects.py 的測試。直接執行：python3 test_check_inventory_rects.py

inventory 的 rect 與 annotate.py spec 的 box 同為 [x0, y0, x1, y1]（inventory 是 CSS px，
DPR 2 的截圖寫進 spec 前要乘 2）。
"""
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "check-inventory-rects.py"


def write_png(path, w, h):
    def chunk(t, d):
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    raw = b"".join(b"\x00" + b"\x00\x00\x00" * w for _ in range(h))
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def run(rect_line, png=(400, 200)):
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        write_png(d / "s01-list.png", *png)
        inv = d / "inventory.yml"
        inv.write_text("可標註元素:\n  - { 名稱: 新增按鈕, %s, 於: s01-list.png }\n" % rect_line, encoding="utf-8")
        r = subprocess.run([sys.executable, str(SCRIPT), str(inv), "--shots", str(d / "s01-list.png"), "--dpr", "2"],
                           capture_output=True, text=True, encoding="utf-8")
        return r.returncode, r.stdout


class RectFormat(unittest.TestCase):
    def test_x0y0x1y1_inside_image_passes(self):
        code, out = run("rect: [10, 10, 100, 50]")   # CSS 尺寸 200x100
        self.assertEqual(code, 0, out)

    def test_x1_beyond_image_fails(self):
        code, out = run("rect: [10, 10, 250, 50]")
        self.assertEqual(code, 1)
        self.assertIn("超出", out)

    def test_x1_not_greater_than_x0_fails(self):
        code, out = run("rect: [100, 10, 40, 50]")
        self.assertEqual(code, 1)
        self.assertIn("x1", out)

    def test_non_numeric_fails(self):
        code, out = run("rect: [約10, 10, 100, 50]")
        self.assertEqual(code, 1)

    def test_missing_rect_fails(self):
        code, out = run("sel: x")
        self.assertEqual(code, 1)
        self.assertIn("截圖零 rect", out)


if __name__ == "__main__":
    unittest.main()
