---
name: qa-verify
description: Dev 完工後依驗收案例做實機 E2E 驗收——輸入驗收案例檔（markdown 或 YAML，格式見 acceptance-format.md）或票號（從票面重現步驟產案例），派 agent 對實機逐條驗，機械判定 PASS／FAIL／前端未擋／BLOCKED／未執行／無法比對，產 qa-report.md 與規格校正清單，有票號則回票。加 `--sweep` 為批次模式：撈指派給我的待測票、分類、逐張驗後依結果寫回階段與留言。觸發：「驗收 [案例檔]」「qa-verify [票號]」「這支功能開發完了幫我驗」「掃待測票」「qa-sweep」。不開 Bug 票（單張流程處置欄由人填）。
---

# qa-verify — 驗收案例 → 實機 E2E 驗收

> 非 Claude Code（如 Pi）執行時，先讀 `${CLAUDE_PLUGIN_ROOT}/references/harness-terms.md`（Claude Code 照字面執行可略過），把 Claude 專屬工具與路徑換成對應項。

驗「做出來的跟驗收案例一不一樣」。案例來源不限：人寫的驗收清單、其他 skill 轉出的案例，只要符合 `${CLAUDE_SKILL_DIR}/references/acceptance-format.md`。派工慣例見 `${CLAUDE_PLUGIN_ROOT}/references/dispatch-conventions.md`。

`<PY>` ＝ `command -v python3 || command -v python`（不要寫死）。`<plugin>` ＝ `${CLAUDE_PLUGIN_ROOT}`。
`<ws>` ＝ 專案根的**字面絕對路徑**。所有指令不 `cd`。

## 模式

- 預設：單張流程（下方 Step 0–7）。
- `--sweep [票號] [--dry-run]`：批次模式，做法讀 `${CLAUDE_SKILL_DIR}/references/batch-mode.md`（純後端 Bug 票另見 `references/backend-verify.md`）。批次模式逐張回到單張流程的 Step 0–7 測試，自己只負責撈票、分類、寫回。

## Step 0：前置檢查（缺什麼停在那裡）

1. `bash <plugin>/skills/qa-verify/scripts/preflight.sh <ws>`；exit ≠ 0 → 照它印的補，補不了就停。
   缺 `qa.environments` 或 `.plugharbor/qa.local.md` → 依 `${CLAUDE_PLUGIN_ROOT}/references/harness-terms.md` 的提問方式問使用者（環境名／網址／可否寫入／帳號／密碼），經同意後代寫（格式見 `${CLAUDE_PLUGIN_ROOT}/references/config.md`「qa.environments」；密碼只寫進 `qa.local.md`，不回顯）。**寫入前**跑 `git check-ignore -q .plugharbor/qa.local.md`：未被忽略 → 先把該路徑追加到 `git rev-parse --git-path info/exclude` 印出的檔（本機不入版控，worktree 也適用；專案已有慣例要寫 `.gitignore` 則依專案），並告知使用者；非 git repo 則略過。
2. `ToolSearch("select:mcp__chrome-devtools__navigate_page")` 必須有；缺 → 停，指向 `references/browser-modes.md`。唯讀 DB 查詢工具（專案有提供才有）選配：不可用 → 標記「DB 不可查」（fixtures 省略 `查證`，`依據` 仍必填），plan 有資料斷言時該槽會判「無法比對」。
3. 輸入是票號才需要票務工具：經 `lifecycle:ticket-ops` 的 `get`（讀票）與 `comment`（回票），不直接呼叫任何票務 MCP 或 CLI。ticket-ops 不可用（缺 `ticket.tool` 設定、工具未接）→ 票面模式無法開始，直接停；案例檔模式降級為「只落報告不回票」，明說。帶 `--no-comment` → 不回票，Step 6 改把 `--comment` 輸出寫到 `<工作區>/ticket-comment.md`，由呼叫端統一貼。
4. 有票號才做**環境版本閘**：讀該票完工留言取交付 commit／版本，比對目標環境是否已部署（做法見 `references/environments.md`「版本比對」；有部署狀態工具就用它）。
   **票面指定的測試環境**不在 `qa.environments` → 不硬跑：`--no-comment` 時直接回報「待人工：票面環境 <名稱> 不在設定」結束本輪；其餘情況 `AskUserQuestion`（補進設定／換環境／停）。換環境跑時，依賴該環境特性的 TC 會 BLOCKED，結果不會是嚴格 PASS。判不出或未部署 → **停**，`AskUserQuestion`：換環境／等部署／照跑（照跑要在報告環境節寫「版本未確認」）。
   > 計畫若靠事前推測實機，版本與路由要到 runner 實跑才發現，會造成大量返工——所以版本閘在派工前做。

## Step 1：解析輸入

