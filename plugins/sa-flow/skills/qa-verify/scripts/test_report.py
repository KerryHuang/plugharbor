import datetime
import json
import os
import tempfile
import unittest
import yaml
from report import render_report, render_linear_comment, plan_patch, main, _fmt

VERDICT = {
    "cases": [
        {"id": "TC-C-002", "狀態": "FAIL", "歸因傾向": "疑似實作偏離", "備註": ["結果 預期 擋下，觀察 放行"],
         "證據": {"預期": {"結果": "擋下", "訊息": "最多 3 個字元", "訊息比對": "逐字", "欄位變化": [], "視覺標記": []},
                  "觀察": {"結果": "放行", "訊息": None, "訊息位置": None,
                           "欄位變化": [{"欄位": "訂單分類代碼", "變化": "值被帶入", "值": "ABCD"}], "視覺標記": []},
                  "api": None}},
        {"id": "TC-U-002", "狀態": "PASS", "歸因傾向": None, "備註": [],
         "證據": {"預期": {"結果": "擋下", "訊息": None, "訊息比對": "逐字", "欄位變化": [], "視覺標記": []},
                  "觀察": {"結果": "擋下", "訊息": None, "訊息位置": None, "欄位變化": [], "視覺標記": []}, "api": None}},
    ],
    "總計": {"PASS": 1, "FAIL": 1, "前端未擋": 0, "BLOCKED": 0, "未執行": 0, "無法比對": 0},
    "判讀": "有 1 條偏離、0 條後端待驗、0 條環境受阻，見「需要人決定的」",
    "規格校正": [{"類型": "欄位改名", "內容": "「分類代號」→「訂單分類代碼」"}],
    "全域訊號": {"欄位找不到": 1, "互動模型一致": False},
}
PLAN = {"meta": {"功能": "訂單分類檔", "功能碼": "ordercat", "票號": "PROJ-1",
                 "規格": {"ffs": {"路徑": "docs/f.md", "sha": "99a11af0"}, "bfs": None},
                 "欄位對照": [], "互動模型": {"規格": "批量", "實機": "逐列", "一致": False}},
        "cases": [{"id": "TC-C-002", "來源": {"文件": "ffs", "章節": "§8.2", "規則章節": "§4.1"}},
                  {"id": "TC-U-002", "來源": {"文件": "ffs", "章節": "§8.3", "規則章節": "§2.2"}}]}
FIX = {"環境": {"url": "https://example.test/", "租戶": "示範公司", "資料類別": "客戶副本",
               "允許寫入": False, "含個資": True, "查證": "SELECT 1"},
       "解析": [{"條件": "存在一筆訂單分類", "結果": "找到", "值": {"代碼": "CNC"}, "查詢": "SELECT ..."}]}
META = {"環境": "staging", "執行日期": "2026-09-12", "執行者": "tester", "模式": "唯讀", "含修復": False}

