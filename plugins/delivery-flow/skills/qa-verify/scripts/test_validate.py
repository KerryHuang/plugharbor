#!/usr/bin/env python3
"""validate.py 的測試。直接執行：python3 test_validate.py"""
import unittest
from validate import (validate_plan, validate_fixtures, validate_run_ui,
                      validate_run_api, validate_steps,
                      validate_acceptance, parse_acceptance_md)

def plan(**over):
    d = {
        "meta": {
            "功能": "訂單分類檔", "功能碼": "ordercat", "票號": None,
            "規格": {"案例檔": {"路徑": "qa/cases.md", "sha": "99a11af0"}},
            "欄位對照": [{"規格": "分類代號", "實機": "訂單分類代碼", "信心": "確定"}],
            "互動模型": {"規格": "批量儲存", "實機": "逐列儲存", "一致": False},
        },
        "cases": [{
            "id": "TC-C-002", "欄位": "分類代號", "依賴互動模型": False,
            "來源": {"文件": "案例檔", "章節": "AC-1", "規則章節": "AC-1"},
            "執行器": "ui", "類型": "長度",
            "前置資料": [],
            "步驟": [{"動作": "navigate", "url": "/next/x"}],
            "預期": {"結果": "擋下", "訊息": "最多 3 個字元", "訊息比對": "逐字",
                     "欄位變化": [], "視覺標記": []},
            "寫入": "無",
        }],
    }
    d.update(over)
    return d

def ticket_plan():
    d = plan()
    d["meta"]["票號"] = "BUG-790"
    d["meta"]["規格"] = {"ticket": {"票號": "BUG-790", "updatedAt": "2026-10-01T08:00:00Z"}}
    d["cases"][0]["來源"] = {"文件": "ticket", "章節": "BUG-790 重現步驟", "規則章節": "BUG-790 預期結果"}
    return d

