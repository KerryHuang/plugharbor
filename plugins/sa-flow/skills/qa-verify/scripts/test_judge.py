import unittest
from judge import judge, STATUS_VALUES

def mk_plan(cases, mapping=None, model_ok=True):
    return {"meta": {"功能": "x", "功能碼": "X", "票號": None,
                     "規格": {"ffs": {"路徑": "f", "sha": "abc"}, "bfs": None},
                     "欄位對照": mapping if mapping is not None else
                         [{"規格": "分類代號", "實機": "訂單分類代碼", "信心": "確定"}],
                     "互動模型": {"規格": "批量", "實機": "逐列", "一致": model_ok}},
            "cases": cases}

def mk_case(cid, 結果="擋下", 訊息=None, 比對="逐字", 寫入="無", 欄位="分類代號",
            依賴=False, 前置=None, 欄位變化=None, 視覺標記=None):
    return {"id": cid, "欄位": 欄位, "依賴互動模型": 依賴,
            "來源": {"文件": "ffs", "章節": "§8", "規則章節": "§4"},
            "執行器": "ui", "類型": "必填", "前置資料": 前置 or [],
            "步驟": [{"動作": "navigate", "url": "/x"}],
            "預期": {"結果": 結果, "訊息": 訊息, "訊息比對": 比對,
                     "欄位變化": 欄位變化 or [], "視覺標記": 視覺標記 or []},
            "寫入": 寫入}

def mk_fix(writable=True, items=None):
    return {"環境": {"url": "u", "租戶": "t", "資料類別": "內部", "允許寫入": writable, "查證": "SELECT 1"},
            "解析": items or []}

def mk_obs(結果="擋下", 訊息=None, 位置=None, 失敗=0, 欄位變化=None, 視覺標記=None):
    return {"結果": 結果, "訊息": 訊息, "訊息位置": 位置, "欄位變化": 欄位變化 or [],
            "視覺標記": 視覺標記 or [], "描述": "不可被讀", "步驟失敗次數": 失敗, "記錄讀值次數": 1, "網路": []}

def mk_run(**rules):
    return {"_meta": {}, "rules": rules}

