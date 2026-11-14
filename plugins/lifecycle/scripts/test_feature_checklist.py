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

ROADMAP = """# Roadmap

### 工作段

| 工作段 | 內容 | 狀態 |
|---|---|---|
| t1a | 任務 | 已上線（含補強） |
| p1 | 公開 repo | 進行中 |

### 簽核

| 工作段 | 內容 | 狀態 |
|---|---|---|
| a2c、a2d | 重新比對 | 未開始 |
| p2 | Demo | 未開始 |
| p2 | 重複 | 未開始 |
"""

DEPS = """# 清單

Roadmap：[roadmap](specs/roadmap.md#工作段)

## A

- [x] 甲（段 a2c） — 已勾但 roadmap 未開始
- [ ] 📋 丙（段 a2c） — 第二順位
- [ ] 📋 乙（段 p1） — 第一順位
- [ ] 📋 戊（段 t1a） — roadmap 已上線
- [ ] 📋 丁 — 說明 ⛔ 等：p2、裁決 C1
- [ ] 💡 己 — ⛔ 等：不存在
- [ ] 📋 庚 — ⛔ 等：甲
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

    def test_open_lists_ready_items_with_section(self):
        out = subprocess.run([sys.executable, str(SCRIPT), "-", "--open"], input=SAMPLE,
                             capture_output=True, text=True, check=True).stdout
        ready, unplanned = out.split("## 未排段")  # 沒 roadmap：非 💡 都可開工，💡 歸未排段
        self.assertTrue(ready.startswith("## 可開工\n\n- [ ] 🚧 匯入"))
        self.assertIn("- [ ] 📋 匯出 — 見 docs/specs/export.md［模組 A］", ready)
        self.assertIn("- [ ] 沒標狀態的項目［模組 B］", ready)
        self.assertIn("- [ ] 💡 通知", unplanned)
        self.assertNotIn("新增", out)
        self.assertNotIn("列印", out)
        self.assertNotIn("被擋", out)
        self.assertNotIn("完成 ", out)  # 只列項目，不印報表

    def test_roadmap_order_blockers_and_drift(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "specs").mkdir()
            (d / "specs" / "roadmap.md").write_text(ROADMAP, encoding="utf-8")
            p = d / "feature-checklist.md"
            p.write_text(DEPS, encoding="utf-8")
            run = lambda *a: subprocess.run([sys.executable, str(SCRIPT), str(p), *a], capture_output=True, text=True)
            out = run("--open").stdout
            ready, rest = out.split("## 依序等待")
            queued, rest = rest.split("## 被擋")
            blocked, unplanned = rest.split("## 未排段")
            # 第一個未完成段是 p1：t1a（已上線但未勾）與 p1 可開工，a2c 排後面
            self.assertLess(ready.index("戊"), ready.index("乙"))
            self.assertIn("丙", queued)
            self.assertNotIn("丙", ready)
            self.assertIn("庚", unplanned)  # 等的已完成，但沒段號＝未排段
            self.assertIn("丁", blocked)
            self.assertIn("← 等：p2、裁決 C1", blocked)
            self.assertIn("己", blocked)  # 💡 被擋仍列被擋
            rep = run()
            self.assertIn("庚：等「甲」已完成，可刪 ⛔", rep.stdout)
            self.assertIn("找不到「不存在」", rep.stdout)
            self.assertIn("甲：清單已勾，roadmap 段 a2c 是「未開始」", rep.stdout)
            self.assertIn("戊：roadmap 段 t1a 是「已上線（含補強）」，清單未勾", rep.stdout)
            self.assertNotIn("丙：", rep.stdout)  # a2c 未開始、清單未勾＝一致
            self.assertIn("roadmap 段號重複：p2", rep.stdout)
            subprocess.run([sys.executable, str(SCRIPT), str(p), "--write"], check=True, capture_output=True)
            self.assertEqual(run("--check").returncode, 1)  # 數字對了，但不同步仍失敗

    def test_parallel_window_and_order_conflict(self):
        roadmap = ("| 工作段 | 內容 | 狀態 | 設計 |\n|---|---|---|---|\n"
                   "| d1 | 已做 | 已上線 | [d](d.md) |\n"
                   "| m1 | 主線 | 未開始 | [m](m.md) |\n"
                   "| x1 | 有設計 | 未開始 | [x1](x1.md) |\n"
                   "| x2 | 佔位 | 未開始（設計待寫） | — |\n"
                   "| x3 | 有設計但等後面 | 未開始 | [x3](x3.md) |\n"
                   "| x4 | 窗外 | 未開始 | [x4](x4.md) |\n")
        checklist = ("# 清單\n\n## A\n\n"
                     "- [ ] 📋 主（段 m1）\n- [ ] 📋 平甲（段 x1）\n- [ ] 📋 佔（段 x2）\n"
                     "- [ ] 📋 平乙（段 x3） — ⛔ 等：x4\n- [ ] 📋 遠（段 x4）\n")
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "roadmap.md").write_text(roadmap, encoding="utf-8")
            p = d / "feature-checklist.md"
            p.write_text(checklist, encoding="utf-8")
            out = subprocess.run([sys.executable, str(SCRIPT), str(p), "--open"],
                                 capture_output=True, text=True, check=True).stdout
            ready, rest = out.split("## 可平行")
            parallel, rest = rest.split("## 依序等待")
            queued, rest = rest.split("## 被擋")
            self.assertIn("主", ready)
            self.assertIn("平甲", parallel)  # 往後 3 段內、有設計、沒被擋
            self.assertNotIn("佔", parallel)  # 佔位段（沒設計連結）不平行
            self.assertIn("佔", queued)
            self.assertIn("遠", queued)  # 窗外（第 4 段）照順序等
            self.assertNotIn("平乙", parallel)
            self.assertIn("平乙", rest)  # 被擋
            self.assertIn("## 列序矛盾", rest)
            self.assertIn("平乙（段 x3）排在段 x4 前面，卻等 x4", rest)

    def test_default_sibling_roadmap(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "roadmap.md").write_text(ROADMAP, encoding="utf-8")
            p = d / "feature-checklist.md"
            p.write_text("# 清單\n\n## A\n\n- [ ] 📋 乙（段 a2d）\n- [ ] 📋 甲（段 p1）\n", encoding="utf-8")
            out = subprocess.run([sys.executable, str(SCRIPT), str(p), "--open"],
                                 capture_output=True, text=True, check=True).stdout
            # 沒寫連結也讀到同目錄 roadmap.md；a2d 與 a2c 同列，排在 p1 之後
            self.assertLess(out.index("甲"), out.index("依序等待"))
            self.assertLess(out.index("依序等待"), out.index("乙"))

    def test_missing_roadmap_link_fails(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "feature-checklist.md"
            p.write_text("# 清單\n\nRoadmap：[roadmap](nope.md)\n", encoding="utf-8")
            r = subprocess.run([sys.executable, str(SCRIPT), str(p)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("找不到 roadmap", r.stderr)

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
