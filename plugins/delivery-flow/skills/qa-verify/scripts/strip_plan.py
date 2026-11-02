#!/usr/bin/env python3
"""從 plan.yml 抽出 runner 能看的部分：id／欄位（實機名）／步驟／寫入／畫面斷言目標。**不含 預期**——預期是答案，會錨定；
畫面斷言只給 目標（要讀什麼），不給 期望／比對。"""
import sys, yaml
from validate import STALE_NOTE_RE

# Windows 預設 cp950：印中文會亂碼、印 emoji 直接炸 UnicodeEncodeError。
# 與 parse_foxpro.py 同一做法，腳本自己處理，不靠呼叫端設 PYTHONUTF8。
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

def strip(plan):
    real = {m["規格"]: m["實機"] for m in plan["meta"]["欄位對照"]}
    cases = []
    for c in plan["cases"]:
        for s in c["步驟"]:
            for key in ("注意", "目標"):
                val = s.get(key)
                if val and STALE_NOTE_RE.search(str(val)):
                    raise SystemExit(f"步驟 {key} 含結論性文字：{c['id']} {val}")
        cases.append({"id": c["id"], "實機欄位": real.get(c["欄位"]), "步驟": c["步驟"], "寫入": c["寫入"],
                      "畫面斷言目標": [a["目標"] for a in c["預期"].get("畫面斷言", [])]})
    return {"meta": {"功能": plan["meta"]["功能"], "功能碼": plan["meta"]["功能碼"]}, "cases": cases}

def db_targets(plan):
    """給 fixture 跑完後查核用：每條 TC 的 資料斷言 目標＋前置條件，不給 期望／比對（同樣防錨定）。"""
    cases = {c["id"]: {"目標": [a["目標"] for a in c["預期"]["資料斷言"]],
                       "前置條件": [p["條件"] for p in c["前置資料"]], "步驟": c["步驟"]}
             for c in plan["cases"] if c["預期"].get("資料斷言")}
    return {"meta": {"功能": plan["meta"]["功能"], "功能碼": plan["meta"]["功能碼"]}, "cases": cases}

def _dump(doc, path):
    assert "預期" not in yaml.safe_dump(doc, allow_unicode=True), "預期 洩漏"
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(doc, f, allow_unicode=True, sort_keys=False)

if __name__ == "__main__":
    # strip_plan.py <plan> <steps-only 輸出> [<db-targets 輸出>]：有 資料斷言 的 TC 才寫第三個檔
    plan = yaml.safe_load(open(sys.argv[1], encoding="utf-8"))
    out = strip(plan)
    _dump(out, sys.argv[2])
    print(f"OK {len(out['cases'])} cases → {sys.argv[2]}")
    if len(sys.argv) > 3:
        targets = db_targets(plan)
        if targets["cases"]:
            _dump(targets, sys.argv[3])
            print(f"OK {len(targets['cases'])} 條 TC 有資料斷言 → {sys.argv[3]}")
        else:
            print("無資料斷言，不產 db-targets")
