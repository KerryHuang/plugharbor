#!/usr/bin/env python3
"""qa-verify 機器檔 schema 驗證。

原則（memory「缺值長得像成功」）：
- 空輸入、非 dict、缺頂層鍵 → 回錯誤，永不回空 list
- 鍵白名單：未知鍵是錯誤（已知步驟放錯層的教訓）
- 鍵存在但值型別不對 → 錯誤，不當預設值
"""
import json
import re
import sys

# Windows 預設 cp950：印中文會亂碼、印 emoji 直接炸 UnicodeEncodeError。
# 與 parse_foxpro.py 同一做法，腳本自己處理，不靠呼叫端設 PYTHONUTF8。
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

RESULT_VALUES = ["擋下", "放行", "未送出", "不適用"]
EXPECT_RESULT_VALUES = ["擋下", "放行"]
EXECUTOR_VALUES = ["ui", "api"]
TYPE_VALUES = ["必填", "長度", "唯一", "格式化", "狀態鎖", "流程", "權限", "例外", "範圍", "自動帶入", "按鈕狀態"]
WRITE_VALUES = ["無", "建立", "修改", "刪除"]
MSG_CMP_VALUES = ["逐字", "語意"]
CONFIDENCE_VALUES = ["確定", "找不到"]
FIXTURE_RESULT_VALUES = ["找到", "建立", "無法備妥"]
FIELD_CHANGE_VALUES = ["值被還原", "值被清空", "值被帶入", "值被截斷", "值被轉換"]
MARK_TYPE_VALUES = ["紅星", "反白", "變色", "禁用", "啟用", "圖示", "對話框"]
MSG_POS_VALUES = ["欄位下方", "欄位上方", "表單頂部", "toast", "對話框"]
DATA_CLASS_VALUES = ["內部", "客戶副本"]
ASSERT_CMP_VALUES = ["等於", "包含", "不存在", "存在", "數值等於", "等於目標"]
# 期望整段是 <…>／{…}：規劃時不知道的值寫成佔位符，judge 會拿字面比對（曾造成假 FAIL）。改用 等於目標 或 資料斷言。
PLACEHOLDER_RE = re.compile(r"^\s*(<[^<>]+>|\{[^{}]+\})\s*$")

# 步驟／預期「注意」欄禁詞：命中代表寫進了結論而非機械操作資訊（防第二輪快取回灌自己的結論）。
STALE_NOTE_RE = re.compile(r"(結果記|結果:|預期|不適用|未送出|規格)")

_META_KEYS = {"功能", "功能碼", "票號", "規格", "欄位對照", "互動模型"}
_CASE_KEYS = {"id", "欄位", "依賴互動模型", "來源", "執行器", "類型", "前置資料", "步驟", "預期", "寫入"}
_EXPECT_KEYS = {"結果", "訊息", "訊息比對", "欄位變化", "視覺標記"}  # 另有選填「畫面斷言」，舊檔無此欄合法
_RUN_UI_KEYS = {"結果", "訊息", "訊息位置", "欄位變化", "視覺標記", "描述", "步驟失敗次數", "記錄讀值次數", "網路"}  # 另有選填「畫面斷言」
_RUN_API_KEYS = {"請求", "回應"}
_ENV_KEYS = {"url", "租戶", "資料類別", "允許寫入", "含個資", "查證"}


def _enum(errs, where, value, allowed):
    if value not in allowed:
        errs.append(f"{where}: 值 {value!r} 不在 {allowed}")


def _keys(errs, where, obj, allowed, required=None):
    """未知鍵與缺必要鍵都是錯誤。required 省略＝allowed 全部必要。"""
    if not isinstance(obj, dict):
        errs.append(f"{where}: 必須是 dict，實際 {type(obj).__name__}")
        return False
    req = allowed if required is None else required
    for k in obj:
        if k not in allowed:
            errs.append(f"{where}: 未知鍵「{k}」")
    for k in req:
        if k not in obj:
            errs.append(f"{where}: 缺鍵「{k}」")
    return True


def _int(errs, where, value):
    if not isinstance(value, int) or isinstance(value, bool):
        errs.append(f"{where}: 必須是整數，實際 {value!r}")