- `$ARGUMENTS` 是存在的檔案路徑 → **案例檔模式**。先 `<PY> -B <plugin>/skills/qa-verify/scripts/validate.py acceptance <路徑>`，非 `OK` → 停，把錯誤回給使用者（`.md` 或 `.yml`／`.yaml` 皆可）。案例檔 sha：在 git 內用 `git log -1 --format=%h -- <路徑>`，不在 git 內用 `shasum` 前 8 碼。
- `$ARGUMENTS` 含票號（`[A-Z]+-\d+` 或 `#\d+`）→ **票面模式**：經 `lifecycle:ticket-ops` 先 `get` 父票，再逐一 `get` 每個 child id，把各票標題＋body 寫成 `<工作區>/ticket.md`；記下父票 `updatedAt`。功能碼取票標題標明的功能代碼，取不到就用功能名的 ASCII slug 或 `AskUserQuestion` 問。
- 都不是 → 視為功能名，`AskUserQuestion` 請使用者給案例檔路徑或票號。
- 環境：`--env <名稱>`，預設 `qa.environments` 的第一項；網址取該項 `url`。前端路由：從專案前端的 router 設定找該功能的 `path`，實機網址是 `<url>/<path>`（hash 或 history 模式依專案而定，先在實機驗一次）。
- 工作區：`<ws>/.tmp/qa-verify/<案例檔名或票號，小寫 ASCII>/`，`mkdir -p`。

## Step 2：planner（第一閘門）

派 `lifecycle:qa-planner`（model sonnet）：案例檔路徑與 sha、URL、環境名、`<ws>`（登入用）、輸出 `plan.yml`、`steps.yml`（工作區已有上輪的 `steps.yml` 才給）、isolated_context=qa-planner。
票面模式：派工改給 票號、功能碼、`<工作區>/ticket.md`、`updatedAt`、URL、環境名、`<ws>`、輸出 `plan.yml`、isolated_context=qa-planner；案例檔／steps.yml 給 null。planner 回傳第一行是 `票面無可驗預期結果` → 沒有 plan，**不走下方三選一**，直接結束本輪並回報「待人工：票面無可驗預期結果」（選項 2／3 都需要 plan，選了會在 Step 3／5 壞掉）。
回傳第一行有「找不到 ≥ 1」或「不一致」→ **停**，用 `AskUserQuestion` 給使用者看對照表，選：
1. 先校正案例檔（產「規格校正清單」草稿到報告，結束本輪）
2. 照對照繼續（無法比對／未執行會自然出現在報告）
3. 我來補對應（讓使用者填實機欄名，寫回 plan.yml 後 `validate.py plan`）

## Step 3：fixture

派 `lifecycle:qa-fixture`（sonnet）：plan、環境名、URL、`<ws>`（登入用），輸出 `fixtures.yml`、isolated_context=qa-fixture。
回傳 `允許寫入 false` 而使用者要求 CRUD → 告知依據（設定 `qa.environments` 該項 `writable`），不硬寫。`允許寫入` 只看設定，與 DB 工具有無無關：沒有 DB 工具只讓 `含個資` 判 `true`、資料斷言回「未查證（無 DB 工具）」。

## Step 4：runner

`<PY> -B <plugin>/skills/qa-verify/scripts/strip_plan.py <工作區>/plan.yml <工作區>/steps-only.yml <工作區>/db-targets.yml`
派 `lifecycle:qa-runner-ui`（sonnet）：steps-only、fixtures、輸出目錄、案例檔 sha、欄位對照、`<ws>`（登入用，給它寫 steps.yml 用）、isolated_context=qa-runner-<批>。
票面模式：runner 派工的「案例檔 sha」給 `ticket:<票號>@<updatedAt>`；它產的 `steps.yml` 只留在工作區，下輪也不當快取。
回傳「觸發自限停止」→ 記進報告環境節，不重派；**例外**：原因是「超出 context 預算」→ 只把未跑的 TC 拆成新的 steps-only 再派一次（一輪最多拆一次）。
**禁止**用 `general-purpose` 頂替 planner／fixture／runner——它繼承主 session 的模型，瀏覽器操作量大、成本遠高於專用 agent；多張票要驗就逐票走 Step 2–4，不要一次派 20 個通用 agent。
`run-ui.yml` 的 `_meta.contains_pii: true` → 記下來，Step 6 落檔時在報告環境節註明「截圖含個資」。
steps-only 會帶 `畫面斷言目標`（只有目標、沒有期望），runner 對每個目標記 `實際`；runner 回報的 `_meta.步驟不精確` 由 Step 5 的 report.py 彙整成 `plan-patch.yml`。

**資料斷言查核**（strip_plan 有產 `db-targets.yml` 才做）：runner 跑完後再派 `lifecycle:qa-fixture` 走「資料斷言查核」模式：db-targets、fixtures、run-ui、環境名，輸出 `db-check.yml`。runner 沒有 DB 工具，DB 落地的預期（如完工後單據狀態欄）不查就全是無法比對。

## Step 5：判定與報告（主 session 只做 agent 做不到的）

先驗各檔，任一非 `OK` → **停**，把錯誤訊息附在派工 prompt 裡重派對應 agent（plan→planner、fixtures／db-check→fixture、run-ui→runner），不可略過直接 judge：

