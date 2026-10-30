# -*- coding: utf-8 -*-
"""產生 Word 輸出用的 reference.docx，樣式對齊 manual-print.css。

    python3 make-docx-reference.py [輸出.docx]

不帶參數時輸出到本腳本同目錄的 manual-reference.docx。
範本本身不進版控（每次由本腳本生成），要調樣式改這個檔。

對應關係（CSS → Word 樣式）：
    h1 藍字＋下邊框        → Heading1
    h2 藍字＋左色條        → Heading2
    h3 淺藍底             → Heading3
    blockquote 黃底左橘條  → BlockText
    body PingFang TC      → Normal
    表格藍表頭             → Table（firstRow 條件格式）
"""
import io, os, re, shutil, subprocess, sys, zipfile

# Windows 預設 cp950：印中文會亂碼、印 emoji 直接炸 UnicodeEncodeError（實測）。
# 與 parse_foxpro.py 同一做法，腳本自己處理，不靠呼叫端設 PYTHONUTF8。
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

# 交付對象多半是 Windows Word，微軟正黑體是那邊的標準繁中黑體。
# ⚠ macOS 用 LibreOffice 驗證時中文會顯示成方框（該環境沒有這套字型），
#   那是驗證環境的問題，不影響 Windows Word 的實際顯示。
FONT = "Microsoft JhengHei"
BLUE = "1A4D8F"      # 主色
LIGHT = "EEF3FA"     # 步驟標題底
WARN_BG = "FFF9E6"   # 說明區塊底
WARN_LN = "E0A800"   # 說明區塊左邊框
GRID = "C8D4E3"      # 表格框線

def rfonts():
    return ('<w:rFonts w:ascii="%s" w:eastAsia="%s" w:hAnsi="%s" w:cs="%s"/>'
            % (FONT, FONT, FONT, FONT))

def style(sid, name, based, ppr, rpr, nxt="BodyText"):
    return ('<w:style w:type="paragraph" w:styleId="%s"><w:name w:val="%s"/>'
            '<w:basedOn w:val="%s"/><w:next w:val="%s"/><w:qFormat/>'
            '<w:pPr>%s</w:pPr><w:rPr>%s</w:rPr></w:style>'
            % (sid, name, based, nxt, ppr, rpr))