def _field_changes(errs, where, items):
    if not isinstance(items, list):
        errs.append(f"{where}: 欄位變化 必須是 list"); return
    for i, ch in enumerate(items):
        w = f"{where}.欄位變化[{i}]"
        if _keys(errs, w, ch, {"欄位", "變化", "值"}):
            _enum(errs, f"{w}.變化", ch.get("變化"), FIELD_CHANGE_VALUES)


def _visual_marks(errs, where, items):
    if not isinstance(items, list):
        errs.append(f"{where}: 視覺標記 必須是 list"); return
    for i, m in enumerate(items):
        w = f"{where}.視覺標記[{i}]"
        if not isinstance(m, dict):
            errs.append(f"{w}: 必須是結構 {{標記類型, 對象欄位, 值}}，不可是散文"); continue
        if _keys(errs, w, m, {"標記類型", "對象欄位", "值"}):
            _enum(errs, f"{w}.標記類型", m.get("標記類型"), MARK_TYPE_VALUES)


def _screen_assertions(errs, where, items, expect, slot="畫面斷言", keys=None):
    """expect=True 驗 plan 預期 {目標, 期望, 比對}；False 驗觀察 {目標, 實際}（db-check 另帶 查詢）。"""
    if not isinstance(items, list):
        errs.append(f"{where}: {slot} 必須是 list"); return
    keys = keys or ({"目標", "期望", "比對"} if expect else {"目標", "實際"})
    targets = {a.get("目標") for a in items if isinstance(a, dict)}
    for i, a in enumerate(items):
        w = f"{where}.{slot}[{i}]"
        if not _keys(errs, w, a, keys):
            continue
        if not isinstance(a.get("目標"), str) or not a["目標"].strip():
            errs.append(f"{w}.目標: 必須是非空 str")
        if expect:
            _enum(errs, f"{w}.比對", a.get("比對"), ASSERT_CMP_VALUES)
            if a.get("比對") not in ("存在", "不存在") and a.get("期望") is None:
                errs.append(f"{w}.期望: {a.get('比對')!r} 必須附期望值")
            if isinstance(a.get("期望"), str) and PLACEHOLDER_RE.match(a["期望"]):
                errs.append(f"{w}.期望: 「{a['期望']}」是佔位符，judge 會拿字面比對；改用 等於目標 或 資料斷言")
            if a.get("比對") == "等於目標" and (a.get("期望") not in targets or a.get("期望") == a.get("目標")):
                errs.append(f"{w}.期望: 等於目標 的期望必須是同一 {slot} 裡另一個目標名，實際 {a.get('期望')!r}")
        v = a.get("期望" if expect else "實際")
        if v is not None and (isinstance(v, bool) or not isinstance(v, (str, int, float))):
            errs.append(f"{w}.{'期望' if expect else '實際'}: 必須是 str／數值{'' if expect else '／null（找不到）'}，實際 {type(v).__name__}")


def _str_or_null(errs, where, value):
    if value is not None and not isinstance(value, str):
        errs.append(f"{where}: 必須是 str 或 null，實際 {value!r}")


def _dict_when_present(errs, where, value):
    if value is not None and not isinstance(value, dict):
        errs.append(f"{where}: 必須是 dict 或 null，實際 {type(value).__name__}")


def _list_of_str(errs, where, value):
    if not isinstance(value, list):
        errs.append(f"{where}: 必須是 list，實際 {type(value).__name__}"); return
    for i, item in enumerate(value):
        if not isinstance(item, str):
            errs.append(f"{where}[{i}]: 必須是 str，實際 {type(item).__name__}")


def _steps(errs, where, steps):
    if not isinstance(steps, list) or not steps:
        errs.append(f"{where}: 步驟 必須是非空 list"); return
    for i, s in enumerate(steps):
        if not isinstance(s, dict) or not s.get("動作"):
            errs.append(f"{where}.步驟[{i}]: 必須是 dict 且含非空「動作」")
            continue
        note = s.get("注意")
        if note and STALE_NOTE_RE.search(str(note)):
            errs.append(f"{where}.步驟[{i}].注意 含結論性文字")
        target = s.get("目標")
        if target and STALE_NOTE_RE.search(str(target)):
            errs.append(f"{where}.步驟[{i}].目標 含結論性文字")