class TestReport(unittest.TestCase):
    def setUp(self):
        self.md = render_report(PLAN, FIX, VERDICT, META)

    def test_ticket_mode_header(self):
        import copy
        p = copy.deepcopy(PLAN)
        p["meta"]["票號"] = "BUG-790"
        p["meta"]["規格"] = {"ticket": {"票號": "BUG-790", "updatedAt": "2026-10-01T08:00:00Z"}}
        md = render_report(p, FIX, VERDICT, META)
        self.assertIn("來源 票面 BUG-790 @ 2026-10-01T08:00:00Z", md)
        self.assertNotIn("規格 FFS", md)

    def test_ffs_mode_header_unchanged(self):
        self.assertIn("規格 FFS 99a11af0", self.md)

    def test_summary_line_and_verdict(self):
        self.assertIn("PASS 1 / FAIL 1 / 前端未擋 0 / BLOCKED 0 / 未執行 0 / 無法比對 0", self.md)
        self.assertIn(VERDICT["判讀"], self.md)

    def test_needs_decision_table_has_empty_disposition(self):
        i = self.md.index("## 需要人決定的")
        sect = self.md[i:self.md.index("## ", i + 5)]
        self.assertIn("TC-C-002", sect); self.assertNotIn("TC-U-002", sect)
        self.assertIn("| 處置 |", sect)
        self.assertIn("開Bug｜改規格｜接受差異｜待PO裁決", sect)
        # 檢查 TC-C-002 行以空處置欄結尾
        lines = sect.split("\n")
        tc_line = [l for l in lines if "TC-C-002" in l][0]
        self.assertTrue(tc_line.rstrip().endswith("|  |"))

    def test_spec_correction_section(self):
        self.assertIn("## 規格校正清單", self.md)
        self.assertIn("「分類代號」→「訂單分類代碼」", self.md)

    def test_fix_section_absent_when_no_fix(self):
        self.assertNotIn("## 修復期間修正", self.md)

    def test_all_cases_collapsed(self):
        self.assertIn("<details>", self.md); self.assertIn("TC-U-002", self.md)

    def test_environment_section_masks_nothing_but_lists_fixtures(self):
        self.assertIn("示範公司", self.md); self.assertIn("CNC", self.md)

    def test_no_description_leaks(self):
        self.assertNotIn("描述", self.md)

    def test_global_signals_line(self):
        self.assertIn("全域訊號：欄位找不到 1｜互動模型 不一致", self.md)

    def test_environment_section_shows_pii_flag(self):
        self.assertIn("含個資：是", self.md)

    def test_collapsed_table_has_notes_column(self):
        i = self.md.index("## 全部 TC 逐條")
        sect = self.md[i:]
        self.assertIn("| TC | 狀態 | 證據 | 備註 |", sect)
        self.assertIn("結果 預期 擋下，觀察 放行", sect)

    def test_not_run_case_appears_in_needs_decision(self):
        """未執行案例應該出現在需要人決定表"""
        verdict = {
            "cases": [
                {"id": "TC-A", "狀態": "PASS", "歸因傾向": None, "備註": [],
                 "證據": {"預期": {"結果": "擋下", "訊息": None, "訊息比對": "逐字", "欄位變化": [], "視覺標記": []},
                          "觀察": {"結果": "擋下", "訊息": None, "訊息位置": None, "欄位變化": [], "視覺標記": []}, "api": None}},
                {"id": "TC-B", "狀態": "未執行", "歸因傾向": None, "備註": ["環境唯讀且此 TC 需寫入，未達可觀察點"],
                 "證據": {"預期": {"結果": "擋下", "訊息": None, "訊息比對": "逐字", "欄位變化": [], "視覺標記": []},
                          "觀察": None, "api": None}},
            ],
            "總計": {"PASS": 1, "FAIL": 0, "前端未擋": 0, "BLOCKED": 0, "未執行": 1, "無法比對": 0},
            "判讀": "有 1 條未執行",
            "規格校正": [],
            "全域訊號": {"欄位找不到": 0, "互動模型一致": True},
        }
        plan = {"meta": {"功能": "測試", "功能碼": "TST", "規格": {"ffs": {"sha": "abc"}, "bfs": None}, "欄位對照": [], "互動模型": {"規格": "批量", "實機": "逐列", "一致": False}},
                "cases": [{"id": "TC-A", "來源": {"文件": "ffs", "章節": "§1", "規則章節": "§1"}},
                          {"id": "TC-B", "來源": {"文件": "ffs", "章節": "§2", "規則章節": "§2"}}]}
        md = render_report(plan, FIX, verdict, META)
        self.assertIn("TC-B", md)
        i = md.index("## 需要人決定的")
        sect = md[i:md.index("## ", i + 5)]
        self.assertIn("TC-B", sect)
        self.assertIn("未執行", sect)

    def test_uncomparable_case_with_null_result_renders_dash(self):
        """無法比對且結果為 None 時應該顯示 — 而不是 None"""
        verdict = {
            "cases": [
                {"id": "TC-X", "狀態": "無法比對", "歸因傾向": "疑似規格過時", "備註": [],
                 "證據": {"預期": {"結果": "擋下", "訊息": None, "訊息比對": "逐字", "欄位變化": [], "視覺標記": []},
                          "觀察": {"結果": None, "訊息": None, "訊息位置": None, "欄位變化": [], "視覺標記": []}, "api": None}},
            ],
            "總計": {"PASS": 0, "FAIL": 0, "前端未擋": 0, "BLOCKED": 0, "未執行": 0, "無法比對": 1},
            "判讀": "有 1 條無法比對",
            "規格校正": [],
            "全域訊號": {"欄位找不到": 1, "互動模型一致": True},
        }
        plan = {"meta": {"功能": "測試", "功能碼": "TST", "規格": {"ffs": {"sha": "abc"}, "bfs": None}, "欄位對照": [], "互動模型": {"規格": "批量", "實機": "逐列", "一致": False}},
                "cases": [{"id": "TC-X", "來源": {"文件": "ffs", "章節": "§1", "規則章節": "§1"}}]}
        fixtures = {"環境": {"url": "https://x.test", "租戶": "測試", "資料類別": "副本", "允許寫入": False, "含個資": False, "查證": "SELECT 1"},
                    "解析": [{"條件": "前置", "結果": "無法備妥"}]}  # 沒有 原因 欄位
        md = render_report(plan, fixtures, verdict, META)
        # 應該有 → — 而不是 → None
        self.assertIn("→—", md)
        self.assertNotIn("None", md)
        # 原因應該顯示為 —
        self.assertIn("，原因 —", md)