STYLES = {
 # 章標題：藍字 19pt ＋ 下邊框，前面留白、與下段不分離
 "Heading1": style("Heading1", "heading 1", "Normal",
    '<w:keepNext/><w:keepLines/>'
    '<w:pBdr><w:bottom w:val="single" w:sz="18" w:space="6" w:color="%s"/></w:pBdr>'
    '<w:spacing w:before="400" w:after="160"/>'
    '<w:outlineLvl w:val="0"/>' % BLUE,
    rfonts() + '<w:b/><w:color w:val="%s"/><w:sz w:val="38"/>' % BLUE),

 # 節標題：藍字 14pt ＋ 左色條
 "Heading2": style("Heading2", "heading 2", "Normal",
    '<w:keepNext/><w:keepLines/>'
    '<w:pBdr><w:left w:val="single" w:sz="24" w:space="6" w:color="%s"/></w:pBdr>'
    '<w:spacing w:before="280" w:after="120"/><w:ind w:left="120"/>'
    '<w:outlineLvl w:val="1"/>' % BLUE,
    rfonts() + '<w:b/><w:color w:val="%s"/><w:sz w:val="28"/>' % BLUE),

 # 步驟標題：淺藍底 12pt
 "Heading3": style("Heading3", "heading 3", "Normal",
    '<w:keepNext/><w:keepLines/>'
    '<w:shd w:val="clear" w:color="auto" w:fill="%s"/>'
    '<w:spacing w:before="220" w:after="100"/><w:ind w:left="80" w:right="80"/>'
    '<w:outlineLvl w:val="2"/>' % LIGHT,
    rfonts() + '<w:b/><w:color w:val="222222"/><w:sz w:val="24"/>'),

 # 說明／警告區塊：黃底＋左橘條
 "BlockText": style("BlockText", "Block Text", "BodyText",
    '<w:pBdr><w:left w:val="single" w:sz="24" w:space="8" w:color="%s"/></w:pBdr>'
    '<w:shd w:val="clear" w:color="auto" w:fill="%s"/>'
    '<w:spacing w:before="140" w:after="140"/>'
    '<w:ind w:left="240" w:right="120"/>' % (WARN_LN, WARN_BG),
    rfonts() + '<w:sz w:val="21"/>'),

 # 內文
 "Normal": ('<w:style w:type="paragraph" w:default="1" w:styleId="Normal">'
    '<w:name w:val="Normal"/><w:qFormat/>'
    '<w:pPr><w:spacing w:line="300" w:lineRule="auto" w:after="100"/></w:pPr>'
    '<w:rPr>' + rfonts() + '<w:sz w:val="21"/></w:rPr></w:style>'),

# 封面
 "CoverBrand": style("CoverBrand", "CoverBrand", "Normal",
    '<w:spacing w:before="2600" w:after="200"/><w:jc w:val="center"/>',
    rfonts() + '<w:color w:val="%s"/><w:sz w:val="26"/><w:spacing w:val="120"/>' % BLUE,
    nxt="Normal"),

 "CoverTitle": style("CoverTitle", "CoverTitle", "Normal",
    '<w:spacing w:before="0" w:after="160"/><w:jc w:val="center"/>',
    rfonts() + '<w:b/><w:color w:val="%s"/><w:sz w:val="60"/>' % BLUE,
    nxt="Normal"),

 "CoverSub": style("CoverSub", "CoverSub", "Normal",
    '<w:pBdr><w:bottom w:val="single" w:sz="18" w:space="10" w:color="%s"/></w:pBdr>'
    '<w:spacing w:before="0" w:after="900"/><w:jc w:val="center"/>' % BLUE,
    rfonts() + '<w:color w:val="666666"/><w:sz w:val="24"/><w:spacing w:val="80"/>',
    nxt="Normal"),

 "CoverMeta": style("CoverMeta", "CoverMeta", "Normal",
    '<w:spacing w:before="0" w:after="0"/><w:jc w:val="center"/>',
    rfonts() + '<w:color w:val="444444"/><w:sz w:val="20"/>',
    nxt="Normal"),

# 目錄標題
 "TocTitle": style("TocTitle", "TocTitle", "Normal",
    '<w:pBdr><w:bottom w:val="single" w:sz="18" w:space="8" w:color="%s"/></w:pBdr>'
    '<w:spacing w:before="0" w:after="260"/>' % BLUE,
    rfonts() + '<w:b/><w:color w:val="%s"/><w:sz w:val="36"/>' % BLUE,
    nxt="Normal"),

# 目錄項目
 "TocL1": style("TocL1", "TocL1", "Normal",
    '<w:spacing w:before="80" w:after="40"/>',
    rfonts() + '<w:b/><w:color w:val="222222"/><w:sz w:val="23"/>', nxt="Normal"),

 "TocL2": style("TocL2", "TocL2", "Normal",
    '<w:spacing w:before="20" w:after="20"/><w:ind w:left="360"/>',
    rfonts() + '<w:color w:val="555555"/><w:sz w:val="21"/>', nxt="Normal"),

 # 圖說
 "Caption": style("Caption", "Caption", "Normal",
    '<w:spacing w:before="60" w:after="200"/><w:jc w:val="center"/>',
    rfonts() + '<w:i/><w:color w:val="555555"/><w:sz w:val="18"/>'),
}

# 頁尾頁碼：PAGE／NUMPAGES 複合欄位，開檔時靠 settings.xml 的 updateFields 自動算好
_PN_RPR = rfonts() + '<w:color w:val="888888"/><w:sz w:val="18"/>'
def _run(inner):
    return '<w:r><w:rPr>%s</w:rPr>%s</w:r>' % (_PN_RPR, inner)
def _text(t):
    return _run('<w:t xml:space="preserve">%s</w:t>' % t)
def _field(instr):
    return (_run('<w:fldChar w:fldCharType="begin"/>')
            + _run('<w:instrText xml:space="preserve"> %s </w:instrText>' % instr)
            + _run('<w:fldChar w:fldCharType="separate"/>')
            + _text("1")
            + _run('<w:fldChar w:fldCharType="end"/>'))
FOOTER_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
    '<w:p><w:pPr><w:jc w:val="center"/></w:pPr>'
    + _text("第 ") + _field("PAGE") + _text(" 頁，共 ") + _field("NUMPAGES") + _text(" 頁")
    + '</w:p></w:ftr>')