```bash
<PY> -B <plugin>/skills/qa-verify/scripts/validate.py plan <工作區>/plan.yml
<PY> -B <plugin>/skills/qa-verify/scripts/validate.py fixtures <工作區>/fixtures.yml
<PY> -B <plugin>/skills/qa-verify/scripts/validate.py run-ui <工作區>/run-ui.yml
<PY> -B <plugin>/skills/qa-verify/scripts/validate.py db-check <工作區>/db-check.yml   # 有 db-targets 才驗；壞了重派 fixture
```

```bash
<PY> -B -c "
import sys, json, yaml
sys.path.insert(0, '<plugin>/skills/qa-verify/scripts')
from judge import judge
W = '<工作區>/'
L = lambda f: yaml.safe_load(open(W + f, encoding='utf-8'))
import os
v = judge(L('plan.yml'), L('fixtures.yml'), L('run-ui.yml'),
          db_check=L('db-check.yml') if os.path.exists(W + 'db-check.yml') else None)
json.dump(v, open(W + 'verdict.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
print(v['總計'], v['判讀'])"
<PY> -B <plugin>/skills/qa-verify/scripts/report.py <工作區>/plan.yml <工作區>/fixtures.yml <工作區>/verdict.json \
  --steps <工作區>/steps.yml --run-ui <工作區>/run-ui.yml --out <工作區>/qa-report.md --env <名稱> --date <今天> --by <git user.name> --mode <唯讀|CRUD> --comment [--report-ref <報告放進 repo 後的相對路徑>]
```

`--report-ref` 只在使用者要把報告放進 repo 時給；預設報告留在工作區，不給。`--comment` 的輸出會貼上票務工具，**不得出現本機路徑**——不給 `--report-ref` 時 report.py 就不印報告位置。
report.py 有 `--steps`／`--run-ui` 時，實機步驟與 plan 不符或 runner 回報步驟不精確就產 `<工作區>/plan-patch.yml` 並在報告加「計畫修正草稿」節（回灌 plan 前由人逐條確認，不自動套用）。

judge 拋錯（TC 集合不一致、欄位缺）→ 那是 runner 的產出壞了：**重派 runner 跑整份 plan**（步驟快取讓重跑便宜），把拋錯訊息原文附在派工 prompt 裡；不手改 run 檔、不拼接新舊觀察。

主 session 只補一件事：讀 verdict 裡 FAIL 的 `證據`，若行為在**任何**案例版本都不合理（如對話框標籤後沒帶值），
把該列 `歸因傾向` 改成 `疑似實作缺陷` 並在 `備註` 寫一句理由，重跑 report.py。不改狀態、不填處置。

## Step 6：落檔與回票

- 落檔前先驗報告不含內網 IP：`grep -E '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' <工作區>/qa-report.md`，命中 → **停**，
  改成環境名後重跑 `report.py` 再落檔。
- 報告、`steps.yml`、`plan-patch.yml` 留在 `<工作區>/`（截圖在 `shots/`）；使用者要放進 repo 才複製，且只 add 這些檔（逐檔指名），commit 前 `git status` 驗 staged；**不 push**。
- Step 4 記下 `contains_pii: true` 時，在 `qa-report.md` 的「環境與前置資料」節補一行「截圖含個資，已遮罩／不外流」。
- 有票號：經 `lifecycle:ticket-ops` 的 `comment` 貼 report.py `--comment` 印出的那幾行；票狀態不動。

## Step 7：清理

fixtures `結果: 建立` 的每條，依 `清理` 產 UPDATE 語句列給使用者，**經同意後**由使用者或可寫的 DB 工具執行（寫入工具不預先核准）；
清不掉的列在報告「環境與前置資料」節。刪 `<工作區>/`**以外**的東西一律不做；工作區保留到使用者確認報告。

## 收尾條件

`--no-comment`：「留言已貼」改為「`ticket-comment.md` 已寫」。

下列皆成立才算完成：`qa-report.md` 在工作區（或使用者指定的位置）；有票號且 ticket-ops 可用則留言已貼；
Step 0 已降級者，報告「環境與前置資料」節有一行「未回票：票務工具不可用」；
`總計` 六個數相加＝plan 的 TC 數（少一條就是 judge 沒跑完，不可回報完成）；
「規格校正清單」非空時每條都有人填的處置（改規格／接受差異／開 Bug／待 PO），沒有就回報「未收工：校正 N 條待處置」——skill 不代填。

完成後依動線用 `AskUserQuestion` 建議下一步：處置有「開 Bug」→ 經 `lifecycle:ticket-create`（開票單一入口，它會出草稿請使用者確認）開票，不直接用 `ticket-ops create`（本 skill 不開票）；使用者同意才接著跑，不自動執行。

**瀏覽器收尾**：agent 只關自己的分頁；主 session 若為本次手動起過任何 Chrome（含 9222 附掛），在回報完成的同一輪關掉並驗證（`curl -s -m 2 http://127.0.0.1:9222/json/version` 無回應、無殘留的 Chrome 行程）。

## 不做

不開 Bug 票、不改票狀態、不修程式碼、不打 API（`channel` 不是 `ui` 的案例 planner 不納入 plan，只在回傳列出；請在回報中轉告使用者）、不改案例檔。