class TestCollapsedTableNotes(unittest.TestCase):
    def test_semantic_pass_note_visible_in_collapsed_table(self):
        """D2：語意比對的 PASS 不進「需要人決定的」表，但備註（待人工確認）要能在摺疊表看到"""
        verdict = {
            "cases": [
                {"id": "TC-S", "狀態": "PASS", "歸因傾向": None,
                 "備註": ["訊息文字待人工確認：預期「此分類代號已存在」，觀察「訂單分類代碼不可重複」"],
                 "證據": {"預期": {"結果": "擋下", "訊息": "此分類代號已存在", "訊息比對": "語意", "欄位變化": [], "視覺標記": []},
                          "觀察": {"結果": "擋下", "訊息": "訂單分類代碼不可重複", "訊息位置": None,
                                   "欄位變化": [], "視覺標記": []}, "api": None}},
            ],
            "總計": {"PASS": 1, "FAIL": 0, "前端未擋": 0, "BLOCKED": 0, "未執行": 0, "無法比對": 0},
            "判讀": "通過",
            "規格校正": [],
            "全域訊號": {"欄位找不到": 0, "互動模型一致": True},
        }
        plan = {"meta": {"功能": "測試", "功能碼": "TST", "規格": {"ffs": {"sha": "abc"}, "bfs": None},
                         "欄位對照": [], "互動模型": {"規格": "批量", "實機": "逐列", "一致": True}},
                "cases": [{"id": "TC-S", "來源": {"文件": "ffs", "章節": "§1", "規則章節": "§1"}}]}
        md = render_report(plan, FIX, verdict, META)
        i = md.index("## 需要人決定的")
        needs_human = md[i:md.index("## ", i + 5)]
        self.assertNotIn("TC-S", needs_human)
        i2 = md.index("## 全部 TC 逐條")
        self.assertIn("待人工確認", md[i2:])