class TestPlan(unittest.TestCase):
    def test_valid_plan_passes(self):
        self.assertEqual(validate_plan(plan()), [])

    def test_empty_doc_is_error_not_pass(self):
        self.assertTrue(validate_plan({}))
        self.assertTrue(validate_plan(None))
        self.assertTrue(validate_plan({"meta": plan()["meta"], "cases": []}))

    def test_unknown_case_key_rejected(self):
        d = plan(); d["cases"][0]["備註"] = "x"
        self.assertTrue(any("未知鍵" in e for e in validate_plan(d)))

    def test_missing_expect_key_rejected(self):
        d = plan(); del d["cases"][0]["預期"]["訊息比對"]
        self.assertTrue(any("訊息比對" in e for e in validate_plan(d)))

    def test_enum_rejected(self):
        d = plan(); d["cases"][0]["預期"]["結果"] = "通過"
        self.assertTrue(any("結果" in e for e in validate_plan(d)))

    def test_duplicate_case_id_rejected(self):
        d = plan(); d["cases"].append(dict(d["cases"][0]))
        self.assertTrue(any("重複" in e for e in validate_plan(d)))

    def test_case_field_must_exist_in_mapping(self):
        d = plan(); d["cases"][0]["欄位"] = "不存在的欄位"
        self.assertTrue(any("欄位對照" in e for e in validate_plan(d)))

    def test_empty_steps_rejected(self):
        d = plan(); d["cases"][0]["步驟"] = []
        self.assertTrue(any("步驟" in e for e in validate_plan(d)))

    def test_case_file_null_rejected(self):
        d = plan(); d["meta"]["規格"]["案例檔"] = None
        self.assertTrue(any("案例檔" in e for e in validate_plan(d)))

    def test_case_file_with_invalid_keys_rejected(self):
        d = plan(); d["meta"]["規格"]["案例檔"] = {"foo": "bar"}
        self.assertTrue(any("未知鍵" in e for e in validate_plan(d)))

    def test_case_file_missing_sha_rejected(self):
        d = plan(); d["meta"]["規格"]["案例檔"]["sha"] = ""
        self.assertTrue(any("sha" in e for e in validate_plan(d)))

    def test_ticket_mode_passes(self):
        self.assertEqual(validate_plan(ticket_plan()), [])

    def test_ticket_mixed_with_case_file_rejected(self):
        d = ticket_plan(); d["meta"]["規格"]["案例檔"] = {"路徑": "qa/x.md", "sha": "abc"}
        self.assertTrue(any("未知鍵" in e for e in validate_plan(d)))

    def test_ticket_missing_updatedAt_rejected(self):
        d = ticket_plan(); del d["meta"]["規格"]["ticket"]["updatedAt"]
        self.assertTrue(any("updatedAt" in e for e in validate_plan(d)))

    def test_ticket_null_rejected(self):
        d = ticket_plan(); d["meta"]["規格"]["ticket"] = None
        self.assertTrue(any("ticket" in e for e in validate_plan(d)))

    def test_ticket_number_mismatch_rejected(self):
        d = ticket_plan(); d["meta"]["票號"] = "BUG-791"
        self.assertTrue(any("票號" in e for e in validate_plan(d)))

    def test_type_enum_includes_new_kinds(self):
        d = plan(); d["cases"][0]["類型"] = "範圍"
        self.assertEqual(validate_plan(d), [])
        d["cases"][0]["類型"] = "神奇"
        self.assertTrue(any("類型" in e for e in validate_plan(d)))

    def test_expect_result_disallows_process_values(self):
        d = plan(); d["cases"][0]["預期"]["結果"] = "不適用"
        self.assertTrue(any("結果" in e for e in validate_plan(d)))
        d["cases"][0]["預期"]["結果"] = "未送出"
        self.assertTrue(any("結果" in e for e in validate_plan(d)))

    def test_expect_result_only_擋下放行(self):
        d = plan()
        d["cases"][0]["預期"]["結果"] = "擋下"
        self.assertEqual(validate_plan(d), [])
        d["cases"][0]["預期"]["結果"] = "放行"
        self.assertEqual(validate_plan(d), [])

    def test_實機_allows_null(self):
        d = plan()
        d["meta"]["欄位對照"] = [{"規格": "分類代號", "實機": None, "信心": "找不到"}]
        d["cases"][0]["欄位"] = None
        self.assertEqual(validate_plan(d), [])

    def test_step_note_with_conclusive_text_rejected(self):
        d = plan()
        d["cases"][0]["步驟"][0]["注意"] = "結果記 不適用"
        self.assertTrue(any("注意 含結論性文字" in e for e in validate_plan(d)))

    def test_step_note_with_mechanical_text_allowed(self):
        d = plan()
        d["cases"][0]["步驟"][0]["注意"] = "先捲動到欄位再點擊"
        self.assertEqual(validate_plan(d), [])

    def test_step_target_with_spec_wording_rejected(self):
        d = plan()
        d["cases"][0]["步驟"][0]["目標"] = "規格所稱全域「儲存」按鈕"
        self.assertTrue(any("目標" in e and "含結論性文字" in e for e in validate_plan(d)))

def fixtures(**over):
    d = {
        "環境": {"url": "https://example.test/", "租戶": "示範公司",
               "允許寫入": False, "含個資": True, "依據": "config qa.environments[example-staging].writable=false",
               "查證": "[readonly-db example-staging] SELECT TOP 1 name FROM company"},
        "解析": [
            {"條件": "存在一筆訂單分類", "結果": "找到", "值": {"代碼": "CNC"}, "查詢": "SELECT ..."},
            {"條件": "存在被引用的分類", "結果": "無法備妥", "原因": "環境唯讀且查無"},
        ],
    }
    d.update(over)
    return d

