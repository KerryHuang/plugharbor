#!/usr/bin/env python3
"""qa-report.md 與 Linear 留言排版。只排版，不判定——判定全在 judge 的輸出裡。"""
import json
import os
import sys

# Windows 預設 cp950：印中文會亂碼、印 emoji 直接炸 UnicodeEncodeError。
# 與 parse_foxpro.py 同一做法，腳本自己處理，不靠呼叫端設 PYTHONUTF8。
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

_ORDER = ["PASS", "FAIL", "前端未擋", "BLOCKED", "未執行", "無法比對"]
_NEEDS_HUMAN = {"FAIL", "前端未擋", "BLOCKED", "未執行", "無法比對"}


def _summary(totals):
    return " / ".join(f"{s} {totals[s]}" for s in _ORDER)


def _fmt(v):
    if v is None:
        return "—"
    if isinstance(v, (list, dict)):
        return json.dumps(v, ensure_ascii=False, default=str)  # yaml 會把未加引號的日期解析成 date
    return str(v)


def _evidence(c):
    e, o = c["證據"]["預期"], c["證據"]["觀察"]
    if o is None:
        return "（無觀察）"
    parts = [f"結果 {e['結果']}→{_fmt(o['結果'])}"]
    if e["訊息"] is not None or o["訊息"]:
        parts.append(f"訊息「{_fmt(e['訊息'])}」→「{_fmt(o['訊息'])}」")
    if e["欄位變化"] or o["欄位變化"]:
        parts.append(f"欄位變化 {_fmt(o['欄位變化'])}")
    if e["視覺標記"] or o["視覺標記"]:
        parts.append(f"視覺標記 {_fmt(o['視覺標記'])}")
    mark = {"通過": "✓", "不成立": "✗", "無法比對": "?"}
    for slot in ("畫面斷言", "資料斷言"):
        if c["證據"].get(slot):
            parts.append(f"{slot} " + "、".join(
                f"{mark[a['結果']]}{a['目標']} {a['比對']} {_fmt(a['期望'])}→{_fmt(a['實際'])}" for a in c["證據"][slot]))
    return "；".join(parts)


def plan_patch(plan, steps_doc, run_ui):
    """runner 實機成功步驟（steps.yml）與 plan 現行步驟不同者，加上 runner 回報的「步驟不精確」（去重）。
    只比 動作＋欄位／目標 的序列；整理成草稿，回灌 plan 前由人逐條確認。"""
    sig = lambda steps: [(s.get("動作"), s.get("欄位") or s.get("目標")) for s in steps or []]
    cases = {c["id"]: c for c in plan["cases"]}
    fixes = [{"TC": cid, "現行步驟": cases[cid]["步驟"], "實機步驟": actual}
             for cid, actual in ((steps_doc or {}).get("cases") or {}).items()
             if cid in cases and sig(actual) != sig(cases[cid]["步驟"])]
    seen, imprecise = set(), []
    for it in ((run_ui or {}).get("_meta") or {}).get("步驟不精確") or []:
        key = (it["TC"], it["步驟"], it["實機"])
        if key not in seen:
            seen.add(key); imprecise.append(dict(it))
    return {"修正": fixes, "步驟不精確": imprecise}