class TestStatus(unittest.TestCase):
    def one(self, case, obs, fix=None, plan_kw=None, api=None):
        r = judge(mk_plan([case], **(plan_kw or {})), fix or mk_fix(), mk_run(**{case["id"]: obs}), api)
        return r["cases"][0]

    def test_pass_exact_message(self):
        c = self.one(mk_case("T1", 訊息="請輸入分類代號"), mk_obs(訊息="請輸入分類代號", 位置="欄位下方"))
        self.assertEqual(c["狀態"], "PASS")

    def test_fail_on_result_mismatch(self):
        c = self.one(mk_case("T1"), mk_obs(結果="放行"))
        self.assertEqual(c["狀態"], "FAIL")
        self.assertEqual(c["歸因傾向"], "疑似實作偏離")

    def test_fail_on_exact_message_mismatch(self):
        c = self.one(mk_case("T1", 訊息="此分類代號已存在"), mk_obs(訊息="訂單分類代碼不可重複"))
        self.assertEqual(c["狀態"], "FAIL")

    def test_exact_message_fails_when_observed_contains_expected_as_substring(self):
        """殺突變 C：逐字比對改成子字串包含會讓這條變綠"""
        c = self.one(mk_case("T1", 訊息="請輸入分類代號"), mk_obs(訊息="錯誤：請輸入分類代號"))
        self.assertEqual(c["狀態"], "FAIL")

    def test_semantic_message_passes_when_any_message_and_flags_for_human(self):
        c = self.one(mk_case("T1", 訊息="此分類代號已存在", 比對="語意"), mk_obs(訊息="訂單分類代碼不可重複"))
        self.assertEqual(c["狀態"], "PASS")
        self.assertTrue(any("待人工確認" in n for n in c["備註"]))

    def test_semantic_message_fails_when_no_message(self):
        c = self.one(mk_case("T1", 訊息="x", 比對="語意"), mk_obs(訊息=None))
        self.assertEqual(c["狀態"], "FAIL")

    def test_frontend_not_blocking_on_readonly_env(self):
        c = self.one(mk_case("T1", 寫入="建立"), mk_obs(結果="放行"), fix=mk_fix(writable=False))
        self.assertEqual(c["狀態"], "前端未擋")

    def test_readonly_write_case_not_reached_is_not_run(self):
        c = self.one(mk_case("T1", 寫入="建立"), mk_obs(結果="未送出"), fix=mk_fix(writable=False))
        self.assertEqual(c["狀態"], "未執行")

    def test_readonly_write_pass_result_but_never_submitted_is_not_run(self):
        """C5：唯讀＋寫入≠無，obs 放行 且 exp 放行 → 未執行（從未真送出），不是 PASS"""
        c = self.one(mk_case("T1", 寫入="建立", 結果="放行"), mk_obs(結果="放行"), fix=mk_fix(writable=False))
        self.assertEqual(c["狀態"], "未執行")
        self.assertTrue(any("未真送出" in n or "未達可觀察點" in n for n in c["備註"]))

    def test_readonly_write_blocked_result_falls_through_to_normal_compare(self):
        """C5：唯讀＋寫入≠無，obs 擋下 → 依一般規則比對（可 PASS）"""
        c = self.one(mk_case("T1", 寫入="建立", 結果="擋下"), mk_obs(結果="擋下"), fix=mk_fix(writable=False))
        self.assertEqual(c["狀態"], "PASS")

    def test_observed_not_applicable_is_uncomparable(self):
        """C4：觀察 結果 == 不適用 → 無法比對，不是拿來跟預期比對出 PASS/FAIL"""
        c = self.one(mk_case("T1"), mk_obs(結果="不適用"))
        self.assertEqual(c["狀態"], "無法比對")
        self.assertTrue(any("工具無法觸發此情境" in n for n in c["備註"]))

    def test_writable_env_write_case_judged_normally(self):
        c = self.one(mk_case("T1", 寫入="建立"), mk_obs(結果="放行"), fix=mk_fix(writable=True))
        self.assertEqual(c["狀態"], "FAIL")

    def test_blocked_when_fixture_unavailable(self):
        case = mk_case("T1", 前置=[{"條件": "存在被引用的分類", "用途": "刪除"}])
        fix = mk_fix(items=[{"條件": "存在被引用的分類", "結果": "無法備妥", "原因": "查無"}])
        c = self.one(case, mk_obs(), fix=fix)
        self.assertEqual(c["狀態"], "BLOCKED")

    def test_not_run_when_model_mismatch_and_dependent(self):
        c = self.one(mk_case("T1", 依賴=True), mk_obs(), plan_kw={"model_ok": False})
        self.assertEqual(c["狀態"], "未執行")

    def test_uncomparable_when_field_unmapped(self):
        mapping = [{"規格": "排列順序", "實機": None, "信心": "找不到"}]
        c = self.one(mk_case("T1", 欄位="排列順序"), mk_obs(結果="不適用"), plan_kw={"mapping": mapping})
        self.assertEqual(c["狀態"], "無法比對")
        self.assertEqual(c["歸因傾向"], "疑似規格過時")

    def test_uncomparable_when_steps_failed_without_observation(self):
        c = self.one(mk_case("T1"), mk_obs(結果=None, 失敗=2))
        self.assertEqual(c["狀態"], "無法比對")

    def test_expected_field_change_must_be_observed(self):
        case = mk_case("T1", 結果="放行", 欄位變化=[{"欄位": "分類代號", "變化": "值被轉換", "值": "A01"}])
        c = self.one(case, mk_obs(結果="放行"))
        self.assertEqual(c["狀態"], "FAIL")
        c2 = self.one(case, mk_obs(結果="放行", 欄位變化=[{"欄位": "訂單分類代碼", "變化": "值被轉換", "值": "A01"}]))
        self.assertEqual(c2["狀態"], "PASS")   # 觀察用實機欄名，透過 欄位對照 對回規格欄名

    def test_produced_value_null_is_not_pass(self):
        """案例：預期「值被帶入、值 null」＝需產出任意值；讀回 null 仍判 PASS 會讓下游斷鏈"""
        case = mk_case("T1", 結果="放行", 欄位變化=[{"欄位": "訂單號", "變化": "值被帶入", "值": None}])
        c = self.one(case, mk_obs(結果="放行", 欄位變化=[{"欄位": "訂單號", "變化": "值被帶入", "值": None}]))
        self.assertEqual(c["狀態"], "FAIL")
        c2 = self.one(case, mk_obs(結果="放行", 欄位變化=[{"欄位": "訂單號", "變化": "值被帶入", "值": ""}]))
        self.assertEqual(c2["狀態"], "FAIL")
        c3 = self.one(case, mk_obs(結果="放行", 欄位變化=[{"欄位": "訂單號", "變化": "值被帶入", "值": "ORD-0001"}]))
        self.assertEqual(c3["狀態"], "PASS")

    def test_cleared_value_null_still_matches(self):
        case = mk_case("T1", 結果="放行", 欄位變化=[{"欄位": "分類代號", "變化": "值被清空", "值": None}])
        c = self.one(case, mk_obs(結果="放行", 欄位變化=[{"欄位": "訂單分類代碼", "變化": "值被清空", "值": None}]))
        self.assertEqual(c["狀態"], "PASS")

    def test_expected_visual_mark_must_be_observed(self):
        case = mk_case("T1", 結果="放行", 視覺標記=[{"標記類型": "禁用", "對象欄位": "分類代號", "值": None}])
        c = self.one(case, mk_obs(結果="放行", 視覺標記=[{"標記類型": "禁用", "對象欄位": "訂單分類代碼", "值": "disabled"}]))
        self.assertEqual(c["狀態"], "PASS")

    def test_visual_mark_matches_when_expected_uses_real_field_name(self):
        """判 1：expected 對象欄位 用實機名時也要正規化——舊 bug 只正規化 observed 那側，
        導致 {禁用, 訂單分類代碼}（expected，實機名）vs {禁用, 訂單分類代碼, readonly}（observed）誤判 FAIL"""
        case = mk_case("T1", 結果="放行",
                       視覺標記=[{"標記類型": "禁用", "對象欄位": "訂單分類代碼", "值": None}])
        c = self.one(case, mk_obs(結果="放行",
                                  視覺標記=[{"標記類型": "禁用", "對象欄位": "訂單分類代碼", "值": "readonly"}]))
        self.assertEqual(c["狀態"], "PASS")

    def test_visual_mark_matches_when_expected_uses_spec_field_name(self):
        """判 1 對稱情境：expected 用規格名、observed 用實機名 → PASS"""
        case = mk_case("T1", 結果="放行",
                       視覺標記=[{"標記類型": "禁用", "對象欄位": "分類代號", "值": None}])
        c = self.one(case, mk_obs(結果="放行",
                                  視覺標記=[{"標記類型": "禁用", "對象欄位": "訂單分類代碼", "值": "readonly"}]))
        self.assertEqual(c["狀態"], "PASS")

    def test_dialog_visual_mark_ignores_object_field_free_text(self):
        """判 2：對話框標記的 對象欄位 是自由文字（確認刪除對話框 vs 刪除確認對話框），只比 (標記類型, 值)"""
        case = mk_case("T1", 結果="放行",
                       視覺標記=[{"標記類型": "對話框", "對象欄位": "確認刪除對話框", "值": "開啟"}])
        c = self.one(case, mk_obs(結果="放行",
                                  視覺標記=[{"標記類型": "對話框", "對象欄位": "刪除確認對話框", "值": "開啟"}]))
        self.assertEqual(c["狀態"], "PASS")

    def test_dialog_visual_mark_value_mismatch_fails(self):
        case = mk_case("T1", 結果="放行",
                       視覺標記=[{"標記類型": "對話框", "對象欄位": "確認刪除對話框", "值": "開啟"}])
        c = self.one(case, mk_obs(結果="放行",
                                  視覺標記=[{"標記類型": "對話框", "對象欄位": "刪除確認對話框", "值": "關閉"}]))
        self.assertEqual(c["狀態"], "FAIL")

    def test_visual_mark_value_mismatch_fails_when_expected_value_given(self):
        """殺突變 A：預期鈕停用、觀察鈕啟用不該是 PASS"""
        case = mk_case("T1", 結果="放行",
                       視覺標記=[{"標記類型": "禁用", "對象欄位": "分類代號", "值": "disabled"}])
        c = self.one(case, mk_obs(結果="放行",
                                  視覺標記=[{"標記類型": "禁用", "對象欄位": "訂單分類代碼", "值": "enabled"}]))
        self.assertEqual(c["狀態"], "FAIL")

    def test_unmapped_case_field_raises(self):
        """C3：case 欄位 非 null 但不在 欄位對照 裡 → 拋錯，不預設 確定"""
        case = mk_case("T1", 欄位="幽靈欄位")
        with self.assertRaises(ValueError):
            judge(mk_plan([case]), mk_fix(), mk_run(T1=mk_obs()))

    def test_global_signals_do_not_override_per_case_attribution(self):
        """C1：刪全域覆寫——找不到欄位數與互動模型不一致只進 全域訊號，不吞掉對得上欄位的 FAIL 歸因"""
        mapping_two = [{"規格": "分類代號", "實機": "訂單分類代碼", "信心": "確定"},
                       {"規格": "排列順序", "實機": None, "信心": "找不到"},
                       {"規格": "描述文字", "實機": None, "信心": "找不到"}]
        r = judge(mk_plan([mk_case("T1")], mapping=mapping_two, model_ok=False),
                  mk_fix(), mk_run(T1=mk_obs(結果="放行")))
        c = r["cases"][0]
        self.assertEqual(c["狀態"], "FAIL")
        self.assertEqual(c["歸因傾向"], "疑似實作偏離")
        self.assertEqual(r["全域訊號"], {"欄位找不到": 2, "互動模型一致": False})