class TestScreenAssertionsAndDate(unittest.TestCase):
    def test_assertion_results_rendered_per_item(self):
        v = {"cases": [{"id": "TC-Q", "狀態": "FAIL", "歸因傾向": "疑似實作偏離", "備註": ["畫面斷言不成立：合計"],
                        "證據": {"預期": {"結果": "放行", "訊息": None, "訊息比對": "逐字", "欄位變化": [], "視覺標記": []},
                                 "觀察": {"結果": "放行", "訊息": None, "訊息位置": None, "欄位變化": [], "視覺標記": []},
                                 "畫面斷言": [{"目標": "列數", "期望": "5", "比對": "等於", "實際": 5, "結果": "通過"},
                                              {"目標": "合計", "期望": "100", "比對": "數值等於", "實際": "99", "結果": "不成立"},
                                              {"目標": "頁碼", "期望": "1", "比對": "等於", "實際": None, "結果": "無法比對"}],
                                 "api": None}}],
             "總計": {"PASS": 0, "FAIL": 1, "前端未擋": 0, "BLOCKED": 0, "未執行": 0, "無法比對": 0},
             "判讀": "x", "規格校正": [], "全域訊號": {"欄位找不到": 0, "互動模型一致": True}}
        plan = {"meta": PLAN["meta"], "cases": [{"id": "TC-Q", "來源": {"文件": "ffs", "章節": "§1", "規則章節": "§1"}}]}
        md = render_report(plan, FIX, v, META)
        self.assertIn("✓列數 等於 5→5", md)
        self.assertIn("✗合計 數值等於 100→99", md)
        self.assertIn("?頁碼 等於 1→—", md)

    def test_data_assertions_rendered(self):
        v = {"cases": [{"id": "TC-Q", "狀態": "PASS", "歸因傾向": None, "備註": [],
                        "證據": {"預期": {"結果": "放行", "訊息": None, "訊息比對": "逐字", "欄位變化": [], "視覺標記": []},
                                 "觀察": {"結果": "放行", "訊息": None, "訊息位置": None, "欄位變化": [], "視覺標記": []},
                                 "畫面斷言": [],
                                 "資料斷言": [{"目標": "WORK_ORDER.STATUS", "期望": "Y", "比對": "等於", "實際": "Y", "結果": "通過"}],
                                 "api": None}}],
             "總計": {"PASS": 1, "FAIL": 0, "前端未擋": 0, "BLOCKED": 0, "未執行": 0, "無法比對": 0},
             "判讀": "通過", "規格校正": [], "全域訊號": {"欄位找不到": 0, "互動模型一致": True}}
        plan = {"meta": PLAN["meta"], "cases": [{"id": "TC-Q", "來源": {"文件": "ffs", "章節": "§1", "規則章節": "§1"}}]}
        self.assertIn("資料斷言 ✓WORK_ORDER.STATUS 等於 Y→Y", render_report(plan, FIX, v, META))

    def test_fixtures_with_unquoted_date_do_not_crash(self):
        """yaml 會把 2026-09-30 解析成 date；json.dumps 沒 default=str 會 TypeError"""
        fix = {"環境": FIX["環境"], "解析": [{"條件": "x", "結果": "找到", "值": {"日期": datetime.date(2026, 9, 30)}}]}
        md = render_report(PLAN, fix, VERDICT, META)
        self.assertIn("2026-09-30", md)
        self.assertIn("2026-09-30", _fmt([datetime.date(2026, 9, 30)]))


