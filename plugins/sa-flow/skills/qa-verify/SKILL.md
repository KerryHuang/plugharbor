---
name: qa-verify
description: Dev 完工後依規格做 E2E 驗收——讀 FFS §8 驗收標準，派 agent 對實機逐條驗，機械判定 PASS／FAIL／前端未擋／BLOCKED／未執行／無法比對，產 qa-report.md 與規格校正清單，有票號則回 QA 子票。無 FFS 的 Bug 票走票面模式（從重現步驟產 TC）。觸發：「驗收 <功能>」「qa-verify <票號>」「這支功能開發完了幫我驗」。不開 Bug 票（處置欄由人填）。
---

# qa-verify — 規格 → 實機 E2E 驗收

> 非 Claude Code（如 Pi）執行時，先讀 `../../references/harness-terms.md`（相對本檔；Claude Code 為 `${CLAUDE_PLUGIN_ROOT}/references/harness-terms.md`，照字面執行可略過），把 Claude 專屬工具與路徑換成對應項。

sa-flow 主鏈最後一棒：verifying-specs 驗「規格站不站得住」，這棒驗「做出來的跟規格一不一樣」。

`<PY>` ＝ `command -v python3 || command -v python`（不要寫死）。`<plugin>` ＝ `${CLAUDE_PLUGIN_ROOT}`。
`<ws>` ＝ workspace 根的**字面絕對路徑**。所有指令不 `cd`。

## Step 0：前置檢查（缺什麼停在那裡）

1. `bash <plugin>/skills/qa-verify/scripts/preflight.sh <ws>`；exit ≠ 0 → 照它印的補，補不了就停。
   缺 `live-drive.local.md` → 問使用者網址／帳號／密碼，經同意後代寫該檔（格式見 `<ws>/.claude/live-drive.local.md` 既有樣式；沒有樣式就寫 `live-drive-url／username／password` 三行）。
2. `<PY> <plugin>/scripts/browser-doctor.py`；非 `OK` → 停。
3. `ToolSearch("select:mcp__chrome-devtools__navigate_page")` 必須有；缺 → 停，指向 `references/browser-modes.md`。唯讀 DB 查詢工具（如專案有提供）選配：檢查是否可用，不可用 → 標記「DB 不可查」，Step 3 交由 `qa-fixture` 請使用者確認環境可寫性；plan 有資料斷言時，該槽會判「無法比對」。
4. 有票號才 `ToolSearch("select:mcp__linear__save_comment")`；缺 → 降級「只落報告不回票」，明說。帶 `--no-comment`（由 `qa-sweep` 呼叫時）→ 不回票，Step 6 改把 `--linear` 輸出寫到 `<工作區>/linear-comment.md`，由呼叫端統一貼。
5. 有票號才做**環境版本閘**：讀該票 Dev 子票的完工留言取交付 commit／版本，比對目標環境是否已部署——版本來源依專案現況：有部署狀態工具就用；沒有就讀前端首頁 `<meta name=app-version>` 尾段的 build sha，用 `git merge-base --is-ancestor` 判交付 commit 是否已含在內（指令見 `references/environments.md`「版本比對」）、後端比對最新 tag。
   **票面指定的測試環境**與 `live-drive-url` 不同 → 先照 `references/environments.md`「取其他環境帳密」查同檔的「其他環境」表；有帳密就以該環境為 `--env` 跑（派工的 URL 換成該環境，agent 依 host 取對應帳密）。只看 `live-drive-*` 三個鍵會把有帳密的環境誤判成沒有。查到無帳密 → 不換環境硬跑：`--no-comment`（qa-sweep 呼叫）時直接回報「待人工：票面環境 <slug> 無帳密」結束本輪；其餘情況照下方 `AskUserQuestion`。換環境跑時，依賴該環境特性的 TC 會 BLOCKED，結果不會是嚴格 PASS。判不出或未部署 → **停**，`AskUserQuestion`：換環境／等部署／照跑（照跑要在報告環境節寫「版本未確認」）。
   > 計畫若靠事前推測實機，版本與路由要到 runner 實跑才發現，會造成大量返工——所以版本閘在派工前做。

## Step 1：解析輸入