class TestScreenAssertions(unittest.TestCase):
    """第四槽「畫面斷言」：查詢頁的列數／合計／欄存在與否不再塞訊息槽（避免查詢頁假 FAIL）"""
    def run_case(self, asserts, observed, **case_kw):
        case = mk_case("T1", 結果="放行", **case_kw)
        if asserts is not None:
            case["預期"]["畫面斷言"] = asserts
        obs = mk_obs(結果="放行")
        if observed is not None:
            obs["畫面斷言"] = observed
        return judge(mk_plan([case]), mk_fix(), mk_run(T1=obs))["cases"][0]

    def test_all_assertions_hold_is_pass(self):
        c = self.run_case(
            [{"目標": "列數", "期望": "5", "比對": "等於"},
             {"目標": "合計", "期望": "1200", "比對": "數值等於"},
             {"目標": "欄:備註", "期望": None, "比對": "不存在"},
             {"目標": "欄:金額", "期望": None, "比對": "存在"},
             {"目標": "分頁", "期望": "第 1 頁", "比對": "包含"}],
            [{"目標": "列數", "實際": 5}, {"目標": "合計", "實際": "1,200.00"}, {"目標": "欄:備註", "實際": None},
             {"目標": "欄:金額", "實際": "金額"}, {"目標": "分頁", "實際": "目前在第 1 頁"}])
        self.assertEqual(c["狀態"], "PASS")
        self.assertTrue(all(a["結果"] == "通過" for a in c["證據"]["畫面斷言"]))

    def test_one_failed_assertion_fails_with_expected_vs_actual(self):
        c = self.run_case([{"目標": "列數", "期望": "5", "比對": "等於"}, {"目標": "合計", "期望": "100", "比對": "數值等於"}],
                          [{"目標": "列數", "實際": "5"}, {"目標": "合計", "實際": "99"}])
        self.assertEqual(c["狀態"], "FAIL")
        self.assertTrue(any("合計" in n and "100" in n and "99" in n for n in c["備註"]))

    def test_element_not_found_fails_equal(self):
        c = self.run_case([{"目標": "列數", "期望": "5", "比對": "等於"}], [{"目標": "列數", "實際": None}])
        self.assertEqual(c["狀態"], "FAIL")

    def test_missing_observation_entry_is_uncomparable_not_fail(self):
        c = self.run_case([{"目標": "列數", "期望": "5", "比對": "等於"}], [])
        self.assertEqual(c["狀態"], "無法比對")
        self.assertTrue(any("待人工" in n for n in c["備註"]))
        c2 = self.run_case([{"目標": "列數", "期望": "5", "比對": "等於"}], None)   # 舊 runner 完全沒這欄
        self.assertEqual(c2["狀態"], "無法比對")

    def test_fail_beats_uncomparable(self):
        c = self.run_case([{"目標": "a", "期望": "1", "比對": "等於"}, {"目標": "b", "期望": "1", "比對": "等於"}],
                          [{"目標": "a", "實際": "2"}])
        self.assertEqual(c["狀態"], "FAIL")

    def test_old_format_without_assertions_unchanged(self):
        c = self.run_case(None, None)
        self.assertEqual(c["狀態"], "PASS")
        self.assertEqual(c["證據"]["畫面斷言"], [])

    def test_semantic_message_without_observation_not_fail_when_assertions_exist(self):
        """安全網：語意訊息槽被誤塞斷言文字、畫面無訊息——有畫面斷言且全過就不判 FAIL"""
        c = self.run_case([{"目標": "列數", "期望": "5", "比對": "等於"}], [{"目標": "列數", "實際": 5}],
                          訊息="共 5 筆", 比對="語意")
        self.assertEqual(c["狀態"], "PASS")

    def test_semantic_message_without_observation_still_fails_without_assertions(self):
        c = self.run_case(None, None, 訊息="共 5 筆", 比對="語意")
        self.assertEqual(c["狀態"], "FAIL")

    def test_exact_message_still_strict_with_assertions(self):
        c = self.run_case([{"目標": "列數", "期望": "5", "比對": "等於"}], [{"目標": "列數", "實際": 5}],
                          訊息="共 5 筆", 比對="逐字")
        self.assertEqual(c["狀態"], "FAIL")


