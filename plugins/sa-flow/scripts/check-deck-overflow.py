#!/usr/bin/env python3
"""簡報 PDF 溢出檢查：內容被擠進頁尾帶（頁尾文字與頁碼之間的中段），就判定溢出。

用法：check-deck-overflow.py <簡報.pdf>
結束碼：0 無溢出｜1 有溢出（列出頁碼）｜2 無法檢查（缺 PyMuPDF 與 pdftoppm）

來由：Marp 投影片 1280×720，一頁放「說明＋截圖＋說明框」時，
說明框會被擠出投影片、壓到頁尾。md 原稿看不出版面，
只有產出 PDF 才看得到。腳本標出的頁仍要開圖確認。
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

# Windows 預設 cp950：印中文會亂碼、印 emoji 直接炸 UnicodeEncodeError。
# 與 parse_foxpro.py 同一做法，腳本自己處理，不靠呼叫端設 PYTHONUTF8。
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

# 頁尾帶：下方 7% 高；避開左側頁尾文字（左 20%）與右側頁碼（右 8%）
BAND_TOP, BAND_LEFT, BAND_RIGHT = 0.93, 0.20, 0.92
# 投影片底色純白，頁尾帶中段出現「非白」像素就是內容侵入。
# 原本門檻 200 只算深色：淺色截圖底部、說明框黃底（亮度約 249）都漏抓，
# 所以門檻放寬到 250。
INK_THRESHOLD, MIN_INK_PIXELS = 250, 20


def render_pages(pdf: Path, out_dir: Path):
    """每頁轉成 50dpi PNG。優先 PyMuPDF（跨平台），沒有才用 pdftoppm。"""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        fitz = None
    if fitz is not None:
        paths = []
        with fitz.open(pdf) as doc:
            for i, page in enumerate(doc, 1):
                path = out_dir / f"p-{i:03d}.png"
                page.get_pixmap(dpi=50).save(path)
                paths.append(path)
        return paths
    if shutil.which("pdftoppm"):
        subprocess.run(["pdftoppm", "-r", "50", "-png", str(pdf), str(out_dir / "p")], check=True)
        return sorted(out_dir.glob("p-*.png"))
    return None


def ink_pixels_in_footer_band(png: Path) -> int:
    im = Image.open(png).convert("L")
    w, h = im.size
    band = im.crop((int(w * BAND_LEFT), int(h * BAND_TOP), int(w * BAND_RIGHT), h))
    return sum(1 for v in band.getdata() if v < INK_THRESHOLD)


def main() -> int:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    pdf = Path(sys.argv[1])
    with tempfile.TemporaryDirectory() as tmp:
        pages = render_pages(pdf, Path(tmp))
        if pages is None:
            print("⚠ 無法檢查簡報溢出：需要 PyMuPDF（pip install pymupdf）或 pdftoppm（poppler）")
            return 2
        flagged = [i for i, png in enumerate(pages, 1)
                   if ink_pixels_in_footer_band(png) > MIN_INK_PIXELS]
    if not flagged:
        print(f"✅ 簡報溢出檢查：{len(pages)} 頁皆無內容侵入頁尾帶")
        return 0
    print(f"❌ 簡報溢出：第 {'、'.join(map(str, flagged))} 頁的內容侵入頁尾帶（共 {len(pages)} 頁）")
    print("   修法：截圖改 h: 限高（不得小於 h:380）；仍放不下就把說明框拆到「原標題（續）」頁")
    return 1


if __name__ == "__main__":
    sys.exit(main())