class TestFixtures(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(validate_fixtures(fixtures()), [])

    def test_empty_is_error(self):
        self.assertTrue(validate_fixtures({}))

    def test_unavailable_needs_reason(self):
        d = fixtures(); del d["解析"][1]["原因"]
        self.assertTrue(any("原因" in e for e in validate_fixtures(d)))

    def test_created_needs_cleanup(self):
        d = fixtures()
        d["解析"][0] = {"條件": "x", "結果": "建立", "值": {"代碼": "QA01"}}
        self.assertTrue(any("清理" in e for e in validate_fixtures(d)))

    def test_writable_must_be_bool(self):
        d = fixtures(); d["環境"]["允許寫入"] = "no"
        self.assertTrue(any("允許寫入" in e for e in validate_fixtures(d)))

    def test_empty_fixtures_解析_allowed(self):
        d = fixtures(); d["解析"] = []
        self.assertEqual(validate_fixtures(d), [])

    def test_fixture_值_must_be_dict(self):
        d = fixtures(); d["解析"][0]["值"] = "invalid"
        self.assertTrue(any("值" in e for e in validate_fixtures(d)))

    def test_fixture_查詢_must_be_str(self):
        d = fixtures(); d["解析"][0]["查詢"] = 123
        self.assertTrue(any("查詢" in e for e in validate_fixtures(d)))

    def test_fixture_清理_must_be_dict(self):
        d = fixtures()
        d["解析"][0] = {"條件": "x", "結果": "建立", "值": {"代碼": "QA01"}, "清理": "invalid"}
        self.assertTrue(any("清理" in e for e in validate_fixtures(d)))

    def test_fixture_資料類別_removed(self):
        d = fixtures(); d["環境"]["資料類別"] = "內部"
        self.assertTrue(any("未知鍵" in e and "資料類別" in e for e in validate_fixtures(d)))

    def test_含個資_required_bool(self):
        d = fixtures(); del d["環境"]["含個資"]
        self.assertTrue(any("含個資" in e for e in validate_fixtures(d)))
        d = fixtures(); d["環境"]["含個資"] = "yes"
        self.assertTrue(any("含個資" in e for e in validate_fixtures(d)))

    def test_依據_required_nonempty(self):
        for bad in ("", "   ", None, 3):
            d = fixtures(); d["環境"]["依據"] = bad
            self.assertTrue(any("依據" in e for e in validate_fixtures(d)), bad)
        d = fixtures(); del d["環境"]["依據"]
        self.assertTrue(any("依據" in e for e in validate_fixtures(d)))

    def test_查證_optional(self):
        d = fixtures(); del d["環境"]["查證"]
        self.assertEqual(validate_fixtures(d), [])

    def test_查證_must_be_readonly_query(self):
        bad = ["看 banner", "config qa.environments[dev].writable=true", "", "   ",
               "DELETE FROM t", "UPDATE t SET a=1", "INSERT INTO t VALUES (1)",
               "SELECT 1; DELETE FROM t", "WITH x AS (SELECT 1) DELETE FROM t",
               "[readonly-db x] DROP TABLE t", "SELECT 1 -- ok\nEXEC sp_x"]
        for q in bad:
            d = fixtures(); d["環境"]["查證"] = q
            errs = validate_fixtures(d)
            self.assertTrue(any("查證" in e for e in errs), q)

    def test_查證_readonly_forms_pass(self):
        good = ["select top 1 * from x", "  WITH x AS (SELECT 1) SELECT * FROM x",
                "with x as (select 1) select * from x", "[DB工具 conn] SELECT 1",
                "  [DB工具 conn]   SELECT update_time FROM t", "SELECT 1;", "SELECT 1 ;; "]
        for q in good:
            d = fixtures(); d["環境"]["查證"] = q
            self.assertEqual(validate_fixtures(d), [], q)

def run_ui(**over):
    d = {"_meta": {"url": "x", "surveyed_at": "2026-09-12"},
         "rules": {"TC-C-002": {
             "結果": "放行", "訊息": None, "訊息位置": None,
             "欄位變化": [{"欄位": "訂單分類代碼", "變化": "值被帶入", "值": "ABCD"}],
             "視覺標記": [{"標記類型": "禁用", "對象欄位": "check 按鈕", "值": "disabled"}],
             "描述": "…", "步驟失敗次數": 0, "記錄讀值次數": 2,
             "網路": [{"方法": "GET", "路徑": "/api/x", "狀態碼": 200}]}}}
    d.update(over)
    return d

class TestRunUi(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(validate_run_ui(run_ui()), [])

    def test_empty_is_error(self):
        self.assertTrue(validate_run_ui({}))
        self.assertTrue(validate_run_ui({"_meta": {}, "rules": {}}))

    def test_null_count_rejected(self):
        d = run_ui(); d["rules"]["TC-C-002"]["步驟失敗次數"] = None
        self.assertTrue(any("步驟失敗次數" in e for e in validate_run_ui(d)))

    def test_null_result_only_with_step_failure(self):
        d = run_ui(); d["rules"]["TC-C-002"]["結果"] = None
        self.assertTrue(any("結果" in e for e in validate_run_ui(d)))
        d["rules"]["TC-C-002"]["步驟失敗次數"] = 2
        self.assertEqual(validate_run_ui(d), [])

    def test_prose_visual_mark_rejected(self):
        d = run_ui(); d["rules"]["TC-C-002"]["視覺標記"] = ["紅星出現在異常件數"]
        self.assertTrue(any("視覺標記" in e for e in validate_run_ui(d)))

    def test_unchanged_field_change_rejected(self):
        d = run_ui(); d["rules"]["TC-C-002"]["欄位變化"][0]["變化"] = "值未變"
        self.assertTrue(any("欄位變化" in e for e in validate_run_ui(d)))

    def test_bool_count_rejected(self):
        d = run_ui(); d["rules"]["TC-C-002"]["步驟失敗次數"] = True
        self.assertTrue(any("步驟失敗次數" in e for e in validate_run_ui(d)))

    def test_mark_type_啟用_allowed(self):
        d = run_ui()
        d["rules"]["TC-C-002"]["視覺標記"] = [{"標記類型": "啟用", "對象欄位": "check 按鈕", "值": "enabled"}]
        self.assertEqual(validate_run_ui(d), [])

class TestRunApi(unittest.TestCase):
    def test_valid(self):
        d = {"_meta": {"url": "x"}, "rules": {"TC-A-001": {
            "請求": {"方法": "POST", "路徑": "/api/x", "body摘要": "code=ABCD"},
            "回應": {"狀態碼": 400, "錯誤碼": "E001", "欄位": ["processGroupTypeCode"]}}}}
        self.assertEqual(validate_run_api(d), [])

    def test_missing_status_rejected(self):
        d = {"_meta": {}, "rules": {"TC-A-001": {"請求": {"方法": "GET", "路徑": "/x", "body摘要": None},
                                               "回應": {"錯誤碼": None, "欄位": []}}}}
        self.assertTrue(any("狀態碼" in e for e in validate_run_api(d)))

    def test_fields_must_be_list(self):
        d = {"_meta": {"url": "x"}, "rules": {"TC-A-001": {
            "請求": {"方法": "POST", "路徑": "/api/x", "body摘要": "code=ABCD"},
            "回應": {"狀態碼": 400, "錯誤碼": "E001", "欄位": "processGroupTypeCode"}}}}
        self.assertTrue(any("欄位" in e for e in validate_run_api(d)))

    def test_body_summary_must_be_str_or_null(self):
        d = {"_meta": {"url": "x"}, "rules": {"TC-A-001": {
            "請求": {"方法": "POST", "路徑": "/api/x", "body摘要": 123},
            "回應": {"狀態碼": 400, "錯誤碼": "E001", "欄位": []}}}}
        self.assertTrue(any("body摘要" in e for e in validate_run_api(d)))

    def test_error_code_must_be_str_or_null(self):
        d = {"_meta": {"url": "x"}, "rules": {"TC-A-001": {
            "請求": {"方法": "POST", "路徑": "/api/x", "body摘要": "code=ABCD"},
            "回應": {"狀態碼": 400, "錯誤碼": 123, "欄位": []}}}}
        self.assertTrue(any("錯誤碼" in e for e in validate_run_api(d)))

class TestSteps(unittest.TestCase):
    def test_valid(self):
        d = {"規格": {"案例檔_sha": "99a11af0"},
             "欄位對照": [{"規格": "分類代號", "實機": "訂單分類代碼", "信心": "確定"}],
             "cases": {"TC-C-002": [{"動作": "navigate", "url": "/x"}]}}
        self.assertEqual(validate_steps(d), [])

    def test_empty_case_steps_rejected(self):
        d = {"規格": {"案例檔_sha": "a"}, "欄位對照": [], "cases": {"TC-1": []}}
        self.assertTrue(any("TC-1" in e for e in validate_steps(d)))

    def test_empty_cases_dict_rejected(self):
        d = {"規格": {"案例檔_sha": "99a11af0"},
             "欄位對照": [{"規格": "分類代號", "實機": "訂單分類代碼", "信心": "確定"}],
             "cases": {}}
        self.assertTrue(any("必須是非空 dict" in e for e in validate_steps(d)))

    def test_step_note_with_conclusive_text_rejected(self):
        d = {"規格": {"案例檔_sha": "99a11af0"},
             "欄位對照": [{"規格": "分類代號", "實機": "訂單分類代碼", "信心": "確定"}],
             "cases": {"TC-C-002": [{"動作": "navigate", "url": "/x", "注意": "結果記 不適用"}]}}
        self.assertTrue(any("注意 含結論性文字" in e for e in validate_steps(d)))

class TestScreenAssertionSchema(unittest.TestCase):
    def test_plan_assertions_valid(self):
        d = plan()
        d["cases"][0]["預期"]["畫面斷言"] = [{"目標": "列數", "期望": "5", "比對": "等於"},
                                            {"目標": "欄:備註", "期望": None, "比對": "不存在"}]
        self.assertEqual(validate_plan(d), [])

    def test_plan_assertion_bad_enum_missing_expect_unknown_key(self):
        d = plan()
        d["cases"][0]["預期"]["畫面斷言"] = [{"目標": "列數", "期望": "5", "比對": "大於"}]
        self.assertTrue(any("比對" in e for e in validate_plan(d)))
        d["cases"][0]["預期"]["畫面斷言"] = [{"目標": "列數", "期望": None, "比對": "等於"}]
        self.assertTrue(any("期望" in e for e in validate_plan(d)))
        d["cases"][0]["預期"]["畫面斷言"] = [{"目標": "列數", "期望": "5", "比對": "等於", "備註": "x"}]
        self.assertTrue(any("未知鍵" in e for e in validate_plan(d)))
        d["cases"][0]["預期"]["畫面斷言"] = "列數 5"
        self.assertTrue(any("畫面斷言" in e for e in validate_plan(d)))

    def test_run_ui_old_and_new_format_valid(self):
        d = run_ui()
        self.assertEqual(validate_run_ui(d), [])
        d["rules"]["TC-C-002"]["畫面斷言"] = [{"目標": "列數", "實際": 5}, {"目標": "欄:備註", "實際": None}]
        self.assertEqual(validate_run_ui(d), [])

    def test_run_ui_assertion_bad(self):
        d = run_ui()
        d["rules"]["TC-C-002"]["畫面斷言"] = [{"目標": "列數"}]
        self.assertTrue(any("實際" in e for e in validate_run_ui(d)))
        d["rules"]["TC-C-002"]["畫面斷言"] = [{"目標": "列數", "實際": ["a"]}]
        self.assertTrue(any("實際" in e for e in validate_run_ui(d)))

    def test_run_ui_imprecise_steps_meta(self):
        d = run_ui()
        d["_meta"]["步驟不精確"] = [{"TC": "TC-C-002", "步驟": "click 查詢", "實機": "需先展開篩選列"}]
        self.assertEqual(validate_run_ui(d), [])
        d["_meta"]["步驟不精確"] = [{"TC": "TC-C-002", "步驟": "click 查詢"}]
        self.assertTrue(any("實機" in e for e in validate_run_ui(d)))

    def test_strip_passes_assertion_targets_only(self):
        from strip_plan import strip
        import json
        d = plan()
        d["cases"][0]["預期"]["畫面斷言"] = [{"目標": "列數", "期望": "5", "比對": "等於"}]
        out = strip(d)
        self.assertEqual(out["cases"][0]["畫面斷言目標"], ["列數"])
        self.assertNotIn("期望", json.dumps(out, ensure_ascii=False))


class TestStrip(unittest.TestCase):
    def test_strip_removes_expectations(self):
        from strip_plan import strip
        import json
        out = strip(plan())
        self.assertNotIn("預期", json.dumps(out, ensure_ascii=False))
        self.assertEqual(out["cases"][0]["實機欄位"], "訂單分類代碼")

    def test_strip_fails_loud_on_conclusive_note(self):
        from strip_plan import strip
        d = plan()
        d["cases"][0]["步驟"][0]["注意"] = "規格為批量儲存"
        with self.assertRaises(SystemExit):
            strip(d)

    def test_strip_fails_loud_on_spec_wording_in_target(self):
        from strip_plan import strip
        d = plan()
        d["cases"][0]["步驟"][0]["目標"] = "規格所稱全域「儲存」按鈕"
        with self.assertRaises(SystemExit):
            strip(d)


class TestDataAssertionSchema(unittest.TestCase):
    def test_plan_data_assertions_valid(self):
        d = plan()
        d["cases"][0]["預期"]["資料斷言"] = [{"目標": "WORK_ORDER.STATUS", "期望": "Y", "比對": "等於"}]
        self.assertEqual(validate_plan(d), [])

    def test_plan_data_assertion_bad(self):
        d = plan()
        d["cases"][0]["預期"]["資料斷言"] = [{"目標": "WORK_ORDER.STATUS", "期望": None, "比對": "等於"}]
        self.assertTrue(any("資料斷言" in e and "期望" in e for e in validate_plan(d)))

    def test_placeholder_expectation_rejected(self):
        """期望 寫 <該訂單明細之訂單單價> 之類佔位符，judge 會拿佔位符字面比對（曾造成假 FAIL）"""
        for slot in ("畫面斷言", "資料斷言"):
            d = plan()
            d["cases"][0]["預期"][slot] = [{"目標": "單價", "期望": "<該訂單明細之訂單單價>", "比對": "等於"}]
            self.assertTrue(any("佔位符" in e for e in validate_plan(d)), slot)

    def test_equals_target_must_reference_same_slot_target(self):
        d = plan()
        d["cases"][0]["預期"]["畫面斷言"] = [{"目標": "前", "期望": None, "比對": "存在"},
                                            {"目標": "後", "期望": "前", "比對": "等於目標"}]
        self.assertEqual(validate_plan(d), [])
        d["cases"][0]["預期"]["畫面斷言"] = [{"目標": "後", "期望": "前", "比對": "等於目標"}]
        self.assertTrue(any("等於目標" in e for e in validate_plan(d)))

    def test_db_check_valid_and_bad(self):
        from validate import validate_db_check
        ok = {"_meta": {"通道": "[readonly-db demo-staging]", "checked_at": "2026-10-05"},
              "rules": {"TC-C-002": [{"目標": "WORK_ORDER.STATUS", "實際": "Y", "查詢": "SELECT STATUS FROM WORK_ORDER"}]}}
        self.assertEqual(validate_db_check(ok), [])
        self.assertTrue(validate_db_check({}))
        bad = {"_meta": {}, "rules": {"TC-C-002": [{"目標": "WORK_ORDER.STATUS", "實際": "Y"}]}}
        self.assertTrue(any("通道" in e for e in validate_db_check(bad)))
        self.assertTrue(any("查詢" in e for e in validate_db_check(bad)))

    def test_strip_excludes_data_assertions_and_db_targets_lists_them(self):
        from strip_plan import strip, db_targets
        import json
        d = plan()
        d["cases"][0]["預期"]["資料斷言"] = [{"目標": "WORK_ORDER.STATUS", "期望": "Y", "比對": "等於"}]
        out = strip(d)
        self.assertNotIn("WORK_ORDER", json.dumps(out, ensure_ascii=False))
        t = db_targets(d)
        self.assertEqual(t["cases"]["TC-C-002"]["目標"], ["WORK_ORDER.STATUS"])
        self.assertNotIn("期望", json.dumps(t, ensure_ascii=False))
        self.assertEqual(db_targets(plan())["cases"], {})

MIN_MD = """# 示範功能

## AC-1 新增一筆資料 [ui]

### 步驟
1. 開啟清單頁，按「新增」

### 預期
- 出現空白表單
"""

FULL_MD = """## AC-2 代碼重複被擋 [api]

### 前置條件
- 已存在代碼 A01
- 帳號具新增權限

### 步驟
1. 開新增表單
2. 代碼填 A01，按儲存

### 預期
- 顯示「代碼重複」
- 資料未新增
"""


class TestNeutralFormat(unittest.TestCase):
    def test_neutral_format_minimal(self):
        """最小案例（1 步驟、1 預期、無前置）：YAML 與 markdown 都要過"""
        y = {"cases": [{"id": "AC-1", "title": "新增一筆資料",
                        "steps": ["開啟清單頁，按「新增」"], "expected": ["出現空白表單"]}]}
        self.assertEqual(validate_acceptance(y), [])
        doc = parse_acceptance_md(MIN_MD)
        self.assertEqual(validate_acceptance(doc), [])
        self.assertEqual(doc["cases"][0]["id"], "AC-1")
        self.assertEqual(doc["cases"][0]["channel"], "ui")
        self.assertEqual(doc["cases"][0].get("preconditions", []), [])

    def test_markdown_full_case(self):
        c = parse_acceptance_md(FULL_MD)["cases"][0]
        self.assertEqual(c["title"], "代碼重複被擋")
        self.assertEqual(c["channel"], "api")
        self.assertEqual(c["preconditions"], ["已存在代碼 A01", "帳號具新增權限"])
        self.assertEqual(c["steps"], ["開新增表單", "代碼填 A01，按儲存"])
        self.assertEqual(c["expected"], ["顯示「代碼重複」", "資料未新增"])
        self.assertEqual(validate_acceptance({"cases": [c]}), [])

    def test_markdown_without_channel_marker(self):
        doc = parse_acceptance_md(MIN_MD.replace(" [ui]", ""))
        self.assertNotIn("channel", doc["cases"][0])
        self.assertEqual(validate_acceptance(doc), [])

    def test_markdown_multiple_cases(self):
        self.assertEqual([c["id"] for c in parse_acceptance_md(MIN_MD + "\n" + FULL_MD)["cases"]],
                         ["AC-1", "AC-2"])

    def test_empty_rejected(self):
        for bad in (None, {}, {"cases": []}, "x"):
            self.assertTrue(validate_acceptance(bad), bad)

    def test_markdown_without_cases_rejected(self):
        self.assertTrue(validate_acceptance(parse_acceptance_md("# 只有標題\n")))

    def test_missing_steps_or_expected_rejected(self):
        for key in ("steps", "expected"):
            c = {"id": "AC-1", "title": "t", "steps": ["a"], "expected": ["b"]}
            c[key] = []
            self.assertTrue(any(key in e for e in validate_acceptance({"cases": [c]})), key)

    def test_duplicate_id_rejected(self):
        c = {"id": "AC-1", "title": "t", "steps": ["a"], "expected": ["b"]}
        self.assertTrue(any("重複" in e for e in validate_acceptance({"cases": [c, dict(c)]})))

    def test_unknown_key_and_bad_types_rejected(self):
        c = {"id": "AC-1", "title": "t", "steps": ["a"], "expected": ["b"], "foo": 1}
        self.assertTrue(any("未知鍵" in e for e in validate_acceptance({"cases": [c]})))
        c = {"id": "AC-1", "title": "t", "steps": "a", "expected": ["b"]}
        self.assertTrue(any("steps" in e for e in validate_acceptance({"cases": [c]})))
        c = {"id": "AC-1", "title": "t", "steps": ["a"], "expected": ["b"], "preconditions": "x"}
        self.assertTrue(any("preconditions" in e for e in validate_acceptance({"cases": [c]})))
        c = {"id": "AC-1", "title": "t", "steps": ["a"], "expected": ["b"], "channel": 3}
        self.assertTrue(any("channel" in e for e in validate_acceptance({"cases": [c]})))

    def test_missing_title_is_error(self):
        doc = parse_acceptance_md("## AC-x\n\n### 步驟\n1. a\n\n### 預期\n- b\n")
        self.assertTrue(any("title" in e for e in validate_acceptance(doc)))

    def test_non_case_h2_ends_case_without_merge(self):
        text = MIN_MD + "\n## 說明\n\n### 步驟\n1. 不屬於任何案例\n\n" + FULL_MD.replace("AC-2", "AC-3")
        doc = parse_acceptance_md(text)
        self.assertEqual([c["id"] for c in doc["cases"]], ["AC-1", "AC-3"])
        self.assertEqual(doc["cases"][0]["steps"], ["開啟清單頁，按「新增」"])
        self.assertEqual(validate_acceptance(doc), [])

    def test_section_aliases(self):
        doc = parse_acceptance_md("## AC-1 t\n### 前置條件\n- p\n### 步驟\n1. a\n### 預期結果\n- b\n")
        c = doc["cases"][0]
        self.assertEqual((c["preconditions"], c["expected"]), (["p"], ["b"]))

    def test_unknown_section_is_error(self):
        doc = parse_acceptance_md("## AC-1 t\n### 前提x\n- p\n### 步驟\n1. a\n### 預期\n- b\n")
        self.assertTrue(any("未知區段" in e and "前提x" in e for e in validate_acceptance(doc)))

    def test_fullwidth_colon_and_channel_lowercase(self):
        c = parse_acceptance_md("## AC-1：新增資料 [UI]\n### 步驟\n1. a\n### 預期\n- b\n")["cases"][0]
        self.assertEqual((c["id"], c["title"], c["channel"]), ("AC-1", "新增資料", "ui"))

    def test_code_fence_lines_ignored(self):
        text = "## AC-1 t\n### 步驟\n```\n## AC-9 假案例\n1. 假步驟\n```\n1. 真步驟\n### 預期\n- b\n"
        doc = parse_acceptance_md(text)
        self.assertEqual([c["id"] for c in doc["cases"]], ["AC-1"])
        self.assertEqual(doc["cases"][0]["steps"], ["真步驟"])

    def test_bom_file_and_yaml_syntax_error_via_cli(self):
        import os, subprocess, sys, tempfile
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "validate.py")
        with tempfile.TemporaryDirectory() as d:
            bom = os.path.join(d, "bom.md")
            with open(bom, "w", encoding="utf-8-sig") as f:
                f.write(MIN_MD)
            bad = os.path.join(d, "bad.yml")
            with open(bad, "w", encoding="utf-8") as f:
                f.write("cases: [unclosed\n  - : :\n")
            r = subprocess.run([sys.executable, script, "acceptance", bom], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = subprocess.run([sys.executable, script, "acceptance", bad], capture_output=True, text=True)
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
            self.assertNotIn("Traceback", r.stderr)

    def test_cli_accepts_markdown_and_yaml_files(self):
        import os, subprocess, sys, tempfile
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "validate.py")
        with tempfile.TemporaryDirectory() as d:
            md = os.path.join(d, "cases.md")
            with open(md, "w", encoding="utf-8") as f:
                f.write(MIN_MD)
            yml = os.path.join(d, "cases.yml")
            with open(yml, "w", encoding="utf-8") as f:
                f.write("cases:\n  - id: AC-1\n    title: t\n    steps: [a]\n    expected: [b]\n")
            bad = os.path.join(d, "bad.md")
            with open(bad, "w", encoding="utf-8") as f:
                f.write("# 空\n")
            for p, code in ((md, 0), (yml, 0), (bad, 1)):
                r = subprocess.run([sys.executable, script, "acceptance", p], capture_output=True, text=True)
                self.assertEqual(r.returncode, code, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
