# 規格鏈機制細節

指令一律 bash；Python 寫 `<PY>`，以 `command -v python3 || command -v python` 解析。

## 判現況

```bash
ls {功能目錄}
sed -n '/SPEC-INDEX/,/^---$/p' {規格檔}
grep '^| D-' {功能目錄}/decisions.md      # 檔案不存在 = 尚無決策落檔，不是缺陷
```

## 執行狀態與續跑（`_pm-run.json`）

`{功能目錄}/analysis/_pm-run.json`，只有 PM 寫、worker 不得碰；用 JSON（macOS 系統 python3 沒有 pyyaml）。

```json
{
  "feature_dir": "docs/訂單模組/訂單毛利明細表/",
  "ticket": "ABC-123",
  "skill_commit": "29a580b",
  "updated": "2026-09-02T09:40+08:00",
  "watch": { "armed": false, "target": null },
  "stages": [
    { "stage": "system-analysis", "worker": "order-margin-sad", "pane": "w1:p3",
      "session": "6e81fac4-a04c-432f-ab62-e56ed6975641",
      "prompt_file": ".tmp/dispatch/order-margin-sad.md",
      "output": "docs/訂單模組/訂單毛利明細表/訂單毛利明細表_系統分析文件.md",
      "status": "verified" }
  ]
}
```

`status`：`dispatched`／`stopped`（停在提問）／`verified`（五項驗收過）／`rejected`（驗收未過、已回派）。`watch.armed: false` 且有活著的 worker ＝ 無人看守。
寫入時點：派工後（新增 `dispatched` 列＋`watch`）、驗收後（改 `verified`／`rejected`）、重掛等待後（`watch`）；不要等最後補。

```bash
<PY> ${CLAUDE_PLUGIN_ROOT}/skills/spec-chain/scripts/pm_resume.py \
  {功能目錄}/analysis/_pm-run.json --root <專案根的絕對路徑>
```

它把檔案宣稱與現實對帳（pane 問 `herdr agent list`、產出檔問檔案系統，不採信檔案；產出檔先判），輸出各棒判定；結束碼一律 0，看輸出文字。

## 派工 prompt 模板

```
在 {功能目錄} 執行 sdlc:{skill 名稱}。

【路徑規則】一律絕對路徑或 `git -C <路徑>`；不要 `cd <目錄> && <相對路徑指令>`。
submodule 並排下，相對路徑會靜默解析到錯的 repo，指令照樣成功（已出過兩次寫錯 repo 的事故）。

【全域慣例】（worker 不一定載入專案根 CLAUDE.md，自行遵守）
- git staging 逐檔 `git add <檔>`，禁止 `git add -A`／`git add .`。
- 你是背景 worker，`Edit` 可能被 worktree 隔離攔下：改用 Bash 寫檔，不建 worktree、不停下來問。
- 不要刪暫存資料夾（不用 `rm -rf`／`rm -r`）：要清的路徑列在交棒檔，由 PM 收工統一清；專案規則叫你收工刪除時，以本條為準。
- 要使用者裁決的題目不停下來問（平台／UI 題照 codebase 先例定案）：採建議選項當暫定、繼續做；`decisions.md` 記一列 `狀態`＝`暫定`，正文每處引用寫「（暫定，D-xxx 待確認）」，格式見 `${CLAUDE_PLUGIN_ROOT}/references/decision-record.md`「暫定決策」。push、開票、寫 DB 仍先問。
- {PM 依任務補列其他相關條目，至少涵蓋 git 安全}

【先讀這些，不要整檔載入】
- {功能目錄}/decisions.md
- {FRD 路徑} §0 一頁摘要、§{相關章節}
- {SAD 路徑} §0 一頁摘要、§{相關章節}
依 skills/spec-docs/SKILL.md：先讀 SPEC-INDEX，再 grep "^## " 定位，Read 帶 offset/limit。

【已拍板、不要重問】
{decisions.md 的「決策／選定」兩欄逐列貼入}

【需要看後端程式碼時】
派 subagent 進去，不要自己踩進 submodule。subagent 先讀目標路徑下任一檔，才會載入該 repo 規則。

【交棒點】本棒跑完就停，不接下一棒。本棒內部確認門（如 SAD Step 8.5）照常停下問使用者。

【回報】兩條都做：
1. 落檔 {功能目錄}/analysis/_handoff-{棒名}.md：產出檔路徑、decisions.md 新增哪幾號、有無未決事項。
2. 同一份摘要用 SendMessage 送 PM（{PM 的 session 位址}）。
```