def validate_plan(doc):
    errs = []
    if not isinstance(doc, dict):
        return ["plan: 頂層必須是 dict（空輸入不算通過）"]
    if not _keys(errs, "plan", doc, {"meta", "cases"}):
        return errs
    meta, cases = doc.get("meta"), doc.get("cases")
    if _keys(errs, "meta", meta, _META_KEYS):
        spec = meta.get("規格")
        if isinstance(spec, dict) and "ticket" in spec:
            # 票面模式（無 FFS 的 Bug 票）：來源是 Linear 票面，與 ffs/bfs 二擇一
            if _keys(errs, "meta.規格", spec, {"ticket"}):
                t = spec.get("ticket")
                if _keys(errs, "meta.規格.ticket", t, {"票號", "updatedAt"}):
                    if not t.get("票號") or not t.get("updatedAt"):
                        errs.append("meta.規格.ticket: 票號與 updatedAt 不可為空")
                    elif meta.get("票號") != t.get("票號"):
                        errs.append(f"meta.票號 {meta.get('票號')!r} 與 meta.規格.ticket.票號 {t.get('票號')!r} 不一致")
        elif _keys(errs, "meta.規格", spec, {"ffs", "bfs"}):
            ffs = spec.get("ffs")
            if ffs is None:
                errs.append("meta.規格.ffs: 必須是 dict，不可為 null")
            elif _keys(errs, "meta.規格.ffs", ffs, {"路徑", "sha"}):
                if not ffs.get("sha"):
                    errs.append("meta.規格.ffs.sha: 不可為空")
            bfs = spec.get("bfs")
            if bfs is not None and _keys(errs, "meta.規格.bfs", bfs, {"路徑", "sha"}):
                if not bfs.get("sha"):
                    errs.append("meta.規格.bfs.sha: 不可為空")
        mapping = meta.get("欄位對照")
        known_fields = set()
        if not isinstance(mapping, list):
            errs.append("meta.欄位對照: 必須是 list")
        else:
            for i, m in enumerate(mapping):
                if _keys(errs, f"meta.欄位對照[{i}]", m, {"規格", "實機", "信心"}):
                    _enum(errs, f"meta.欄位對照[{i}].信心", m.get("信心"), CONFIDENCE_VALUES)
                    known_fields.add(m.get("規格"))
        model = meta.get("互動模型")
        if _keys(errs, "meta.互動模型", model, {"規格", "實機", "一致"}):
            if not isinstance(model.get("一致"), bool):
                errs.append("meta.互動模型.一致: 必須是 bool")
    if not isinstance(cases, list) or not cases:
        errs.append("cases: 必須是非空 list（零條 TC 不算通過）")
        return errs
    seen = set()
    for i, c in enumerate(cases):
        w = f"cases[{i}]"
        if not _keys(errs, w, c, _CASE_KEYS):
            continue
        cid = c.get("id")
        w = f"cases[{cid}]"
        if cid in seen:
            errs.append(f"{w}: id 重複")
        seen.add(cid)
        if c.get("欄位") is not None and c["欄位"] not in known_fields:
            errs.append(f"{w}.欄位: 「{c['欄位']}」不在 meta.欄位對照 裡")
        if not isinstance(c.get("依賴互動模型"), bool):
            errs.append(f"{w}.依賴互動模型: 必須是 bool")
        _keys(errs, f"{w}.來源", c.get("來源"), {"文件", "章節", "規則章節"})
        _enum(errs, f"{w}.執行器", c.get("執行器"), EXECUTOR_VALUES)
        _enum(errs, f"{w}.類型", c.get("類型"), TYPE_VALUES)
        _enum(errs, f"{w}.寫入", c.get("寫入"), WRITE_VALUES)
        pre = c.get("前置資料")
        if not isinstance(pre, list):
            errs.append(f"{w}.前置資料: 必須是 list")
        else:
            for j, p in enumerate(pre):
                _keys(errs, f"{w}.前置資料[{j}]", p, {"條件", "用途"})
        _steps(errs, w, c.get("步驟"))
        exp = c.get("預期")
        if _keys(errs, f"{w}.預期", exp, _EXPECT_KEYS | {"畫面斷言", "資料斷言"}, required=_EXPECT_KEYS):
            _enum(errs, f"{w}.預期.結果", exp.get("結果"), EXPECT_RESULT_VALUES)
            _enum(errs, f"{w}.預期.訊息比對", exp.get("訊息比對"), MSG_CMP_VALUES)
            if exp.get("訊息") is not None and not isinstance(exp["訊息"], str):
                errs.append(f"{w}.預期.訊息: 必須是 str 或 null")
            _field_changes(errs, f"{w}.預期", exp.get("欄位變化"))
            _visual_marks(errs, f"{w}.預期", exp.get("視覺標記"))
            for slot in ("畫面斷言", "資料斷言"):
                if slot in exp:
                    _screen_assertions(errs, f"{w}.預期", exp[slot], True, slot)
    return errs