# 表格：藍表頭白字、細框線、隔列淺底
TABLE_STYLE = (
 '<w:style w:type="table" w:default="1" w:styleId="Table">'
 '<w:name w:val="Table"/><w:basedOn w:val="TableNormal"/><w:qFormat/>'
 '<w:tblPr><w:tblInd w:w="0" w:type="dxa"/>'
 '<w:tblBorders>'
 '<w:top w:val="single" w:sz="4" w:color="%(g)s"/><w:left w:val="single" w:sz="4" w:color="%(g)s"/>'
 '<w:bottom w:val="single" w:sz="4" w:color="%(g)s"/><w:right w:val="single" w:sz="4" w:color="%(g)s"/>'
 '<w:insideH w:val="single" w:sz="4" w:color="%(g)s"/><w:insideV w:val="single" w:sz="4" w:color="%(g)s"/>'
 '</w:tblBorders>'
 '<w:tblCellMar><w:top w:w="60" w:type="dxa"/><w:left w:w="108" w:type="dxa"/>'
 '<w:bottom w:w="60" w:type="dxa"/><w:right w:w="108" w:type="dxa"/></w:tblCellMar></w:tblPr>'
 '<w:tblStylePr w:type="firstRow"><w:rPr>%(f)s<w:b/><w:color w:val="FFFFFF"/></w:rPr>'
 '<w:tcPr><w:shd w:val="clear" w:color="auto" w:fill="%(b)s"/></w:tcPr></w:tblStylePr>'
 '<w:tblStylePr w:type="band2Horz"><w:tcPr>'
 '<w:shd w:val="clear" w:color="auto" w:fill="F6F9FC"/></w:tcPr></w:tblStylePr>'
 '</w:style>' % {"g": GRID, "f": rfonts(), "b": BLUE})


def build(out):
    tmp = out + ".src"
    with open(tmp, "wb") as f:
        f.write(subprocess.run(["pandoc", "--print-default-data-file", "reference.docx"],
                               capture_output=True, check=True).stdout)
    zin = zipfile.ZipFile(tmp)
    styles_xml = zin.read("word/styles.xml").decode("utf-8")

    for sid, new in list(STYLES.items()) + [("Table", TABLE_STYLE)]:
        pat = re.compile(r'<w:style [^>]*w:styleId="%s".*?</w:style>' % sid, re.S)
        if pat.search(styles_xml):
            styles_xml = pat.sub(new, styles_xml, count=1)
        else:
            styles_xml = styles_xml.replace("</w:styles>", new + "</w:styles>")

    # Word 的 TOC／頁碼都是欄位，不會自己算——加 updateFields 讓開檔時更新
    settings = zin.read("word/settings.xml").decode("utf-8")
    if "updateFields" not in settings:
        settings = re.sub(r'(<w:settings[^>]*>)', r'\1<w:updateFields w:val="true"/>', settings, count=1)

    # pandoc 用 --reference-doc 時會沿用範本裡掛好的頁尾——這裡掛一個含 PAGE/NUMPAGES 的頁尾
    document_xml = zin.read("word/document.xml").decode("utf-8")
    document_xml = re.sub(r'(<w:sectPr\b[^>]*>)',
        r'\1<w:footerReference w:type="default" r:id="rIdPageFooter"/>', document_xml, count=1)

    rels_xml = zin.read("word/_rels/document.xml.rels").decode("utf-8")
    rels_xml = rels_xml.replace("</Relationships>",
        '<Relationship Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" '
        'Id="rIdPageFooter" Target="footer1.xml" /></Relationships>')

    ctypes_xml = zin.read("[Content_Types].xml").decode("utf-8")
    ctypes_xml = ctypes_xml.replace("</Types>",
        '<Override PartName="/word/footer1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml" /></Types>')

    REWRITES = {
        "word/styles.xml": styles_xml,
        "word/settings.xml": settings,
        "word/document.xml": document_xml,
        "word/_rels/document.xml.rels": rels_xml,
        "[Content_Types].xml": ctypes_xml,
    }
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            if item.filename in REWRITES:
                data = REWRITES[item.filename].encode("utf-8")
            else:
                data = zin.read(item.filename)
            zout.writestr(item, data)
        zout.writestr("word/footer1.xml", FOOTER_XML)
    zin.close(); os.remove(tmp)
    print("reference -> %s (%.1f KB)" % (out, os.path.getsize(out) / 1024))


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    build(sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "manual-reference.docx"))
