# -*- coding: utf-8 -*-
"""verify_roundtrip 的 Word COM 降級路徑測試。

CI（python:3.12-slim）沒有 pymupdf／numpy：缺的話塞空殼模組，只測不碰 PDF 的邏輯。
"""
import sys
import types
import unittest
from types import SimpleNamespace
from unittest import mock

for _name in ("fitz", "numpy"):
    try:
        __import__(_name)
    except ImportError:
        _stub = types.ModuleType(_name)
        _stub.Document = object  # 型別註記用
        _stub.Page = object
        sys.modules[_name] = _stub

import verify_roundtrip as vr  # noqa: E402


class DocxToPdfTest(unittest.TestCase):
    def test_no_pywin32_raises_word_unavailable(self):
        with mock.patch.dict(sys.modules, {"win32com": None, "win32com.client": None}):
            with self.assertRaises(vr.WordUnavailable):
                vr.docx_to_pdf("a.docx", "a.pdf")

    def test_dispatch_failure_raises_word_unavailable(self):
        client = types.ModuleType("win32com.client")
        client.Dispatch = mock.Mock(side_effect=OSError("Invalid class string"))
        pkg = types.ModuleType("win32com")
        pkg.client = client
        with mock.patch.dict(sys.modules, {"win32com": pkg, "win32com.client": client}):
            with self.assertRaises(vr.WordUnavailable):
                vr.docx_to_pdf("a.docx", "a.pdf")

    def test_word_available_path_unchanged(self):
        """有 Word 時照舊：Open → ExportAsFixedFormat(17) → Close(False) → Quit。"""
        doc = mock.Mock()
        word = mock.Mock()
        word.Documents.Open.return_value = doc
        client = types.ModuleType("win32com.client")
        client.Dispatch = mock.Mock(return_value=word)
        pkg = types.ModuleType("win32com")
        pkg.client = client
        with mock.patch.dict(sys.modules, {"win32com": pkg, "win32com.client": client}):
            vr.docx_to_pdf("a.docx", "a.pdf")
        client.Dispatch.assert_called_once_with("Word.Application")
        self.assertEqual(doc.ExportAsFixedFormat.call_args.args[1], 17)
        doc.Close.assert_called_once_with(False)
        word.Quit.assert_called_once()

    def test_open_error_with_word_still_raises(self):
        """Word 在但開檔失敗不算降級，照舊上拋。"""
        word = mock.Mock()
        word.Documents.Open.side_effect = RuntimeError("file locked")
        client = types.ModuleType("win32com.client")
        client.Dispatch = mock.Mock(return_value=word)
        pkg = types.ModuleType("win32com")
        pkg.client = client
        with mock.patch.dict(sys.modules, {"win32com": pkg, "win32com.client": client}):
            with self.assertRaises(RuntimeError) as cm:
                vr.docx_to_pdf("a.docx", "a.pdf")
        self.assertNotIsInstance(cm.exception, vr.WordUnavailable)
        word.Quit.assert_called_once()


class DegradedRunTest(unittest.TestCase):
    def _run(self, pdf, docx, text_mode="strict"):
        args = SimpleNamespace(original="o.pdf", docx="d.docx", outdir="out", text_mode=text_mode)
        with mock.patch.object(vr, "pdf_text", return_value=pdf), \
             mock.patch.object(vr, "docx_text", return_value=docx), \
             mock.patch.object(vr.fitz, "open", create=True):
            return vr.run_word_degraded(args, "ImportError: no win32com")

    def test_text_match_passes_and_marks_skipped(self):
        r = self._run("文件範例ABC", "文件範例ABC")
        self.assertEqual(r["verdict"], "pass")
        self.assertTrue(r["degraded"].startswith("word_com_unavailable"))
        self.assertIsNone(r["layout"]["pass"])
        self.assertIsNone(r["visual"]["pass"])

    def test_text_mismatch_is_hard_fail(self):
        r = self._run("文件範例ABC", "文件範例AB")
        self.assertEqual(r["verdict"], "hard_fail")
        self.assertEqual(r["text"]["missing"], ["C"])

    def test_report_only_never_fails(self):
        r = self._run("文件範例ABC", "{文件名稱}", text_mode="report-only")
        self.assertIsNone(r["text"]["pass"])
        self.assertEqual(r["verdict"], "pass")


if __name__ == "__main__":
    unittest.main()