class TestPlanPatch(unittest.TestCase):
    PP = {"cases": [{"id": "T1", "步驟": [{"動作": "navigate", "url": "/x"}, {"動作": "click", "目標": "查詢"}]},
                    {"id": "T2", "步驟": [{"動作": "click", "目標": "新增"}]}]}

    def test_steps_diff_and_imprecise_dedup(self):
        steps = {"cases": {"T1": [{"動作": "navigate", "url": "/x"}, {"動作": "click", "目標": "展開篩選"},
                                  {"動作": "click", "目標": "查詢"}],
                           "T2": [{"動作": "click", "目標": "新增", "注意": "先捲動"}]}}
        run = {"_meta": {"步驟不精確": [{"TC": "T1", "步驟": "click 查詢", "實機": "需先展開篩選"},
                                        {"TC": "T1", "步驟": "click 查詢", "實機": "需先展開篩選"}]}, "rules": {}}
        p = plan_patch(self.PP, steps, run)
        self.assertEqual([x["TC"] for x in p["修正"]], ["T1"])        # T2 只差 注意，簽章相同不算
        self.assertEqual(len(p["步驟不精確"]), 1)

    def test_no_inputs_gives_empty_patch_and_no_section(self):
        p = plan_patch(self.PP, None, None)
        self.assertEqual(p, {"修正": [], "步驟不精確": []})
        self.assertNotIn("計畫修正草稿", render_report(PLAN, FIX, VERDICT, META, patch=p))

    def test_report_has_patch_section_and_escapes_pipe(self):
        p = {"修正": [{"TC": "T1", "現行步驟": [], "實機步驟": []}],
             "步驟不精確": [{"TC": "T1", "步驟": "click 查詢", "實機": "需先展開|篩選"}]}
        md = render_report(PLAN, FIX, VERDICT, META, patch=p)
        self.assertIn("## 計畫修正草稿", md)
        self.assertIn("不符 1 條", md)
        self.assertIn("需先展開\\|篩選", md)

    def test_main_writes_plan_patch_yml_next_to_report(self):
        with tempfile.TemporaryDirectory() as d:
            def put(name, obj):
                with open(os.path.join(d, name), "w", encoding="utf-8") as f:
                    yaml.safe_dump(obj, f, allow_unicode=True)
            put("plan.yml", {"meta": PLAN["meta"], "cases": [{"id": "TC-C-002", "來源": PLAN["cases"][0]["來源"],
                                                              "步驟": [{"動作": "click", "目標": "查詢"}]}]})
            put("fix.yml", FIX)
            put("steps.yml", {"cases": {"TC-C-002": [{"動作": "click", "目標": "展開"}]}})
            with open(os.path.join(d, "v.json"), "w", encoding="utf-8") as f:
                json.dump(VERDICT, f, ensure_ascii=False)
            j = lambda n: os.path.join(d, n)
            rc = main(["report.py", j("plan.yml"), j("fix.yml"), j("v.json"), "--out", j("qa-report.md"),
                       "--env", "e", "--date", "2026-09-30", "--by", "k", "--mode", "唯讀", "--steps", j("steps.yml")])
            self.assertEqual(rc, 0)
            self.assertTrue(os.path.exists(j("plan-patch.yml")))
            with open(j("qa-report.md"), encoding="utf-8") as f:
                self.assertIn("計畫修正草稿", f.read())


class TestLinear(unittest.TestCase):
    def test_comment_is_short(self):
        s = render_linear_comment(PLAN, VERDICT, "docs/x/qa/qa-report.md")
        self.assertIn("PASS 1 / FAIL 1", s); self.assertIn("qa-report.md", s)
        self.assertNotIn("TC-U-002", s)          # 不貼逐條
        self.assertLess(len(s.splitlines()), 12)

    def test_comment_without_ref_has_no_report_line(self):
        s = render_linear_comment(PLAN, VERDICT)
        self.assertNotIn("報告：", s)

    def test_main_linear_does_not_print_local_out_path(self):
        import io, contextlib, tempfile, yaml
        with tempfile.TemporaryDirectory() as d:
            paths = {}
            for name, obj in (("plan.yml", PLAN), ("fixtures.yml", FIX)):
                paths[name] = os.path.join(d, name)
                with open(paths[name], "w", encoding="utf-8") as f:
                    yaml.safe_dump(obj, f, allow_unicode=True)
            vj = os.path.join(d, "verdict.json")
            with open(vj, "w", encoding="utf-8") as f:
                json.dump(VERDICT, f, ensure_ascii=False)
            out = os.path.join(d, "qa-report.md")
            base = ["report.py", paths["plan.yml"], paths["fixtures.yml"], vj, "--out", out, "--linear",
                    "--env", "w02", "--date", "2026-10-02", "--by", "t", "--mode", "唯讀"]
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                main(base)
            self.assertNotIn(d, buf.getvalue())
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                main(base + ["--report-ref", "docs/x/qa/qa-report.md"])
            self.assertIn("報告：docs/x/qa/qa-report.md", buf.getvalue())

if __name__ == "__main__":
    unittest.main()