def validate_fixtures(doc):
    errs = []
    if not isinstance(doc, dict):
        return ["fixtures: 頂層必須是 dict（空輸入不算通過）"]
    if not _keys(errs, "fixtures", doc, {"環境", "解析"}):
        return errs
    env = doc.get("環境")
    if _keys(errs, "環境", env, _ENV_KEYS):
        if not isinstance(env.get("允許寫入"), bool):
            errs.append("環境.允許寫入: 必須是 bool")
        if not isinstance(env.get("含個資"), bool):
            errs.append("環境.含個資: 必須是 bool")
        q = env.get("查證")
        if not isinstance(q, str) or not q.strip().upper().startswith("SELECT"):
            errs.append("環境.查證: 必須是以 SELECT 開頭的查詢語句，不可只是敘事")
        _enum(errs, "環境.資料類別", env.get("資料類別"), DATA_CLASS_VALUES)
    items = doc.get("解析")
    if not isinstance(items, list):
        errs.append("解析: 必須是 list"); return errs
    for i, it in enumerate(items):
        w = f"解析[{i}]"
        if not _keys(errs, w, it, {"條件", "結果", "值", "查詢", "清理", "原因"}, required={"條件", "結果"}):
            continue
        r = it.get("結果")
        _enum(errs, f"{w}.結果", r, FIXTURE_RESULT_VALUES)
        if r == "無法備妥" and not it.get("原因"):
            errs.append(f"{w}: 無法備妥 必須附 原因")
        if r == "建立" and not it.get("清理"):
            errs.append(f"{w}: 建立 的資料必須附 清理 {{方式, 鍵}}")
        if r in ("找到", "建立") and not it.get("值"):
            errs.append(f"{w}: {r} 必須附 值")
        _dict_when_present(errs, f"{w}.值", it.get("值"))
        _str_or_null(errs, f"{w}.查詢", it.get("查詢"))
        _dict_when_present(errs, f"{w}.清理", it.get("清理"))
    return errs


def _run_common(doc, kind):
    errs = []
    if not isinstance(doc, dict):
        return errs + [f"{kind}: 頂層必須是 dict（空輸入不算通過）"], None
    if not _keys(errs, kind, doc, {"_meta", "rules"}):
        return errs, None
    rules = doc.get("rules")
    if not isinstance(rules, dict) or not rules:
        errs.append(f"{kind}.rules: 必須是非空 dict（零條觀察不算通過）")
        return errs, None
    return errs, rules


def validate_run_ui(doc):
    errs, rules = _run_common(doc, "run-ui")
    if rules is None:
        return errs
    imprecise = doc["_meta"].get("步驟不精確") if isinstance(doc["_meta"], dict) else None
    if imprecise is not None:
        if not isinstance(imprecise, list):
            errs.append("run-ui._meta.步驟不精確: 必須是 list")
        else:
            for i, it in enumerate(imprecise):
                w = f"run-ui._meta.步驟不精確[{i}]"
                if _keys(errs, w, it, {"TC", "步驟", "實機"}):
                    for k in ("TC", "步驟", "實機"):
                        if not isinstance(it.get(k), str) or not it[k].strip():
                            errs.append(f"{w}.{k}: 必須是非空 str")
    for rid, o in rules.items():
        w = f"rules[{rid}]"
        if not _keys(errs, w, o, _RUN_UI_KEYS | {"畫面斷言"}, required=_RUN_UI_KEYS):
            continue
        _int(errs, f"{w}.步驟失敗次數", o.get("步驟失敗次數"))
        _int(errs, f"{w}.記錄讀值次數", o.get("記錄讀值次數"))
        res = o.get("結果")
        if res is None:
            if not (isinstance(o.get("步驟失敗次數"), int) and o["步驟失敗次數"] > 0):
                errs.append(f"{w}.結果: 只有 步驟失敗次數 > 0 時才可為 null（沒觀察到≠放行）")
        else:
            _enum(errs, f"{w}.結果", res, RESULT_VALUES)
        if o.get("訊息") is not None and not isinstance(o["訊息"], str):
            errs.append(f"{w}.訊息: 必須是 str 或 null")
        if o.get("訊息位置") is not None:
            _enum(errs, f"{w}.訊息位置", o["訊息位置"], MSG_POS_VALUES)
        _field_changes(errs, w, o.get("欄位變化"))
        _visual_marks(errs, w, o.get("視覺標記"))
        if "畫面斷言" in o:
            _screen_assertions(errs, w, o["畫面斷言"], False)
        net = o.get("網路")
        if not isinstance(net, list):
            errs.append(f"{w}.網路: 必須是 list")
        else:
            for j, n in enumerate(net):
                if _keys(errs, f"{w}.網路[{j}]", n, {"方法", "路徑", "狀態碼"}):
                    _int(errs, f"{w}.網路[{j}].狀態碼", n.get("狀態碼"))
    return errs


