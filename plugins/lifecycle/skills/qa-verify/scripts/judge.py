#!/usr/bin/env python3
"""qa-verify 判定：每條 TC 一個機械狀態，人只裁「這算誰的」。

只讀事實欄位（結果／訊息／訊息位置／欄位變化／視覺標記／畫面斷言／步驟失敗次數），永不讀 描述。
預期有五槽：訊息、欄位變化、視覺標記、畫面斷言、資料斷言。查詢頁的列數、合計、欄存在與否等非訊息事實一律進
畫面斷言槽（逐條 {目標, 期望, 比對} 對 runner 的 {目標, 實際}）；不得塞進訊息槽——語意訊息模式
觀察無訊息即 FAIL（查詢頁多條 TC 假 FAIL 的成因）。畫面讀不到的 DB 落地事實進資料斷言槽，
對 fixture 跑完後唯讀查核的 db-check.yml（runner 沒有 DB 工具，放畫面斷言必成無法比對）。
plan 與 run 的 TC 集合必須完全相等——缺觀察、多觀察都拋錯，沒有「查不到＝通過」。

單一 TC 的狀態判定優先序（`_judge_case` 內，依序判斷、命中即回，不繼續往下比對）：
1. 無法比對（欄位在 欄位對照 找不到對應；或觀察 結果 = 不適用——工具無法觸發此情境，不能拿來跟預期比對）
2. 未執行（互動模型與規格不一致，且此 TC 依賴該模型）
3. BLOCKED（前置資料無法備妥）
4. 以下才進入以觀察為準的比對（結果／訊息／欄位變化／視覺標記／畫面斷言、唯讀環境「寫入≠無」的
   未執行／前端未擋／PASS 合併判定）
較高優先序命中時，若該 TC 同時也命中「前置資料無法備妥」，仍會把該訊號補進 備註，
不讓它被較高優先序的判定吞掉。

全域訊號（欄位找不到的數量、互動模型是否一致）只進報告表頭與備註，**不覆寫**任何一條 TC 自己的歸因傾向——
歸因永遠依該 TC 自己的證據判定。
"""
STATUS_VALUES = ["PASS", "FAIL", "前端未擋", "BLOCKED", "未執行", "無法比對"]
_SPEC_STALE = "疑似規格過時"
_IMPL_DRIFT = "疑似實作偏離"


def _mapping(plan):
    """規格欄名 → 實機欄名；找不到的實機為 None。"""
    return {m["規格"]: (m["實機"], m["信心"]) for m in plan["meta"]["欄位對照"]}


def _to_spec_field(name, mapping):
    """觀察用實機欄名，對回規格欄名；對不回就原樣。"""
    for spec, (real, _) in mapping.items():
        if real == name:
            return spec
    return name


def _message_ok(expected, mode, observed, notes, has_assertions=False):
    if expected is None:
        return True
    if mode == "逐字":
        return (observed or "").strip() == expected.strip()
    # 語意：機械上只能確認「有訊息」；文字交人
    if observed:
        notes.append(f"訊息文字待人工確認：預期「{expected}」，觀察「{observed}」")
        return True
    if has_assertions:  # 安全網：有畫面斷言的 TC，語意訊息槽多半是誤塞，不因無訊息判 FAIL
        notes.append(f"語意訊息「{expected}」未觀察到訊息，此 TC 有畫面斷言，訊息槽不判定")
        return True
    return False


def _num(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).replace(",", "").replace(" ", ""))
    except ValueError:
        return None


def _assertion_ok(cmp, expected, actual):
    a, e = ("" if actual is None else str(actual).strip()), ("" if expected is None else str(expected).strip())
    if cmp == "存在":
        return actual is not None
    if cmp == "不存在":
        return actual is None
    if actual is None:
        return False
    if cmp == "等於":
        return a == e
    if cmp == "包含":
        return e in a
    if cmp == "數值等於":
        x, y = _num(actual), _num(expected)
        return x is not None and y is not None and x == y
    raise ValueError(f"未知的畫面斷言比對「{cmp}」")


def _eval_assertions(expected, observed, slot="畫面斷言"):
    """逐條比對；觀察沒回報該目標（條目缺漏）＝無法比對，不是不成立。實際 null＝畫面上找不到。
    `等於目標`：期望是同槽另一個目標名，比兩邊實際值（修改前後相同之類，期望值在規劃時不可知）。"""
    got = {}
    for o in observed or []:
        got.setdefault(o["目標"], o.get("實際"))
    out = []
    for e in expected or []:
        item = {"槽": slot, "目標": e["目標"], "期望": e.get("期望"), "比對": e["比對"]}
        ref = e.get("期望") if e["比對"] == "等於目標" else None
        if e["目標"] not in got or (ref is not None and ref not in got):
            out.append({**item, "實際": got.get(e["目標"]), "結果": "無法比對"})
        elif ref is not None:
            item["期望"] = f"{ref}＝{got[ref]}"
            ok = got[e["目標"]] is not None and _assertion_ok("等於", got[ref], got[e["目標"]])
            out.append({**item, "實際": got[e["目標"]], "結果": "通過" if ok else "不成立"})
        else:
            ok = _assertion_ok(e["比對"], e.get("期望"), got[e["目標"]])
            out.append({**item, "實際": got[e["目標"]], "結果": "通過" if ok else "不成立"})
    return out