def render_report(plan, fixtures, verdict, meta, fixes=None, patch=None):
    m, src = plan["meta"], {c["id"]: c for c in plan["cases"]}
    gs = verdict["全域訊號"]
    src_line = (f"規格 FFS {m['規格']['ffs']['sha']}" if "ffs" in m["規格"]
                else f"來源 票面 {m['規格']['ticket']['票號']} @ {m['規格']['ticket']['updatedAt']}")
    L = [f"# {m['功能']}（{m['功能碼']}）QA 驗證報告", "",
         f"環境 {meta['環境']}｜租戶 {fixtures['環境']['租戶']}（{fixtures['環境']['資料類別']}）｜"
         f"{src_line}｜執行 {meta['執行日期']} {meta['執行者']}｜"
         f"模式 {meta['模式']}｜含修復 {'是' if meta['含修復'] else '否'}", "",
         f"全域訊號：欄位找不到 {gs['欄位找不到']}｜互動模型 {'一致' if gs['互動模型一致'] else '不一致'}", "",
         "## 結論一行", "", _summary(verdict["總計"]), "", f"判讀：{verdict['判讀']}", "",
         "## 需要人決定的", "",
         "處置值域：開Bug｜改規格｜接受差異｜待PO裁決（由人填，skill 不填）", "",
         "| TC | 狀態 | 歸因傾向 | 規格章節 | 證據（預期→觀察） | 備註 | 處置 |",
         "|---|---|---|---|---|---|---|"]
    for c in verdict["cases"]:
        if c["狀態"] in _NEEDS_HUMAN:
            s = src[c["id"]]["來源"]
            L.append(f"| {c['id']} | {c['狀態']} | {_fmt(c['歸因傾向'])} | {s['文件']} {s['規則章節']} | "
                     f"{_evidence(c)} | {'；'.join(c['備註']) or '—'} |  |")
    if fixes:
        L += ["", "## 修復期間修正", "", "| TC | 改了哪些檔 | commit | 修前 → 修後 |", "|---|---|---|---|"]
        L += [f"| {f['id']} | {', '.join(f['檔案'])} | {f['commit']} | {f['修前']} → {f['修後']} |" for f in fixes]
    L += ["", "## 規格校正清單", ""]
    if verdict["規格校正"]:
        L += [f"- **{x['類型']}**：{x['內容']}" for x in verdict["規格校正"]]
    else:
        L.append("（無）")
    L += ["", "## 全部 TC 逐條", "", "<details><summary>展開</summary>", "",
          "| TC | 狀態 | 證據 | 備註 |", "|---|---|---|---|"]
    L += [f"| {c['id']} | {c['狀態']} | {_evidence(c)} | {'；'.join(c['備註']) or '—'} |" for c in verdict["cases"]]
    L += ["", "</details>"]
    if patch and (patch["修正"] or patch["步驟不精確"]):
        cell = lambda v: str(v).replace("\n", " ").replace("|", "\\|")
        L += ["", "## 計畫修正草稿", "",
              f"實機成功步驟與 plan 不符 {len(patch['修正'])} 條、runner 回報步驟不精確 {len(patch['步驟不精確'])} 條，"
              "全文見 `plan-patch.yml`（回灌 plan／steps 前逐條確認）。", "",
              "| TC | 類型 | 內容 |", "|---|---|---|"]
        L += [f"| {x['TC']} | 步驟與實機不符 | 見 plan-patch.yml |" for x in patch["修正"]]
        L += [f"| {x['TC']} | 步驟不精確 | {cell(x['步驟'])} → {cell(x['實機'])} |" for x in patch["步驟不精確"]]
    L += ["", "## 環境與前置資料", "",
          f"- 可寫性查證：`{fixtures['環境']['查證']}` → 允許寫入 {fixtures['環境']['允許寫入']}",
          f"- 含個資：{'是' if fixtures['環境']['含個資'] else '否'}"]
    for it in fixtures["解析"]:
        tail = f"，清理 {_fmt(it.get('清理'))}" if it["結果"] == "建立" else ""
        tail = f"，原因 {_fmt(it.get('原因'))}" if it["結果"] == "無法備妥" else tail
        L.append(f"- {it['條件']}：{it['結果']} {_fmt(it.get('值'))}{tail}")
    return "\n".join(L) + "\n"


def render_linear_comment(plan, verdict, report_ref=None):
    # 留言會貼上 Linear：只放 docs 相對路徑，本機工作區路徑不外流（票面模式沒有 docs 落點就不印）
    m = plan["meta"]
    lines = [
        f"qa-verify {m['功能']}（{m['功能碼']}）",
        _summary(verdict["總計"]),
        f"判讀：{verdict['判讀']}",
    ]
    if report_ref:
        lines.append(f"報告：{report_ref}")
    lines.append(f"規格校正 {len(verdict['規格校正'])} 項；處置欄待填。")
    return "\n".join(lines) + "\n"


def main(argv):
    import argparse, yaml
    p = argparse.ArgumentParser()
    p.add_argument("plan"); p.add_argument("fixtures"); p.add_argument("verdict_json")
    p.add_argument("--out", required=True); p.add_argument("--linear", action="store_true")
    p.add_argument("--report-ref")  # --linear 印的報告位置（docs 相對路徑）；不給就不印
    p.add_argument("--env", required=True); p.add_argument("--date", required=True)
    p.add_argument("--steps"); p.add_argument("--run-ui")  # 給了才產 plan-patch.yml
    p.add_argument("--by", required=True); p.add_argument("--mode", choices=["唯讀", "CRUD"], required=True)
    a = p.parse_args(argv[1:])
    plan = yaml.safe_load(open(a.plan, encoding="utf-8"))
    fixtures = yaml.safe_load(open(a.fixtures, encoding="utf-8"))
    verdict = json.load(open(a.verdict_json, encoding="utf-8"))
    meta = {"環境": a.env, "執行日期": a.date, "執行者": a.by, "模式": a.mode, "含修復": False}
    load = lambda path: yaml.safe_load(open(path, encoding="utf-8")) if path else None
    patch = plan_patch(plan, load(a.steps), load(a.run_ui))
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(render_report(plan, fixtures, verdict, meta, patch=patch))
    if patch["修正"] or patch["步驟不精確"]:
        with open(os.path.join(os.path.dirname(os.path.abspath(a.out)), "plan-patch.yml"), "w", encoding="utf-8") as f:
            yaml.safe_dump(patch, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
    if a.linear:
        print(render_linear_comment(plan, verdict, a.report_ref))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
