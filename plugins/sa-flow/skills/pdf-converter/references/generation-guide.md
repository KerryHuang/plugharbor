# 版面重建技法 — python-docx / openpyxl

生成腳本由 AI 依 layout.json 現場撰寫；本檔是重建時的技法對照，避免每次重新踩坑。單位換算：layout.json 一律 pt，`mm = pt × 25.4 ÷ 72`；python-docx 用 `Pt()`/`Mm()`，openpyxl 欄寬單位是字元寬（約 `pt ÷ 5.25`，需實測微調）。

## Word（python-docx）

### 頁面設定

```python
sec = doc.sections[0]
sec.page_width, sec.page_height = Mm(w_mm), Mm(h_mm)   # 依 layout size_mm
# 邊界 = 最外圍內容 bbox 到頁緣的距離（從 spans/tables 的 min/max 座標推）
```

### 中文字型對映

PDF 內嵌字型名常是 `CIDFont+F1` 這種代號，**無法直接對映**。判斷順序：

1. 看字形特徵推測（標楷體筆畫楷書、新細明體襯線細明）——渲染原 PDF 頁面 PNG 讀圖判斷
2. 不確定就 `AskUserQuestion`（常見組合：標題標楷體＋內文新細明體）

東亞字型必須同時設 `w:eastAsia`，否則中文字落不到指定字型：

```python
run.font.name = "新細明體"
run._element.rPr.rFonts.set(qn("w:eastAsia"), "新細明體")
```

### 版面定位（表單式 PDF 首選：framePr 絕對定位）

FoxPro 報表這類**表單式 PDF**（元素各有絕對座標）：每個 span 一個段落，掛 `w:framePr` 直接落在頁面座標——實測（採購單類報表）錨點偏差 mean 0.25mm，遠優於表格框架逼近：

```python
fp = OxmlElement("w:framePr")
fp.set(qn("w:x"), str(int(x_pt * 20)))      # pt → twips
fp.set(qn("w:y"), str(int(y_pt * 20)))
fp.set(qn("w:hAnchor"), "page"); fp.set(qn("w:vAnchor"), "page")
fp.set(qn("w:wrap"), "none")
pPr.insert(0, fp)   # 段落再設 line_spacing = Pt(bbox高)、space 前後 0
```

搭配兩個關鍵技法（實測各解掉一類 hard/soft fail）：

- **`w:fitText` 鎖 run 寬度＝bbox 寬**：Word 字元 advance 與 PDF 不同，長字串尾端會漂移出現「鬼影」；fitText 強制同寬（實測文字一致率 96.8% → 100%）。frame 寬要留餘裕（bbox 寬 +30pt）避免折行被 exact 列高截字。
- **數值欄（前導空白＋數字）不用 fitText**：改去空白＋段落右對齊＋frame 寬＝bbox 寬鎖右緣（fitText 會把空白壓縮造成數字位移）。

框線／簽核框：橫線＝細高 frame 掛 `w:pBdr` bottom；豎線＝掛 left＋exact 高；外框＝四邊。填色細矩形（<2pt 高）是粗橫線的畫法，取中線還原。

**已知長尾**（跨渲染器極限，交 reviewer 判定）：全形標點 advance 差異（PDF 常壓縮標點間距）、標楷體字形微差——版面正確但逐像素比對仍紅，屬可放行候選。

流動式文件（合約、說明書）才用**表格當版面框架**逼近：

- 多欄並排區（如表頭左公司右單號）→ 無框線表格分欄，欄寬照 bbox 比例
- 垂直間距 → 段落 `space_before/space_after`（從相鄰 span 的 y 差換算），不要用連發空段落
- 明細表 → 真表格；欄寬 = 各欄 bbox 寬度換算 `Mm()`，並設 `table.autofit = False` + 逐 cell 設寬（Word 對表格欄寬的尊重需要兩者都設）

### 邊框還原（依 layout drawings）

drawings 的線寬（pt）與位置決定樣式：同位置兩條近距平行線＝雙線（`val="double"`）；線寬 ≥1.5pt 判粗線。python-docx 無邊框 API，直接操作 XML：

```python
def set_cell_border(cell, edge, val="single", sz=8):   # sz 單位 1/8 pt
    tcPr = cell._tc.get_or_add_tcPr()
    borders = tcPr.find(qn("w:tcBorders")) or SubElement(tcPr, qn("w:tcBorders"))
    el = SubElement(borders, qn(f"w:{edge}"))
    el.set(qn("w:val"), val); el.set(qn("w:sz"), str(sz)); el.set(qn("w:color"), "000000")
```

「無直向格線」的 FoxPro 報表風格：明細表只設 top/bottom，left/right 用 `val="nil"`。

### 常見翻車點

- 表格 cell 內第一個段落自帶，不要再 `add_paragraph`（會多一行撐高列）
- 列高：`row.height` + `height_rule = WD_ROW_HEIGHT_RULE.EXACTLY` 才鎖得住
- 字級照 span `size` 用 `Pt()`；Word 渲染與 PDF 同字級即近似同寬，折行不一致時優先檢查欄寬而非字級

## Excel（openpyxl）

### 結構

- layout.json `tables[].cells` 的 row/col 直接落格；同表格多 cell bbox 相同 → 合併格，用 `ws.merge_cells()`
- 表格外散落 span：依 y 座標插入對應列，必要時在表格上方/下方增列
- 欄寬：`ws.column_dimensions[letter].width = bbox寬pt / 5.25`（實測微調）；列高：`ws.row_dimensions[i].height = bbox高pt`

### 樣式

```python
from openpyxl.styles import Font, Border, Side, Alignment
cell.font = Font(name="新細明體", size=10, bold=span_bold)
cell.border = Border(bottom=Side(style="double"))      # 依 drawings 判線式
cell.alignment = Alignment(horizontal="right")          # 數值欄靠右，依 span x 位置判
```

### 常見翻車點

- 數字欄保持數值型別＋`number_format`（如 `#,##0`），不要存成字串（驗證比對用正規化文字，兩者都過，但使用者拿到要能加總）
- 合併格只在左上格寫值，其餘留空；驗證腳本已按此假設
- 日期顯示格式照 PDF 原樣（`yyy/mm/dd` 民國年就存文字，不要自作聰明轉西元）

## 迭代修正對照（verify-report → 改法）

| 症狀 | 優先檢查 |
|------|---------|
| text missing 某段 | 生成腳本漏了該 span／cell；掃 layout.json 確認來源存在 |
| 某頁 max_offset 大但其他頁正常 | 該頁某區塊定位框架欄寬錯，連帶下移 |
| 視覺差異集中在表格區 | 邊框樣式（單/雙線、nil 邊）或欄寬；對照 diff PNG 紅區 |
| 頁數變多 | 內容溢出：邊界、列高 EXACTLY 未鎖、或多出的空段落 |