class TestMerge(unittest.TestCase):
    def test_frontend_not_blocking_plus_api_block_is_pass_with_note(self):
        case = mk_case("T1", 寫入="建立")
        api = {"_meta": {}, "rules": {"T1": {"請求": {"方法": "POST", "路徑": "/x", "body摘要": ""},
                                            "回應": {"狀態碼": 400, "錯誤碼": "E1", "欄位": []}}}}
        r = judge(mk_plan([case]), mk_fix(writable=False), mk_run(T1=mk_obs(結果="放行")), api)
        c = r["cases"][0]
        self.assertEqual(c["狀態"], "PASS")
        self.assertTrue(any("前端無即時提示" in n for n in c["備註"]))

    def test_frontend_not_blocking_plus_api_pass_is_fail(self):
        case = mk_case("T1", 寫入="建立")
        api = {"_meta": {}, "rules": {"T1": {"請求": {"方法": "POST", "路徑": "/x", "body摘要": ""},
                                            "回應": {"狀態碼": 200, "錯誤碼": None, "欄位": []}}}}
        r = judge(mk_plan([case]), mk_fix(writable=False), mk_run(T1=mk_obs(結果="放行")), api)
        self.assertEqual(r["cases"][0]["狀態"], "FAIL")

    def test_frontend_not_blocking_plus_api_5xx_is_uncomparable(self):
        case = mk_case("T1", 寫入="建立")
        api = {"_meta": {}, "rules": {"T1": {"請求": {"方法": "POST", "路徑": "/x", "body摘要": ""},
                                            "回應": {"狀態碼": 500, "錯誤碼": None, "欄位": []}}}}
        r = judge(mk_plan([case]), mk_fix(writable=False), mk_run(T1=mk_obs(結果="放行")), api)
        c = r["cases"][0]
        self.assertEqual(c["狀態"], "無法比對")
        self.assertIsNone(c["歸因傾向"])
        self.assertTrue(any("500" in n for n in c["備註"]))