def _subset_field_changes(expected, observed, mapping):
    """預期 `值被帶入` 且值為 null＝「需產出某個值」：觀察到的值也是空的不算數
    （案例：訂單號讀回 null 仍判 PASS，下游全斷）。"""
    obs = {(_to_spec_field(o["欄位"], mapping), o["變化"], o.get("值")) for o in observed}
    obs_no_value = {(f, c) for f, c, v in obs if c != "值被帶入" or v not in (None, "")}
    for e in expected:
        field = _to_spec_field(e["欄位"], mapping)
        key = (field, e["變化"])
        if e.get("值") is None:
            if key not in obs_no_value:
                return False
        elif (field, e["變化"], e["值"]) not in obs:
            return False
    return True


def _subset_marks(expected, observed, mapping):
    """對象欄位 兩側都要正規化成規格名才能比（planner／runner 誰用哪種欄名沒有保證一致）。
    `對話框` 的 對象欄位 是自由文字（如「確認刪除對話框」vs「刪除確認對話框」），不比對象欄位，只比 (標記類型, 值)。"""
    obs = {(m["標記類型"], _to_spec_field(m["對象欄位"], mapping), m.get("值")) for m in observed}
    obs_no_value = {(t, f) for t, f, _ in obs}
    obs_dialog_present = any(t == "對話框" for t, _, _ in obs)
    obs_dialog_values = {v for t, _, v in obs if t == "對話框"}
    for e in expected:
        if e["標記類型"] == "對話框":
            if e.get("值") is None:
                if not obs_dialog_present:
                    return False
            elif e["值"] not in obs_dialog_values:
                return False
            continue
        field = _to_spec_field(e["對象欄位"], mapping)
        key = (e["標記類型"], field)
        if e.get("值") is None:
            if key not in obs_no_value:
                return False
        elif (e["標記類型"], field, e["值"]) not in obs:
            return False
    return True


def _api_result(api_entry):
    code = api_entry["回應"]["狀態碼"]
    if 400 <= code < 500:
        return "擋下"
    if 200 <= code < 400:
        return "放行"
    return "錯誤"  # <200 或 >=500：非驗證結果，不能當放行/擋下判讀


def _judge_case(case, mapping, model_ok, writable, unavailable, obs, api_entry, assertions):
    notes, exp = [], case["預期"]
    unavailable_conds = [p["條件"] for p in case["前置資料"] if p["條件"] in unavailable]
    fixture_note = ("前置資料無法備妥：" + "；".join(unavailable_conds)) if unavailable_conds else None

    field = case.get("欄位")
    if field is not None:
        if field not in mapping:
            raise ValueError(f"case[{case['id']}].欄位「{field}」不在 meta.欄位對照 裡")
        if mapping[field][1] == "找不到":
            return "無法比對", _SPEC_STALE, notes + ([fixture_note] if fixture_note else [])
    if not model_ok and case["依賴互動模型"]:
        extra = ["互動模型與規格不一致，此 TC 依賴該模型"]
        if fixture_note:
            extra.append(fixture_note)
        return "未執行", _SPEC_STALE, notes + extra
    if fixture_note:
        return "BLOCKED", None, notes + [fixture_note]
    if obs["結果"] is None:
        return "無法比對", _IMPL_DRIFT, notes + [f"步驟失敗 {obs['步驟失敗次數']} 次且無最終觀察"]
    if obs["結果"] == "不適用":
        return "無法比對", None, notes + ["工具無法觸發此情境"]

    readonly_write = (not writable) and case["寫入"] != "無"
    if readonly_write and obs["結果"] == "未送出":
        return "未執行", None, notes + ["環境唯讀且此 TC 需寫入，未達可觀察點"]
    if readonly_write and obs["結果"] == "放行":
        if exp["結果"] == "放行":
            return "未執行", None, notes + ["環境唯讀，未真送出，無法視為已放行"]
        if api_entry is None:
            return "前端未擋", None, notes + ["後端未驗"]
        api_result = _api_result(api_entry)
        if api_result == "擋下":
            return "PASS", None, notes + ["後端擋；前端無即時提示"]
        if api_result == "錯誤":
            code = api_entry["回應"]["狀態碼"]
            return "無法比對", None, notes + [f"後端回應 {code}，非驗證結果，需人判"]
        return "FAIL", _IMPL_DRIFT, notes + ["前端與後端皆放行"]

    if obs["結果"] != exp["結果"]:
        return "FAIL", _IMPL_DRIFT, notes + [f"結果 預期 {exp['結果']}，觀察 {obs['結果']}"]
    if not _message_ok(exp["訊息"], exp["訊息比對"], obs["訊息"], notes, bool(assertions)):
        return "FAIL", _IMPL_DRIFT, notes + [f"訊息 預期「{exp['訊息']}」，觀察「{obs['訊息']}」"]
    if not _subset_field_changes(exp["欄位變化"], obs["欄位變化"], mapping):
        return "FAIL", _IMPL_DRIFT, notes + ["預期的欄位變化未觀察到"]
    if not _subset_marks(exp["視覺標記"], obs["視覺標記"], mapping):
        return "FAIL", _IMPL_DRIFT, notes + ["預期的視覺標記未觀察到"]
    bad = [a for a in assertions if a["結果"] == "不成立"]
    if bad:
        return "FAIL", _IMPL_DRIFT, notes + [
            f"{a['槽']}不成立：{a['目標']} {a['比對']} 預期「{a['期望']}」，實際「{a['實際']}」" for a in bad]
    missing = [a for a in assertions if a["結果"] == "無法比對"]
    if missing:
        who = {"畫面斷言": "runner 未回報實際值", "資料斷言": "未經 DB 查核（缺 db-check.yml 或該目標）"}
        return "無法比對", None, notes + [f"{a['槽']} {who[a['槽']]}，待人工：{a['目標']}" for a in missing]
    return "PASS", None, notes


