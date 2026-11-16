#!/usr/bin/env python3
"""spec_to_cases.py 的測試。直接執行：python3 test_spec_to_cases.py"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "spec_to_cases.py"
VALIDATE = HERE / "validate.py"

NEW = """# 備註欄

票號：#12 · 狀態：草稿 · 2026-11-16

## 決定
- D-01 備註上限 200 字；否決：不限長度（資料表欄位有限）（拍板：使用者）

## 驗收
說明文字會被丟掉。

### AC-01 備註存檔後顯示（D-01） [ui]
#### 前置條件
- 已存在訂單 SO-001
#### 步驟
1. 開啟 SO-001，備註填「週五前出貨」，按「儲存」
#### 預期
- 顯示「儲存成功」
- 備註欄顯示「週五前出貨」

### AC-02 備註 API 回 400 [api]
#### 步驟
1. POST /orders/SO-001/note，body 備註 201 字
#### 預期
- 回 400，訊息「備註不可超過 200 字」

## 留給 builder
- 無
"""

LEGACY = """# 備註欄

| 項目 | 內容 |
|------|------|
| 狀態 | 草稿 |

## 2. 需求
### 2.3 驗收標準
#### AC-01 備註存檔後顯示（US-01） [ui]
##### 前置條件
- 已存在訂單 SO-001
##### 步驟
1. 開啟 SO-001，備註填「週五前出貨」，按「儲存」
##### 預期
- 顯示「儲存成功」
- 備註欄顯示「週五前出貨」

#### AC-02 備註 API 回 400 [api]
##### 步驟
1. POST /orders/SO-001/note，body 備註 201 字
##### 預期
- 回 400，訊息「備註不可超過 200 字」

### 2.4 非功能約束
無
"""


def run(doc_text, name="spec.md"):
    d = Path(tempfile.mkdtemp())
    src, out = d / name, d / "out" / "cases.md"
    src.write_text(doc_text, encoding="utf-8")
    p = subprocess.run([sys.executable, str(SCRIPT), str(src), str(out)],
                       capture_output=True, text=True)
    return p, out


def validate(path):
    return subprocess.run([sys.executable, str(VALIDATE), "acceptance", str(path)],
                          capture_output=True, text=True)


class TestSpecToCases(unittest.TestCase):
    def check_roundtrip(self, doc):
        p, out = run(doc)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stdout.strip(), "2")
        t = out.read_text(encoding="utf-8")
        self.assertIn("## AC-01 備註存檔後顯示（D-01） [ui]" if "D-01" in doc
                      else "## AC-01 備註存檔後顯示（US-01） [ui]", t)
        self.assertIn("## AC-02 備註 API 回 400 [api]", t)
        self.assertIn("### 前置條件\n- 已存在訂單 SO-001", t)
        self.assertIn("### 步驟\n1. 開啟 SO-001，備註填「週五前出貨」，按「儲存」", t)
        self.assertIn("- 顯示「儲存成功」\n- 備註欄顯示「週五前出貨」", t)
        self.assertIn("- 回 400，訊息「備註不可超過 200 字」", t)
        self.assertNotIn("#### ", t)
        self.assertNotIn("說明文字", t)
        v = validate(out)
        self.assertEqual(v.returncode, 0, v.stdout)

    def test_new_format_roundtrip(self):
        self.check_roundtrip(NEW)

    def test_legacy_23_roundtrip(self):
        self.check_roundtrip(LEGACY)

    def test_missing_expected_exit4(self):
        doc = NEW.replace("#### 預期\n- 回 400，訊息「備註不可超過 200 字」\n", "")
        p, out = run(doc)
        self.assertEqual(p.returncode, 4)
        self.assertIn("AC-02：缺 預期", p.stderr)
        self.assertFalse(out.exists())

    def test_placeholder_and_non_ascii_id_exit4(self):
        p, out = run(NEW.replace("- 回 400，訊息「備註不可超過 200 字」", "- {預期結果}"))
        self.assertEqual(p.returncode, 4)
        self.assertIn("AC-02", p.stderr)
        self.assertFalse(out.exists())
        p, out = run(NEW.replace("### AC-02 ", "### 驗收二 "))
        self.assertEqual(p.returncode, 4)
        self.assertIn("驗收二", p.stderr)
        self.assertFalse(out.exists())

    def test_braces_inside_item_are_not_placeholders(self):
        doc = NEW.replace("body 備註 201 字", 'body {"note":"x"}，路徑 /orders/{id}/note')
        p, out = run(doc)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn('{"note":"x"}', out.read_text(encoding="utf-8"))
        p, _ = run(NEW.replace("- 顯示「儲存成功」", "- <預期訊息>"))
        self.assertEqual(p.returncode, 4)

    def test_no_acceptance_section_exit4(self):
        p, out = run("# x\n\n## 決定\n- D-01 y\n")
        self.assertEqual(p.returncode, 4)
        self.assertIn("找不到驗收一節", p.stderr)
        self.assertFalse(out.exists())

    def test_fenced_heading_between_cases_does_not_truncate(self):
        fenced = "```\n## 範例\n### 2.4 假的\n```\n"
        for doc, case_p in ((NEW, "### AC-02"), (LEGACY, "#### AC-02")):
            doc2 = doc.replace(case_p, fenced + "\n" + case_p, 1)
            self.assertIn("## 範例", doc2)
            p, out = run(doc2)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertEqual(p.stdout.strip(), "2")
            self.assertIn("AC-02", out.read_text(encoding="utf-8"))

    def test_fenced_heading_before_section_is_not_start(self):
        doc = "# x\n\n```\n## 驗收\n### AC-09 假 [ui]\n```\n\n" + NEW.split("# 備註欄\n", 1)[1]
        p, out = run(doc)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stdout.strip(), "2")
        self.assertNotIn("AC-09", out.read_text(encoding="utf-8"))

    def test_nested_and_tilde_fences_follow_commonmark(self):
        nested = "````\n```\n## 範例\n### 2.4 假的\n```\n## 又一個\n````\n"
        tilde = "~~~\n```\n## 範例\n### 2.4 假的\n~~~\n"
        for fenced in (nested, tilde):
            for doc, case_p in ((NEW, "### AC-02"), (LEGACY, "#### AC-02")):
                p, out = run(doc.replace(case_p, fenced + "\n" + case_p, 1))
                self.assertEqual(p.returncode, 0, p.stderr)
                self.assertEqual(p.stdout.strip(), "2")

    def test_usage_exit2(self):
        p = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True)
        self.assertEqual(p.returncode, 2)


if __name__ == "__main__":
    unittest.main()