class TestIntegrity(unittest.TestCase):
    def test_missing_observation_raises(self):
        with self.assertRaises(ValueError):
            judge(mk_plan([mk_case("T1"), mk_case("T2")]), mk_fix(), mk_run(T1=mk_obs()))

    def test_unexpected_observation_raises(self):
        with self.assertRaises(ValueError):
            judge(mk_plan([mk_case("T1")]), mk_fix(), mk_run(T1=mk_obs(), T9=mk_obs()))

    def test_description_is_never_read(self):
        obs = mk_obs(); obs["描述"] = "擋下 請輸入分類代號 欄位下方"
        r = judge(mk_plan([mk_case("T1", 訊息="請輸入分類代號")]), mk_fix(), mk_run(T1=obs))
        self.assertEqual(r["cases"][0]["狀態"], "FAIL")   # 訊息在 描述 裡不算

    def test_plan_precondition_not_resolved_by_fixture_raises(self):
        """C2：plan 的前置資料條件必須是 fixtures.解析 條件集合的子集，缺席不能被當成已備妥（TC-D-005 情境）"""
        case = mk_case("T1", 前置=[{"條件": "存在可刪除的訂單分類資料", "用途": "刪除"}])
        with self.assertRaises(ValueError):
            judge(mk_plan([case]), mk_fix(items=[]), mk_run(T1=mk_obs()))

    def test_precedence_model_mismatch_over_blocked_keeps_fixture_note(self):
        case = mk_case("T1", 依賴=True, 前置=[{"條件": "存在被引用的分類", "用途": "刪除"}])
        fix = mk_fix(items=[{"條件": "存在被引用的分類", "結果": "無法備妥", "原因": "查無"}])
        r = judge(mk_plan([case], model_ok=False), fix, mk_run(T1=mk_obs()))
        c = r["cases"][0]
        self.assertEqual(c["狀態"], "未執行")
        self.assertTrue(any("前置資料無法備妥" in n for n in c["備註"]))