def validate_run_api(doc):
    errs, rules = _run_common(doc, "run-api")
    if rules is None:
        return errs
    for rid, o in rules.items():
        w = f"rules[{rid}]"
        if not _keys(errs, w, o, _RUN_API_KEYS):
            continue
        if _keys(errs, f"{w}.請求", o.get("請求"), {"方法", "路徑", "body摘要"}):
            _str_or_null(errs, f"{w}.請求.body摘要", o["請求"].get("body摘要"))
        if _keys(errs, f"{w}.回應", o.get("回應"), {"狀態碼", "錯誤碼", "欄位"}):
            _int(errs, f"{w}.回應.狀態碼", o["回應"].get("狀態碼"))
            _str_or_null(errs, f"{w}.回應.錯誤碼", o["回應"].get("錯誤碼"))
            _list_of_str(errs, f"{w}.回應.欄位", o["回應"].get("欄位"))
    return errs


def validate_db_check(doc):
    """fixture 跑完後唯讀查核 資料斷言 的結果；`_meta.通道` 必填（共用 DB 連線可能被並行 session 切走）。"""
    errs, rules = _run_common(doc, "db-check")
    if rules is None:
        return errs
    meta = doc.get("_meta")
    if not isinstance(meta, dict) or not isinstance(meta.get("通道"), str) or not meta["通道"].strip():
        errs.append("db-check._meta.通道: 必填（如「[readonly-db demo-staging]」）")
    for rid, items in rules.items():
        _screen_assertions(errs, f"rules[{rid}]", items, False, "資料斷言", {"目標", "實際", "查詢"})
        for i, a in enumerate(items if isinstance(items, list) else []):
            if isinstance(a, dict) and (not isinstance(a.get("查詢"), str) or not a.get("查詢", "").strip()):
                errs.append(f"rules[{rid}].資料斷言[{i}].查詢: 必須是非空 str（SQL 原文）")
    return errs


def validate_steps(doc):
    errs = []
    if not isinstance(doc, dict):
        return ["steps: 頂層必須是 dict"]
    if not _keys(errs, "steps", doc, {"規格", "欄位對照", "cases"}):
        return errs
    if not isinstance(doc.get("規格"), dict) or not doc["規格"].get("ffs_sha"):
        errs.append("steps.規格.ffs_sha: 必填（脫鉤偵測用）")
    cases = doc.get("cases")
    if not isinstance(cases, dict):
        errs.append("steps.cases: 必須是 dict"); return errs
    if not cases:
        errs.append("steps.cases: 必須是非空 dict（零條快取不算通過）"); return errs
    for cid, steps in cases.items():
        _steps(errs, f"steps.cases[{cid}]", steps)
    return errs


_KINDS = {"plan": validate_plan, "fixtures": validate_fixtures, "run-ui": validate_run_ui,
          "run-api": validate_run_api, "steps": validate_steps, "db-check": validate_db_check}


def main(argv):
    if len(argv) != 3 or argv[1] not in _KINDS:
        print(f"用法: validate.py <{'|'.join(_KINDS)}> <file>", file=sys.stderr)
        return 2
    try:
        import yaml
    except ImportError:
        print("缺 PyYAML：<PY> -m pip install pyyaml", file=sys.stderr)
        return 2
    with open(argv[2], encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    errs = _KINDS[argv[1]](doc)
    for e in errs:
        print(e)
    print("OK" if not errs else f"{len(errs)} 個錯誤")
    return 0 if not errs else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
