#!/usr/bin/env python3
"""功能清單統計腳本的測試。直接執行：python3 test_feature_checklist.py"""
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "feature_checklist.py"

SAMPLE = """# 示範專案功能清單

總計：舊數字。

說明文字。

## 模組 A

完成 9／共 9。驗收見 phase1。

- [x] 新增 — 說明
- [ ] 🚧 匯入 — 部分完成
- [ ] 📋 匯出 — 見 docs/specs/export.md
- [-] 列印 — 不做：改用瀏覽器列印

## 模組 B

- [ ] 💡 通知 — 討論中提到（待確認）
- [ ] 沒標狀態的項目
- [x] 登入
"""


def load():
    spec = importlib.util.spec_from_file_location("fc", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestFeatureChecklist(unittest.TestCase):
    def setUp(self):
        self.fc = load()

    def test_counts(self):
        r = self.fc.analyze(SAMPLE)
        t = r["total"]
        self.assertEqual(t["done"], 2)
        self.assertEqual(t["doing"], 1)
        self.assertEqual(t["planned"], 1)
        self.assertEqual(t["idea"], 1)
        self.assertEqual(t["dropped"], 1)
        self.assertEqual(t["unlabeled"], 1)
        self.assertEqual(t["total"], 6)  # 不含決定不做
        self.assertEqual(r["sections"][0]["name"], "模組 A")
        self.assertEqual(r["sections"][0]["counts"]["total"], 3)
        self.assertEqual(len(r["pending"]), 1)
        self.assertEqual(len(r["unlabeled"]), 1)

    def test_write_updates_summary_and_subtotals(self):
        out = self.fc.rewrite(SAMPLE, today="2026-11-11")
        self.assertIn("總計：完成 2／共 6（另有 1 項決定不做）", out)
        self.assertIn("進行中 1、已規劃 1、構想 1、未分類 1；待確認 1 項。更新於 2026-11-11。", out)
        self.assertIn("完成 1／共 3。驗收見 phase1。", out)  # 保留小計後的文字
        self.assertIn("## 模組 B\n\n完成 1／共 3。\n\n- [ ] 💡", out)  # 缺小計就補
        self.assertNotIn("舊數字", out)
        self.assertEqual(self.fc.rewrite(out, today="2026-11-11"), out)  # 冪等

    def test_keeps_summary_prefix_and_skips_dropped_only_section(self):
        text = "# 清單\n\n依據 abc123。總計：舊。\n\n## A\n\n- [x] 甲\n\n## 決定不做\n\n共 1 項。\n\n- [-] 乙 — 理由\n"
        out = self.fc.rewrite(text, today="2026-11-11")
        self.assertIn("依據 abc123。總計：完成 1／共 1（另有 1 項決定不做）", out)
        self.assertEqual(out.count("總計："), 1)
        self.assertIn("## 決定不做\n\n共 1 項。", out)

    def test_open_lists_unfinished_by_section(self):
        out = subprocess.run([sys.executable, str(SCRIPT), "-", "--open"], input=SAMPLE,
                             capture_output=True, text=True, check=True).stdout
        self.assertIn("## 模組 A\n- [ ] 🚧 匯入", out)
        self.assertIn("- [ ] 📋 匯出", out)
        self.assertIn("## 模組 B\n- [ ] 💡 通知", out)
        self.assertIn("- [ ] 沒標狀態的項目", out)
        self.assertNotIn("新增", out)
        self.assertNotIn("列印", out)
        self.assertNotIn("完成 ", out)  # 只列項目，不印報表

    def test_check_mode_exit_codes(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "feature-checklist.md"
            p.write_text(SAMPLE, encoding="utf-8")
            stale = subprocess.run([sys.executable, str(SCRIPT), str(p), "--check"], capture_output=True, text=True)
            self.assertEqual(stale.returncode, 1, stale.stdout + stale.stderr)
            subprocess.run([sys.executable, str(SCRIPT), str(p), "--write"], check=True, capture_output=True)
            ok = subprocess.run([sys.executable, str(SCRIPT), str(p), "--check"], capture_output=True, text=True)
            self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)
            self.assertIn("未分類", ok.stdout)


if __name__ == "__main__":
    unittest.main()