class TestVerdict(unittest.TestCase):
    def test_spec_first_when_over_30_percent_uncomparable_or_not_run(self):
        mapping = [{"規格": "分類代號", "實機": "訂單分類代碼", "信心": "確定"},
                   {"規格": "排列順序", "實機": None, "信心": "找不到"}]
        cases = [mk_case("T1"), mk_case("T2", 欄位="排列順序"), mk_case("T3", 依賴=True)]
        run = mk_run(T1=mk_obs(), T2=mk_obs(結果="不適用"), T3=mk_obs())
        r = judge(mk_plan(cases, mapping=mapping, model_ok=False), mk_fix(), run)
        self.assertIn("先校正規格", r["判讀"])
        self.assertEqual(r["總計"]["無法比對"], 1)
        self.assertEqual(r["總計"]["未執行"], 1)
        kinds = {x["類型"] for x in r["規格校正"]}
        self.assertIn("欄位不存在", kinds); self.assertIn("互動模型", kinds)

    def test_spec_correction_suggests_message_text_on_exact_mismatch(self):
        r = judge(mk_plan([mk_case("T1", 訊息="此分類代號已存在")]), mk_fix(),
                  mk_run(T1=mk_obs(訊息="訂單分類代碼不可重複")))
        self.assertTrue(any(x["類型"] == "訊息文字" and "訂單分類代碼不可重複" in x["內容"] for x in r["規格校正"]))

    def test_verdict_mentions_not_run_when_below_threshold(self):
        """9 PASS + 1 未執行（低於 30% 閾值）時，判讀應該說「通過（含 1 條...）」"""
        cases = [mk_case(f"T{i}") for i in range(1, 10)]  # 9 PASS
        cases.append(mk_case("T10", 依賴=True))  # 1 未執行（因為互動模型不一致）
        r = judge(mk_plan(cases, model_ok=False), mk_fix(),
                  mk_run(**{f"T{i}": mk_obs() for i in range(1, 10)} | {"T10": mk_obs(結果="未送出")}))
        self.assertEqual(r["總計"]["PASS"], 9)
        self.assertEqual(r["總計"]["未執行"], 1)
        self.assertIn("含 1 條", r["判讀"])
        self.assertIn("未執行", r["判讀"])

    def test_all_pass_verdict(self):
        r = judge(mk_plan([mk_case("T1")]), mk_fix(), mk_run(T1=mk_obs()))
        self.assertEqual(r["判讀"], "通過")
        self.assertEqual(sum(r["總計"].values()), 1)