SendMessage 快、檔案準；`--bg` worker 送不出 SendMessage，所以驗收只看檔案。subagent 的 context 沒有專案根 CLAUDE.md，全域慣例要自己寫進 prompt。

不經 PM context 抽決策進 prompt 檔，抽完數列數並與 `decisions.md` 實際列數對照（欄位切錯或漏抽只有這裡攔得到）：

```bash
grep -E "^\| D-[0-9]+" "{功能目錄}/decisions.md" \
  | awk -F'|' '{print "- " $2 "｜" $3 " → **" $4 "**"}' >> "$PROMPT"
```

## 提醒與轉送

停點提醒：「worker『{名稱}』停在提問（{哪一棒}），pane {pane_id}。要回答：`herdr agent attach <pane_id>`」。短時間內同一 worker 再停下，先確認不是自己上次提醒引發的（使用者正在 pane 裡對話）。
使用者把答覆交給 PM 時只原話轉送：`herdr agent prompt <target> "$(cat <答覆檔絕對路徑>)"`。

## 量 context 用量

```bash
<PY> ${CLAUDE_PLUGIN_ROOT}/skills/spec-chain/scripts/ctx.py <sessionId 前綴>...
```

`agent start` 回傳的 `agent_session.value` 即 session id。PM 若先跑過上游，起始數字不能當派工省了多少的對照。

## 驗收

```bash
F={產出檔}; T={對應範本}

# 第 1 項：三條都要過
[ "$(wc -c < "$F")" -ge "$(wc -c < "$T")" ] && echo "體積 OK" || echo "體積 FAIL"
[ "$(grep -cE '^## [0-9A-Za-z]+\.' "$F")" -ge "$(grep -cE '^## [0-9A-Za-z]+\.' "$T")" ] && echo "章節 OK" || echo "章節 FAIL"
grep -oE '\{[^}]+\}' "$T" | sort -u | while read -r ph; do
  grep -qF "$ph" "$F" && echo "殘留佔位符：$ph"
done

# 第 2 項
grep -E '^\| D-[0-9]+' "$(dirname "$F")/decisions.md" | tail -5 | cut -c1-120
sed -n '/^## D\. 決策紀錄/,/^## /p' "$F" | grep -oE 'D-[0-9]+' | sort -u | tr '\n' ' '

# 第 4 項：決策傳播＋暫定標記＋版本機械閘，exit 0 才算過
<PY> ${CLAUDE_PLUGIN_ROOT}/skills/verifying-specs/scripts/check-decision-propagation.py "$(dirname "$F")"
```

- 章節只數編號章（`^## [0-9A-Za-z]+\.`）：`撰寫指南`、`文件資訊` 這類鷹架章產出本來就會刪或併，計入會誤擋。
- 佔位符以範本實際用到的 `{…}` 為準，不要對產出直接 grep `{.*}`（JSON 範例會誤傷）。體積單獨會過原樣複製的空殼，三條互補。
- 第 3 項不重述指令：照 `spec-index-format.md` 規則 6，比對章節編號，不比標題與數量。
- 第 4 項非 0 先回派，不進第 5 項（派 subagent 比對宣稱依循的 D 編號）。

## 使用者裁決回寫：回派樣板

開票前集中裁決（`shared-preludes-details.md`「規格鏈中途裁決」）問完後，交回寫過那幾章的 worker；顧問分流裁定的題同樣用此樣板，裁決欄寫「顧問裁定：{結論}」、`拍板` 填 `顧問`。修正指示檔一題一段，不要只丟一句「照使用者決定改」：

```
使用者已裁決以下暫定題，逐題回寫，不改其他內容：
D-{編號}｜{題目}｜裁決：{維持建議／改為 X}
  - decisions.md：該列「狀態」改「定案」；改為 X 時同步改「選定」與「否決的選項與原因」
  - 正文：{文件}§{章}、{文件}§{章} 的「（暫定，D-{編號} 待確認）」改回一般引用；改為 X 時依 X 改寫該段
回寫的文件升版號並在 CHANGELOG 列本輪 D 編號。
完成後跑 check-decision-propagation.py {功能目錄}，exit 0 才算完成。
不刪暫存（列在交棒檔），只用你有的工具。
```

回派走檔案：worker 有沒有回話與改沒改對無關，回派後重跑五項驗收即可。