def judge(plan, fixtures, run_ui, run_api=None, db_check=None):
    plan_ids = [c["id"] for c in plan["cases"]]
    run_ids = set(run_ui["rules"])
    missing, extra = set(plan_ids) - run_ids, run_ids - set(plan_ids)
    if missing or extra:
        raise ValueError(f"plan 與 run-ui 的 TC 集合不一致：缺觀察 {sorted(missing)}，多出 {sorted(extra)}")

    plan_conditions = {p["條件"] for case in plan["cases"] for p in case["前置資料"]}
    fixture_conditions = {it["條件"] for it in fixtures["解析"]}
    unresolved = plan_conditions - fixture_conditions
    if unresolved:
        raise ValueError(f"前置資料條件未被 fixture 解析：{sorted(unresolved)}")

    mapping = _mapping(plan)
    model_ok = plan["meta"]["互動模型"]["一致"]
    writable = fixtures["環境"]["允許寫入"]
    unavailable = {it["條件"] for it in fixtures["解析"] if it["結果"] == "無法備妥"}
    api_rules = (run_api or {}).get("rules", {})
    db_rules = (db_check or {}).get("rules", {})

    out, totals = [], {s: 0 for s in STATUS_VALUES}
    global_signals = {"欄位找不到": sum(1 for _, (_, conf) in mapping.items() if conf == "找不到"),
                       "互動模型一致": model_ok}
    for case in plan["cases"]:
        obs = run_ui["rules"][case["id"]]
        screen = _eval_assertions(case["預期"].get("畫面斷言"), obs.get("畫面斷言"))
        data = _eval_assertions(case["預期"].get("資料斷言"), db_rules.get(case["id"]), "資料斷言")
        assertions = screen + data
        status, attribution, notes = _judge_case(
            case, mapping, model_ok, writable, unavailable, obs, api_rules.get(case["id"]), assertions)
        totals[status] += 1
        out.append({"id": case["id"], "狀態": status, "歸因傾向": attribution, "備註": notes,
                    "證據": {"預期": case["預期"],
                             "觀察": {k: obs[k] for k in ("結果", "訊息", "訊息位置", "欄位變化", "視覺標記")},
                             "畫面斷言": screen,
                             "資料斷言": data,
                             "api": api_rules.get(case["id"])}})

    corrections = []
    for spec, (real, conf) in mapping.items():
        if conf == "找不到":
            corrections.append({"類型": "欄位不存在", "內容": f"規格欄位「{spec}」在實機找不到對應"})
        elif real and real != spec:
            corrections.append({"類型": "欄位改名", "內容": f"「{spec}」→「{real}」"})
    if not model_ok:
        m = plan["meta"]["互動模型"]
        corrections.append({"類型": "互動模型", "內容": f"規格「{m['規格']}」，實機「{m['實機']}」"})
    for c, case in zip(out, plan["cases"]):
        exp, ob = case["預期"], c["證據"]["觀察"]
        if (c["狀態"] == "FAIL" and exp["訊息比對"] == "逐字" and exp["訊息"] and ob["訊息"]
                and ob["結果"] == exp["結果"]):
            corrections.append({"類型": "訊息文字",
                                "內容": f"{case['id']}：規格「{exp['訊息']}」，實機「{ob['訊息']}」"})

    n = len(out)
    if (totals["無法比對"] + totals["未執行"]) / n > 0.3:
        verdict = "規格與實作對不上，先校正規格再驗"
    elif totals["FAIL"] or totals["前端未擋"] or totals["BLOCKED"]:
        verdict = f"有 {totals['FAIL']} 條偏離、{totals['前端未擋']} 條後端待驗、{totals['BLOCKED']} 條環境受阻，見「需要人決定的」"
    elif totals["未執行"] or totals["無法比對"]:
        n_other = totals["未執行"] + totals["無法比對"]
        verdict = f"通過（含 {n_other} 條未執行／無法比對，見「需要人決定的」）"
    else:
        verdict = "通過"
    return {"cases": out, "總計": totals, "判讀": verdict, "規格校正": corrections, "全域訊號": global_signals}