- `$ARGUMENTS` 含 `[A-Z]+-\d+` → 票號：`mcp__linear__get_issue` 取標題→功能名；依 `${CLAUDE_PLUGIN_ROOT}/references/doc-boundaries.md`「票↔文件雙向註記」找 FFS，找不到再依功能名 Glob。
- **票面模式**：帶 `--from-ticket`，或票號找不到 FFS 且該票 labels 含 `Bug` → 切票面模式。`get_issue` 該票、`list_issues parentId=<票號>` 列子票並逐張 `get_issue`，把 QA 票與子票的標題＋描述寫成 `<工作區>/ticket.md`；記下該票 `updatedAt`。功能碼取票標題標明的功能代碼，取不到就用功能名的 ASCII slug 或 `AskUserQuestion` 問。
- 否則視為功能名：`Glob {docs-root}/**/<功能名>*前端功能規格書*.md`；多個或零個 → `AskUserQuestion` 讓使用者選。
- 功能碼：取 FFS 標明的功能代碼；專案沒有功能代碼就用功能名的 ASCII slug。前端路由：從專案前端的 router 設定找該功能的 `path`，實機網址是 `<url>/<path>`（hash 或 history 模式依專案而定，先在實機驗一次）。
- 環境：`--env <slug>`；預設 `live-drive.local.md` 的 `live-drive-url`。DB 連線名（如有唯讀 DB 工具）從 `references/environments.md` 對。
- 工作區：FFS 模式 `<ws>/.tmp/qa-verify/<功能碼小寫>/`、票面模式 `<ws>/.tmp/qa-verify/<票號小寫>/`（ASCII），`mkdir -p`。

## Step 2：planner（第一閘門）

派 `sa-flow:qa-planner`（model sonnet）：FFS、BFS（M1 給 null）、URL、`<ws>`（登入用），輸出 `plan.yml`、`steps.yml`（`{docs-root}/<模組>/<功能>/qa/steps.yml` 存在才給）、isolated_context=qa-planner。
票面模式：派工改給 票號、功能碼、`<工作區>/ticket.md`、`updatedAt`、URL、`<ws>`、輸出 `plan.yml`、isolated_context=qa-planner；FFS／BFS／steps.yml 給 null。planner 回傳第一行是 `票面無可驗預期結果` → 沒有 plan，**不走下方三選一**，直接結束本輪並回報「待人工：票面無可驗預期結果」（選項 2／3 都需要 plan，選了會在 Step 3／5 壞掉）。
回傳第一行有「找不到 ≥ 1」或「不一致」→ **停**，用 `AskUserQuestion` 給使用者看對照表，選：
1. 先校正規格（產「規格校正清單」草稿到報告，結束本輪）
2. 照對照繼續（無法比對／未執行會自然出現在報告）
3. 我來補對應（讓使用者填實機欄名，寫回 plan.yml 後 `validate.py plan`）

## Step 3：fixture

派 `sa-flow:qa-fixture`（sonnet）：plan、連線名、URL、`<ws>`（登入用），輸出 `fixtures.yml`、isolated_context=qa-fixture。
回傳 `允許寫入 false` 而使用者要求 CRUD → 告知查證依據，不硬寫。

## Step 4：runner

`<PY> -B <plugin>/skills/qa-verify/scripts/strip_plan.py <工作區>/plan.yml <工作區>/steps-only.yml <工作區>/db-targets.yml`
派 `sa-flow:qa-runner-ui`（sonnet）：steps-only、fixtures、輸出目錄、FFS sha、欄位對照、`<ws>`（登入用，給它寫 steps.yml 用）、isolated_context=qa-runner-<批>。
票面模式：runner 派工的「FFS sha」給 `ticket:<票號>@<updatedAt>`；它產的 `steps.yml` 只留在工作區，不進 docs、下輪也不當快取。
回傳「觸發自限停止」→ 記進報告環境節，不重派；**例外**：原因是「超出 context 預算」→ 只把未跑的 TC 拆成新的 steps-only 再派一次（一輪最多拆一次）。
**禁止**用 `general-purpose` 頂替 planner／fixture／runner——它繼承主 session 的模型，瀏覽器操作量大、成本遠高於專用 agent；多張票要驗就逐票走 Step 2–4，不要一次派 20 個通用 agent。
`run-ui.yml` 的 `_meta.contains_pii: true` → 記下來，Step 6 落檔時在報告環境節註明「截圖含個資」。
steps-only 會帶 `畫面斷言目標`（只有目標、沒有期望），runner 對每個目標記 `實際`；runner 回報的 `_meta.步驟不精確` 由 Step 5 的 report.py 彙整成 `plan-patch.yml`。

**資料斷言查核**（strip_plan 有產 `db-targets.yml` 才做）：runner 跑完後再派 `sa-flow:qa-fixture` 走「資料斷言查核」模式：db-targets、fixtures、run-ui、連線名，輸出 `db-check.yml`。runner 沒有 DB 工具，DB 落地的預期（如完工後單據狀態欄）不查就全是無法比對——曾有一批票因此只能靠主 session 手動補證。

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
  --steps <工作區>/steps.yml --run-ui <工作區>/run-ui.yml --out <工作區>/qa-report.md --env <slug> --date <今天> --by <git user.name> --mode <唯讀|CRUD> --linear [--report-ref docs/<模組>/<功能>/qa/qa-report.md]
