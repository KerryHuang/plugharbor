# -*- coding: utf-8 -*-
"""操作手冊 Markdown → PDF

用法：
    python3 build-manual-pdf.py <手冊.md> [輸出.pdf]

輸出未指定時，產在手冊同目錄的同名 .pdf。
需要：mkdocs 環境的 python（有 markdown 套件）＋ 系統 Chrome。

    /Users/<你>/.local/share/uv/tools/mkdocs/bin/python build-manual-pdf.py 手冊.md

流程：md → HTML（套 manual-print.css）→ Chrome headless 列印 → PDF → 蓋頁碼
封面資訊取自手冊開頭的第一個表格；目錄由 H1/H2 自動產生（可點擊，無頁碼）。

Chrome headless 的 --print-to-pdf 不支援自訂頁尾樣板（要嘛不印頁尾，要嘛印
預設樣式含本機檔案路徑，兩者都不能交付客戶），所以頁碼是 PDF 產出後另外
用 PyMuPDF 逐頁蓋章，不是列印時產生的。
"""
import io, os, re, sys, html, subprocess

import fitz  # PyMuPDF：蓋頁碼
import markdown

PAGE_NUM_FONT = "china-t"
PAGE_NUM_SIZE = 9
PAGE_NUM_COLOR = (0.45, 0.45, 0.45)
PAGE_NUM_BOTTOM_MARGIN = 24  # pt，落在版面下邊界 20mm(≈56.7pt) 的留白帶內


def stamp_page_numbers(pdf_path):
    doc = fitz.open(pdf_path)
    total = doc.page_count
    for i, page in enumerate(doc, start=1):
        text = "第 %d 頁，共 %d 頁" % (i, total)
        tw = fitz.get_text_length(text, fontname=PAGE_NUM_FONT, fontsize=PAGE_NUM_SIZE)
        x = (page.rect.width - tw) / 2
        y = page.rect.height - PAGE_NUM_BOTTOM_MARGIN
        page.insert_text((x, y), text, fontname=PAGE_NUM_FONT,
                          fontsize=PAGE_NUM_SIZE, color=PAGE_NUM_COLOR)
    tmp = pdf_path + ".tmp"
    doc.save(tmp)
    doc.close()
    os.replace(tmp, pdf_path)

# Windows 預設 cp950：印中文會亂碼、印 emoji 直接炸 UnicodeEncodeError（實測）。
# 與 parse_foxpro.py 同一做法，腳本自己處理，不靠呼叫端設 PYTHONUTF8。
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
CSS_PATH = os.path.join(HERE, "manual-print.css")
CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "C:/Program Files/Google/Chrome/Application/chrome.exe",  # Windows
    "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
    "/usr/bin/google-chrome",  # linux
    "/usr/bin/chromium",
]


def find_chrome():
    for path in CHROME_CANDIDATES:
        if os.path.exists(path):
            return path
    sys.exit("找不到 Chrome，請確認已安裝（試過：%s）" % "、".join(CHROME_CANDIDATES))


def build(src, out):
    src_dir = os.path.dirname(os.path.abspath(src))
    out = os.path.abspath(out)
    html_path = os.path.splitext(out)[0] + ".build.html"
    raw = io.open(src, encoding="utf-8").read()

    title = re.search(r'^#\s+(.+)$', raw, re.M).group(1).strip().replace("操作手冊：", "")

    # 封面資訊 = 文件開頭第一個表格
    first_tbl = re.search(r'^\|.*\|\n\|[-\s|:]+\|\n(?:\|.*\|\n)+', raw, re.M)
    meta = {}
    if first_tbl:
        for line in first_tbl.group(0).strip().split("\n")[2:]:
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) == 2 and cells[0]:
                meta[cells[0]] = cells[1]

    body_md = re.sub(r'^#\s+.+?\n', '', raw, count=1, flags=re.M)
    if first_tbl:
        body_md = body_md.replace(first_tbl.group(0), "", 1)
    # 圖片相對路徑 → 絕對 file://，HTML 才能放在別的目錄
    body_md = re.sub(r'\]\((images/[^)]+)\)',
                     lambda m: "](file://%s/%s)" % (src_dir, m.group(1)), body_md)

    md = markdown.Markdown(
        extensions=["tables", "toc", "attr_list", "fenced_code", "sane_lists"],
        extension_configs={"toc": {"toc_depth": "1-2"}})
    body_html = md.convert(body_md)

    css = io.open(CSS_PATH, encoding="utf-8").read()
    meta_rows = "".join("<tr><td>%s</td><td>%s</td></tr>" % (html.escape(k), html.escape(v))
                        for k, v in meta.items() if k != "功能名稱")

    doc = """<!doctype html><html lang="zh-TW"><head><meta charset="utf-8">
<title>%s</title><style>%s</style></head><body>
<div class="cover">
  <h1>%s</h1>
  <div class="code">操作手冊</div>
  <div class="rule"></div>
  <table>%s</table>
</div>
<div class="toc-page"><h2>目　錄</h2><div class="toc">%s</div></div>
%s
</body></html>""" % (html.escape(title), css, html.escape(title), meta_rows, md.toc, body_html)

    io.open(html_path, "w", encoding="utf-8").write(doc)

    r = subprocess.run(
        [find_chrome(), "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
         "--virtual-time-budget=15000", "--print-to-pdf=" + out, "file://" + html_path],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    if not os.path.exists(out):
        sys.exit("PDF 產生失敗\n%s\n%s" % (r.stdout, r.stderr))
    os.remove(html_path)
    stamp_page_numbers(out)
    print("PDF -> %s (%.1f KB)" % (out, os.path.getsize(out) / 1024))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    s = sys.argv[1]
    o = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(s)[0] + ".pdf"
    build(s, o)