class TestDataAssertions(unittest.TestCase):
    """資料斷言：DB 落地事實（票面模式 WORK_ORDER.STATUS 之類），runner 讀不到，由 fixture 跑完後唯讀查核（曾有多張票因此假無法比對）"""
    def run_case(self, asserts, db_rows, screen=None, screen_obs=None):
        case = mk_case("T1", 結果="放行")
        case["預期"]["資料斷言"] = asserts
        if screen is not None:
            case["預期"]["畫面斷言"] = screen
        obs = mk_obs(結果="放行")
        if screen_obs is not None:
            obs["畫面斷言"] = screen_obs
        db = None if db_rows is None else {"_meta": {"通道": "[readonly-db demo-staging]"}, "rules": {"T1": db_rows}}
        return judge(mk_plan([case]), mk_fix(), mk_run(T1=obs), db_check=db)["cases"][0]

    def test_all_hold_is_pass(self):
        c = self.run_case([{"目標": "WORK_ORDER.STATUS", "期望": "Y", "比對": "等於"}],
                          [{"目標": "WORK_ORDER.STATUS", "實際": "Y", "查詢": "SELECT STATUS FROM WORK_ORDER WHERE 1=0"}])
        self.assertEqual(c["狀態"], "PASS")
        self.assertEqual(c["證據"]["資料斷言"][0]["結果"], "通過")

    def test_not_checked_is_uncomparable_with_note(self):
        c = self.run_case([{"目標": "WORK_ORDER.STATUS", "期望": "Y", "比對": "等於"}], None)
        self.assertEqual(c["狀態"], "無法比對")
        self.assertTrue(any("資料斷言" in n for n in c["備註"]))

    def test_failed_is_fail_labelled_data(self):
        c = self.run_case([{"目標": "WORK_ORDER.QTY2", "期望": "18", "比對": "數值等於"}],
                          [{"目標": "WORK_ORDER.QTY2", "實際": 12, "查詢": "SELECT QTY2 FROM WORK_ORDER"}])
        self.assertEqual(c["狀態"], "FAIL")
        self.assertTrue(any(n.startswith("資料斷言不成立") and "18" in n and "12" in n for n in c["備註"]))

    def test_screen_and_data_both_evaluated(self):
        c = self.run_case([{"目標": "WORK_ORDER.STATUS", "期望": "Y", "比對": "等於"}],
                          [{"目標": "WORK_ORDER.STATUS", "實際": "Y", "查詢": "q"}],
                          screen=[{"目標": "列數", "期望": "1", "比對": "等於"}], screen_obs=[{"目標": "列數", "實際": "2"}])
        self.assertEqual(c["狀態"], "FAIL")
        self.assertTrue(any(n.startswith("畫面斷言不成立") for n in c["備註"]))


class TestEqualsTarget(unittest.TestCase):
    """比對「等於目標」：期望寫同一槽另一個目標名，比兩個實際值（「修改後與修改前相同」不再寫成 期望「是」——曾造成假 FAIL）"""
    def run_case(self, observed):
        case = mk_case("T1", 結果="放行")
        case["預期"]["畫面斷言"] = [{"目標": "廠區位置（修改前）", "期望": None, "比對": "存在"},
                                  {"目標": "廠區位置（修改後）", "期望": "廠區位置（修改前）", "比對": "等於目標"}]
        obs = mk_obs(結果="放行")
        obs["畫面斷言"] = observed
        return judge(mk_plan([case]), mk_fix(), mk_run(T1=obs))["cases"][0]

    def test_same_values_pass(self):
        c = self.run_case([{"目標": "廠區位置（修改前）", "實際": "A 棟"}, {"目標": "廠區位置（修改後）", "實際": "A 棟 "}])
        self.assertEqual(c["狀態"], "PASS")

    def test_different_values_fail(self):
        c = self.run_case([{"目標": "廠區位置（修改前）", "實際": "A 棟"}, {"目標": "廠區位置（修改後）", "實際": "B 棟"}])
        self.assertEqual(c["狀態"], "FAIL")
        self.assertTrue(any("A 棟" in n and "B 棟" in n for n in c["備註"]))

    def test_reference_missing_is_uncomparable(self):
        c = self.run_case([{"目標": "廠區位置（修改後）", "實際": "A 棟"}])
        self.assertEqual(c["狀態"], "無法比對")

if __name__ == "__main__":
    unittest.main()
