#!/usr/bin/env python3
"""操作手冊產線腳本的品牌參數化測試。直接執行：python3 test_manual_brand.py

- 品牌來源優先序：--brand > 設定 manual-brand > 空字串（不寫任何品牌）
- 腳本、skill、agent 與範本原始碼不得含 .leak-denylist 的字串（檔案不存在時只略過該項）
- manual-reference.docx 的 metadata 與內容不得有作者、公司資訊
"""
import importlib.util
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parent
ROOT = PLUGIN.parents[1]

MANUAL = """# 操作手冊：示範功能

| 項目 | 內容 |
|------|------|
| 功能名稱 | 示範功能 |
| 版本 | 1.0 |

## 1. 開始之前

內文。
"""


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_prep(cwd, *extra):
    src = Path(cwd) / "m.md"
    src.write_text(MANUAL, encoding="utf-8")
    out = Path(cwd) / "out.md"
    r = subprocess.run([sys.executable, str(HERE / "prep-docx-cover.py"), str(src), str(out), *extra],
                       cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    return out.read_text(encoding="utf-8")


def write_config(cwd, brand):
    d = Path(cwd) / ".plugharbor"
    d.mkdir()
    (d / "lifecycle.yml").write_text("manual-brand: %s\n" % brand, encoding="utf-8")


class DocxCoverBrand(unittest.TestCase):
    def test_brand_argument_appears_in_cover(self):
        with tempfile.TemporaryDirectory() as d:
            out = run_prep(d, "--brand", "Acme")
            self.assertIn('custom-style="CoverBrand"', out)
            self.assertIn("Acme", out)

    def test_no_brand_no_config_writes_no_brand(self):
        with tempfile.TemporaryDirectory() as d:
            out = run_prep(d)
            self.assertNotIn("CoverBrand", out)
            self.assertIn("CoverTitle", out)

    def test_brand_read_from_config(self):
        with tempfile.TemporaryDirectory() as d:
            write_config(d, "Beta")
            out = run_prep(d)
            self.assertIn("Beta", out)

    def test_argument_overrides_config(self):
        with tempfile.TemporaryDirectory() as d:
            write_config(d, "Beta")
            out = run_prep(d, "--brand", "Acme")
            self.assertIn("Acme", out)
            self.assertNotIn("Beta", out)

    def test_empty_brand_argument_suppresses_config(self):
        with tempfile.TemporaryDirectory() as d:
            write_config(d, "Beta")
            out = run_prep(d, "--brand", "")
            self.assertNotIn("CoverBrand", out)
            self.assertNotIn("Beta", out)


@unittest.skipUnless(importlib.util.find_spec("markdown"), "未安裝 markdown，略過 PDF 封面測試")
class PdfCoverBrand(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_module("build_manual_pdf", "build-manual-pdf.py")

    def render(self, cwd, brand):
        src = Path(cwd) / "m.md"
        src.write_text(MANUAL, encoding="utf-8")
        return self.mod.render_html(str(src), brand)

    def test_brand_in_cover(self):
        with tempfile.TemporaryDirectory() as d:
            html = self.render(d, "Acme")
            self.assertIn('<div class="brand">Acme</div>', html)

    def test_empty_brand_writes_no_brand_div(self):
        with tempfile.TemporaryDirectory() as d:
            html = self.render(d, "")
            self.assertNotIn('class="brand"', html)

    def test_brand_is_escaped(self):
        with tempfile.TemporaryDirectory() as d:
            html = self.render(d, "A<b>&Co")
            self.assertIn("A&lt;b&gt;&amp;Co", html)


class ScriptsSanity(unittest.TestCase):
    def test_shell_scripts_pass_bash_n_and_are_executable(self):
        for sh in HERE.glob("*.sh"):
            r = subprocess.run(["bash", "-n", str(sh)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, "%s: %s" % (sh.name, r.stderr))
            self.assertTrue(sh.stat().st_mode & 0o111, "%s 不可執行" % sh.name)

    def test_ensure_tools_checks_pillow(self):
        self.assertTrue("PIL:pillow" in (HERE / "ensure-tools.sh").read_text(encoding="utf-8"), "ensure-tools.sh 沒檢查 Pillow")

    def test_annotator_is_bundled(self):
        # lifecycle 要能單獨安裝：文件引用的標註器與換假資料工具必須在本 plugin 內
        for rel in ("scripts/annotate.py", "scripts/anonymize-page.js",
                    "references/annotate-spec.md", "references/anonymize-before-capture.md"):
            self.assertTrue((PLUGIN / rel).is_file(), rel)


class MissingDependencyHint(unittest.TestCase):
    """依賴缺失時要一行提示與正確退出碼，不是 traceback。"""

    def run_blocked(self, script, blocked, *args):
        code = ("import sys, runpy\n"
                "sys.path.insert(0, %r)\n"
                "for m in %r: sys.modules[m] = None\n"
                "sys.argv = [%r] + %r\n"
                "runpy.run_path(%r, run_name='__main__')\n") % (str(HERE), blocked, script, list(args), str(HERE / script))
        return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, encoding="utf-8")

    def test_pdf_build_without_markdown_gives_hint(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "m.md"
            src.write_text(MANUAL, encoding="utf-8")
            r = self.run_blocked("build-manual-pdf.py", ["markdown"], str(src), "--brand", "")
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn("Traceback", r.stderr)
        self.assertIn("pip install markdown", r.stderr)

    def test_stamp_without_fitz_gives_hint(self):
        r = self.run_blocked("build-manual-pdf.py", ["fitz"], "--help")
        self.assertEqual(r.returncode, 0)  # --help 不需要 fitz，確認腳本頂層沒有硬 import
        code = ("import sys, importlib.util\nsys.path.insert(0, %r)\nsys.modules['fitz'] = None\n"
                "spec = importlib.util.spec_from_file_location('b', %r)\n"
                "m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)\n"
                "m.stamp_page_numbers('x.pdf')\n") % (str(HERE), str(HERE / "build-manual-pdf.py"))
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, encoding="utf-8")
        self.assertNotIn("Traceback", r.stderr)
        self.assertIn("pip install pymupdf", r.stderr)

    def test_overflow_check_without_pillow_exits_2(self):
        with tempfile.TemporaryDirectory() as d:
            pdf = Path(d) / "x.pdf"
            pdf.write_bytes(b"%PDF-1.4\n")
            r = self.run_blocked("check-deck-overflow.py", ["PIL"], str(pdf))
        self.assertEqual(r.returncode, 2)
        self.assertNotIn("Traceback", r.stderr)
        self.assertIn("pip install pillow", r.stdout)

    def test_overflow_check_corrupt_pdf_exits_2(self):
        if importlib.util.find_spec("PIL") is None:
            self.skipTest("未安裝 Pillow")
        with tempfile.TemporaryDirectory() as d:
            pdf = Path(d) / "bad.pdf"
            pdf.write_text("not a pdf", encoding="utf-8")
            r = self.run_blocked("check-deck-overflow.py", [], str(pdf))
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertNotIn("Traceback", r.stderr)

    def test_overflow_check_missing_pdf_exits_2(self):
        if importlib.util.find_spec("PIL") is None:
            self.skipTest("未安裝 Pillow")
        r = self.run_blocked("check-deck-overflow.py", [], str(HERE / "nope.pdf"))
        self.assertEqual(r.returncode, 2)
        self.assertNotIn("Traceback", r.stderr)


def load_denylist():
    f = ROOT / ".leak-denylist"
    if not f.is_file():
        return None
    pats = []
    for line in f.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        pats.append(re.compile(line[len("regex:"):]) if line.startswith("regex:") else re.compile(re.escape(line)))
    return pats


def shipped_files():
    out = [p for p in HERE.iterdir() if p.is_file() and p.suffix in {".py", ".sh", ".css", ".docx"}]
    out += [p for p in (PLUGIN / "skills" / "operation-manual").rglob("*") if p.is_file()]
    out += list((PLUGIN / "agents").glob("manual-*.md"))
    return sorted(out)


def texts_of(path):
    """docx 展開成各個 zip 部件的文字，其餘直接讀。"""
    if path.suffix == ".docx":
        with zipfile.ZipFile(path) as z:
            return [z.read(n).decode("utf-8", "replace") for n in z.namelist()]
    return [path.read_text(encoding="utf-8", errors="replace")]


class Leaks(unittest.TestCase):
    def test_denylist_has_no_hit_in_shipped_files(self):
        pats = load_denylist()
        if pats is None:
            self.skipTest("沒有 .leak-denylist（CI 環境），略過本項；其餘斷言照跑")
        hits = {}
        for path in shipped_files():
            n = sum(len(p.findall(t)) for t in texts_of(path) for p in pats)
            if n:
                hits[str(path.relative_to(ROOT))] = n
        # 只印命中數與檔案路徑，不印黑名單內容
        self.assertEqual(hits, {}, "denylist 命中（檔案: 次數）")

    def test_reference_docx_has_no_author_metadata(self):
        docx = HERE / "manual-reference.docx"
        with zipfile.ZipFile(docx) as z:
            core = z.read("docProps/core.xml").decode("utf-8") if "docProps/core.xml" in z.namelist() else ""
            app = z.read("docProps/app.xml").decode("utf-8") if "docProps/app.xml" in z.namelist() else ""
        for tag in ("dc:creator", "cp:lastModifiedBy"):
            m = re.search(r"<%s[^>]*>([^<]*)</%s>" % (tag, tag), core)
            self.assertTrue(m is None or m.group(1).strip() in ("", "unknown"), "%s 不是空或通用值" % tag)
        m = re.search(r"<Company>([^<]*)</Company>", app)
        self.assertTrue(m is None or m.group(1).strip() == "", "Company 不是空值")


if __name__ == "__main__":
    unittest.main()