```

`--report-ref` 只在 FFS 模式給（報告會落 docs）；票面模式不給。`--linear` 的輸出會貼上 Linear，**不得出現本機路徑**——不給 `--report-ref` 時 report.py 就不印報告位置。
report.py 有 `--steps`／`--run-ui` 時，實機步驟與 plan 不符或 runner 回報步驟不精確就產 `<工作區>/plan-patch.yml` 並在報告加「計畫修正草稿」節（回灌 plan 前由人逐條確認，不自動套用）。

judge 拋錯（TC 集合不一致、欄位缺）→ 那是 runner 的產出壞了：**重派 runner 跑整份 plan**（步驟快取讓重跑便宜），把拋錯訊息原文附在派工 prompt 裡；不手改 run 檔、不拼接新舊觀察。

主 session 只補一件事：讀 verdict 裡 FAIL 的 `證據`，若行為在**任何**規格版本都不合理（如對話框標籤後沒帶值），
把該列 `歸因傾向` 改成 `疑似實作缺陷` 並在 `備註` 寫一句理由，重跑 report.py。不改狀態、不填處置。

## Step 6：落檔與回票

- **票面模式**：跳過下方 mkdir／複製進 docs／docs commit 三件事；IP 檢查、`contains_pii` 註記、回票（或 `--no-comment` 時寫 `linear-comment.md`）照做。
- 落檔前先驗報告不含內網 IP：`grep -E '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' <工作區>/qa-report.md`，命中 → **停**，
  改成連線名或環境代稱後重跑 `report.py` 再落檔。
- `mkdir -p {docs-root}/<模組>/<功能>/qa/`（模組目錄取自 docs 既有第一階目錄，不自創，新增先問使用者）；複製 `qa-report.md`、`steps.yml`、`plan-patch.yml`（Step 5 有產才有）進去（截圖**不**進去）。
- docs 若為獨立 repo／子模組：只 add 這些檔（逐檔指名），commit 前 `git status` 驗 staged；**不 push**。
- 有票號：`mcp__linear__save_comment` 貼 report.py `--linear` 印出的那幾行；票狀態不動。
- Step 4 記下 `contains_pii: true` 時，落檔前在 `qa-report.md` 的「環境與前置資料」節補一行「截圖含個資，已遮罩／不外流」。
- `--sync-spec`（**未驗證，M2**）：把 `規格校正清單` 以 CR 格式套回 FFS（走 `references/cr-update-flow.md` Step 2 起；欄位改名改 §4.1／§7.1，欄位不存在刪該列並在 changelog 註「qa-verify 校正」，互動模型改 §2.2／§5.3）。**沒有 `--sync-spec` 不動 FFS。**

## Step 7：清理

fixtures `結果: 建立` 的每條，依 `清理` 產 UPDATE 語句列給使用者，**經同意後**由使用者或可寫的 DB 工具執行（寫入工具不預先核准）；
清不掉的列在報告「環境與前置資料」節。刪 `<工作區>/`**以外**的東西一律不做；工作區保留到使用者確認報告。

## 收尾條件

票面模式：「`qa-report.md` 在 docs 且已 commit」改為「`qa-report.md` 在工作區」。`--no-comment`：「留言已貼」改為「`linear-comment.md` 已寫」。其餘條件照舊。

四者皆成立才算完成：`qa-report.md` 在 docs 且已 commit；有票號且 Linear 可用則留言已貼；
Step 0 已降級者，改為報告「環境與前置資料」節有一行「未回票：Linear 不可用」；
`總計` 六個數相加＝plan 的 TC 數（少一條就是 judge 沒跑完，不可回報完成）；
「規格校正清單」非空時每條都有人填的處置（改規格／接受差異／開 Bug／待 PO），沒有就回報「未收工：校正 N 條待處置」——skill 不代填（曾有校正條目處置全空、規格未回寫就回報完成）。

完成後依動線用 AskUserQuestion 建議下一步：處置有「開 Bug」→ `sa-flow:linear-create` 開 Bug 樹（本 skill 不開票）；規格校正清單有「改規格」→ 依 `references/cr-update-flow.md` 回寫規格；全 PASS、票已 Done 且 docs 有 `*_{票號}.md` → `sa-flow:consolidate-docs`（CR 收口要把票號檔併回主規格）；使用者同意才接著跑，不自動執行。

**瀏覽器收尾**：agent 只關自己的分頁；主 session 若為本次手動起過任何 Chrome（含 9222 附掛），在回報完成的同一輪關掉並驗證（`curl -s -m 2 http://127.0.0.1:9222/json/version` 無回應、無 `puppeteer_dev_chrome_profile`／`claude-shared-chrome` 行程）。

## 不做

不開 Bug 票、不改票狀態、不修程式碼（M2）、不打 API（M3）、不動 FFS（除非 `--sync-spec`）。
