# -*- coding: utf-8 -*-
"""converter_select 測試：用模擬 env 驗證選擇邏輯，不依賴本機是否裝了 Word／LibreOffice。

CI（ubuntu）沒有 pymupdf／numpy：缺的話塞空殼模組，只測不碰 PDF 的邏輯。
"""
import os
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

for _name in ("fitz", "numpy"):
    try:
        __import__(_name)
    except ImportError:
        _stub = types.ModuleType(_name)
        _stub.Document = object
        _stub.Page = object
        sys.modules[_name] = _stub

import converter_select as cs  # noqa: E402
import verify_roundtrip as vr  # noqa: E402

HERE = Path(__file__).resolve().parent


class SelectConverterTest(unittest.TestCase):
    def test_windows_with_word(self):
        env = {"platform": "win32", "word_com": True, "soffice": None}
        self.assertEqual(cs.select_converter(env), "word")

    def test_windows_prefers_word_over_libreoffice(self):
        env = {"platform": "win32", "word_com": True, "soffice": "C:/lo/soffice.exe"}
        self.assertEqual(cs.select_converter(env), "word")

    def test_non_windows_with_soffice(self):
        env = {"platform": "linux", "word_com": False, "soffice": "/usr/bin/soffice"}
        self.assertEqual(cs.select_converter(env), "libreoffice")

    def test_windows_without_word_falls_back_to_libreoffice(self):
        env = {"platform": "win32", "word_com": False, "soffice": "C:/lo/soffice.exe"}
        self.assertEqual(cs.select_converter(env), "libreoffice")

    def test_neither_raises(self):
        env = {"platform": "linux", "word_com": False, "soffice": None}
        with self.assertRaises(cs.ConverterUnavailable):
            cs.select_converter(env)

    def test_word_flag_ignored_off_windows(self):
        env = {"platform": "linux", "word_com": True, "soffice": None}
        with self.assertRaises(cs.ConverterUnavailable):
            cs.select_converter(env)

    def test_detect_env_finds_soffice_on_path(self):
        with tempfile.TemporaryDirectory() as d:
            exe = Path(d) / "soffice"
            exe.write_text("#!/bin/sh\n")
            exe.chmod(0o755)
            with mock.patch.dict(os.environ, {"PATH": d}):
                env = cs.detect_env()
        self.assertEqual(Path(env["soffice"]).name, "soffice")


class CliTest(unittest.TestCase):
    @unittest.skipIf(sys.platform == "win32", "Windows 可能真的有 Word")
    @unittest.skipIf(os.path.exists(cs._MAC_SOFFICE), "本機 macOS 已裝 LibreOffice，PATH 清空仍找得到")
    def test_cli_exit_3_without_converter(self):
        with tempfile.TemporaryDirectory() as empty:
            # PATH 清空 → 找不到 soffice；非 Windows → 沒有 Word
            r = subprocess.run([sys.executable, "-B", str(HERE / "converter_select.py")],
                               env={"PATH": empty}, capture_output=True, text=True)
        self.assertEqual(r.returncode, 3)
        self.assertNotIn("Traceback", r.stderr)
        self.assertIn("LibreOffice", r.stderr)


class VerifyIntegrationTest(unittest.TestCase):
    def test_docx_to_pdf_libreoffice_invokes_soffice_headless(self):
        calls = []

        def fake_run(cmd, **kw):
            calls.append(cmd)
            outdir = cmd[cmd.index("--outdir") + 1]
            (Path(outdir) / "a.pdf").write_bytes(b"%PDF")
            return SimpleNamespace(returncode=0, stderr="")

        with tempfile.TemporaryDirectory() as d:
            docx, out = Path(d) / "a.docx", Path(d) / "out.pdf"
            docx.write_bytes(b"x")
            with mock.patch.object(vr.subprocess, "run", fake_run):
                vr.docx_to_pdf(str(docx), str(out), "libreoffice",
                               {"soffice": "/x/soffice"})
            self.assertTrue(out.exists())
        cmd = calls[0]
        self.assertEqual(cmd[0], "/x/soffice")
        self.assertIn("--headless", cmd)
        self.assertEqual(cmd[cmd.index("--convert-to") + 1], "pdf")

    def test_run_word_exit_3_path_raises_converter_unavailable(self):
        args = SimpleNamespace(original="o.pdf", docx="d.docx", outdir=tempfile.mkdtemp(),
                               text_mode="strict", allow_degraded=False, dpi=150)
        env = {"platform": "linux", "word_com": False, "soffice": None}
        with mock.patch.object(vr, "detect_env", return_value=env):
            with self.assertRaises(cs.ConverterUnavailable):
                vr.run_word(args)

    def test_allow_degraded_keeps_text_only_path(self):
        args = SimpleNamespace(original="o.pdf", docx="d.docx", outdir=tempfile.mkdtemp(),
                               text_mode="strict", allow_degraded=True, dpi=150)
        env = {"platform": "linux", "word_com": False, "soffice": None}
        with mock.patch.object(vr, "detect_env", return_value=env), \
             mock.patch.object(vr, "run_word_degraded", return_value={"verdict": "pass"}) as m:
            self.assertEqual(vr.run_word(args)["verdict"], "pass")
        m.assert_called_once()

    def test_main_exits_3_without_traceback(self):
        argv = ["verify_roundtrip.py", "word", "--original", "o.pdf", "--docx", "d.docx",
                "--outdir", tempfile.mkdtemp()]
        env = {"platform": "linux", "word_com": False, "soffice": None}
        err = []
        with mock.patch.object(sys, "argv", argv), \
             mock.patch.object(vr, "detect_env", return_value=env), \
             mock.patch.object(sys, "stderr", types.SimpleNamespace(write=err.append, flush=lambda: None)):
            with self.assertRaises(SystemExit) as cm:
                vr.main()
        self.assertEqual(cm.exception.code, 3)
        self.assertIn("LibreOffice", "".join(err))


if __name__ == "__main__":
    unittest.main()
