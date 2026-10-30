---
name: config-doctor
description: 全面健檢 Claude Code agent-system 設定——User 層 ~/.claude 與當前專案 .claude 的 settings／skills／rules／agents／hooks／CLAUDE.md，可選加自家 plugin marketplace 結構掃描；產出 P0–P3 分級報告、逐批拍板後修復並重掃驗證。Use when 使用者輸入 /config-doctor、要求「健檢 claude 設定」「agent-system 健檢」「檢查 skill/rule/agent 設定」。
argument-hint: "[--marketplace <目錄>] [--quick]"
disable-model-invocation: true
---

# config-doctor — Claude Code 設定健檢

角色：agent-system 健檢醫生兼修復編排者。對象：User 層 `~/.claude`＋當前專案 `.claude`（含根 CLAUDE.md）；本機另裝有其他 agent CLI（Codex、Antigravity `agy`、pi）時，它們的設定與副本一併納入；帶 `--marketplace <目錄>` 時加掃自家 plugin 源碼的結構與版本一致性。**不審**第三方 plugin 內容（只查與自家設定的衝突）、不改 plugin cache。

**與內建 `/doctor` 分工**：`/doctor` 是第一層、本 skill 是第二層——**先跑 `/doctor`，再跑本 skill**。
交給 `/doctor`：安裝健康、版本、擴充使用率與未使用清理、被拒指令 allowlist、hook 計時、settings 與 agent frontmatter 的可解析性，以及 CLAUDE.md 的「可推導內容修剪」與「改延遲載入」。
本 skill 只做 `/doctor` 不查的**跨層一致性與時效性**：跨層同名檔與分層引用漂移、觸發詞撞名、permissions 規則之間的矛盾與冗餘（不重做使用率統計）、設定 ↔ 內建 system prompt 的重疊與牴觸、rules／skills 指涉的路徑與旗標是否還存在、`--marketplace` 的自家 plugin 結構與版本一致性。
CLAUDE.md 兩邊都碰但角度不同：`/doctor` 問「這段能不能從 codebase 推導出來」，本 skill 問「這段跟別層或內建有沒有打架」——重疊的結論以先跑的 `/doctor` 為準，不重複提案。

`--quick`：只跑 Phase 1 結構掃描並回報，不進後續階段。

## 鐵律

1. **掃描結果是疑點不是結論**——每個 P0/P1 都先驗真偽再入報告：可能是刻意設計（先查 auto-memory 與檔內註記）或範例文字誤判。
2. **報告必須以文字收尾的獨立回合完整輸出**，其後不得接任何工具呼叫；下一回合才開始拍板提問（同回合先印再問＝報告被吞）。
3. **修復只做拍板核准項**；未核准項在報告標「保留現狀」留痕。
4. 修復規則：本地檔直改；自家 plugin 改動走該 repo 的版本 bump＋commit 慣例，並提醒使用者更新 plugin 才生效（改 source ≠ 生效）；第三方只能停用或建議，不碰 cache。

## Phase 0：範圍確認與盤點

1. 先偵測其他 CLI：`for c in codex agy pi; do command -v "$c"; done`。再以 AskUserQuestion 確認範圍（若使用者未指明）：是否含自家 marketplace、是否納入偵測到的 CLI、修復模式（預設：報告後逐批拍板）。
2. 派一個唯讀 agent（Explore 型）盤點：兩層的檔案清單與行數、settings 非預設欄位、hooks 指向、installed plugins 與版本。盤點只列事實不評論。
3. 納入的 CLI，用它自己的 CLI 或文件查出設定位置，不憑記憶。盤點四件事：指令檔、rules／skills 副本與產生它的腳本、plugin 快照版本、MCP 與權限設定。設定只讀 key，不印 env／token。產生腳本寫進報告，Phase 4／5 會用到。

**驗證**：得到兩層完整清單與 plugin 安裝狀態。

## Phase 1：結構掃描（機械）

`<PY>` = 本機 python 直譯器。**不要寫死 `python`**：macOS 只有 `python3`，Windows Git Bash
多半只有 `python`——用 `$(command -v python || command -v python3)` 取存在的那個。
腳本只用標準庫，Python 3.8 以上都跑得動。

```bash
<PY> ${CLAUDE_SKILL_DIR}/scripts/health_scan.py --project <專案根目錄> [--marketplace <目錄>]
<PY> ${CLAUDE_SKILL_DIR}/scripts/hardcode_scan.py ~/.claude/{CLAUDE.md,settings.json,skills,rules,agents,hooks} <專案>/.claude <專案>/CLAUDE.md [<marketplace>/plugins]
```

涵蓋：frontmatter 合法性、斷鏈、hook／statusLine 腳本存在性、孤兒空殼、settings JSON、enabledPlugins 對齊、marketplace 版本一致性。輸出 `FINDING|P0-P3|area|message` 逐行。
**掃描範圍含 plugin skill**：skill 不只在 `~/.claude/skills` 與 `<專案>/.claude/skills`，也可能由已安裝的 plugin 提供（`~/.claude/plugins/` 下，屬第三方，只查與自家設定的衝突、不審內容）。自己維護的 plugin 源碼用 `--marketplace <目錄>` 帶進來，預設不帶就只掃 user 層與專案層。

`hardcode_scan.py` 找寫死的機器值：家目錄、任何磁碟代號的路徑、暫存路徑、私有 IP、localhost 埠、email。只掃文字設定類副檔名（md、py、sh、mjs、js、ts、json、toml、yml、yaml），`*.local.*` 與 `.env*` 不掃，因為那裡本來就是放這些值的地方。~/.claude 只傳上面列的路徑，不要整個傳進去，否則會掃到 plugin cache（第三方）、memory 與 transcript。命中處逐筆判定：工具的固定預設值、引用的證據原文、由版控範本安裝時展開的本機檔（範本本身沒寫死），標「判定保留」；其餘改指向 `*.local.md`／`.env` 的設定鍵。這支腳本沒有 allowlist，重掃時判定保留的項目仍會出現，靠報告的拍板紀錄結案（見完成判準）。**不要改用合併的 grep regex**：BSD 與 GNU 語法不同，錯誤又常被 `2>/dev/null` 吞掉，結果是靜默回 0 筆。

**腳本失敗時的降級**：`health_scan.py` 因 Python 環境／路徑／例外跑不起來時，**不中止流程**——改由主線手動掃描補上腳本涵蓋項（frontmatter 合法性、斷鏈、腳本存在性、settings JSON parse、enabledPlugins 對齊、marketplace 版本），並在報告標明「Phase 1 走降級手動掃描」。`--quick` 若腳本失敗則回報無法完成快掃、建議修復腳本或改跑完整流程。

**驗證**：腳本跑通（或已降級手動掃描並標記）；每個 P0/P1 逐項驗真偽（讀該檔上下文＋查記憶），標記「屬實／誤判／刻意設計」。`--quick` 模式到此輸出結果即結束。

## Phase 2：重複與衝突

- 跨層同名／同主題檔（rules、skills）；分層引用（「詳見 user 層」式）逐條比對是否漂移。
- CLAUDE.md ↔ rules 逐字重複（雙載）；兩層 CLAUDE.md 之間重複。
- 觸發詞撞名：本地 skills 與各 plugin skills 的 description 對照；已有導覽 skill 管理撞名者標「受管理」。
- permissions 合併視角：全放行＋deny 覆蓋度、ask 守門、與 rules 的矛盾、跨層冗餘。
- **設定 ↔ 內建 system prompt 重疊**：CLAUDE.md／rules／shared 的每一條，對照本 session 已載入的
  內建指示。**這項必須主線自己做**——subagent 的 system prompt 不同，派出去等於拿錯基準比對。
  冗餘（內建已明載同義）列 P2、牴觸（內建要求相反行為）列 P1。刪冗餘不改變行為，因為內建在管。

**驗證**：每筆衝突都指出兩個具體位置（檔案＋行）；與內建重疊者改附內建原文片段當對照側。

## Phase 3：內容品質審查

**reviewer agents 在**（本 plugin 的 `agents/*-reviewer.md`，叫用名為 `toolkit:claudemd-reviewer` 等；也可能有 user 層 `~/.claude/agents/*-reviewer.md` 的同名副本）：一則訊息並行派發——claudemd-reviewer×每份 CLAUDE.md、rule-reviewer×每層 rules 一批、skill-reviewer×每 3–4 個 skill 一批、subagent-reviewer×agents、hook-reviewer×hooks。prompt 附上刻意設計白名單（Phase 1 已判定者），避免重複誤報。

**reviewer 不在**（例如新機器還沒 install）：主線依 [references/review-checklist.md](references/review-checklist.md) 逐元件自審。

**驗證**：所有元件都被某個 reviewer 或自審覆蓋。

## Phase 4：時效性抽驗

- rules／skills 指涉的路徑、工具、旗標抽驗存在性；CLAUDE.md 列舉的結構（子模組表等）與現狀比對（`.gitmodules`、目錄實況）。
- 設計稿／殘檔對照現狀判定歸檔；auto-memory 中設定相關記憶與現狀對勘。
- 納入的其他 CLI 逐項比對：副本與來源一致（重跑產生腳本，回報 0 個檔變更、或 diff 為空）；plugin 快照版本等於 marketplace 版本；MCP 與權限設定沒有違反 Claude 端的紅線（例如 Claude 要求確認的寫入工具，在該 CLI 不得直接放行）；實跑一次非互動模式，確認讀得到使用者層與專案層指示。FINDING 的 area 用 `cli:<名稱>`。

**驗證**：每筆時效問題附「文件說 vs 實況」證據對。

## Phase 5：報告 → 拍板 → 修復 → 重掃

1. 彙整分級報告落檔專案 `.tmp/`（或使用者慣用暫存路徑）：**P0 失效**（壞掉／不生效／斷鏈）、**P1 衝突落後**、**P2 品質**、**P3 建議**、**通過項**、**修復批次建議**（低風險直改／重寫類／大工程／使用習慣決策，各為一批）。
2. 報告全文以獨立回合輸出（鐵律 2），等使用者回應。
3. 逐批 AskUserQuestion 拍板（一次一題；使用習慣類 settings 決策逐項問）。
4. 依批次修復；hook 類修完**實際執行驗證** exit code；大檔拆分用腳本按行號切（避免手抄漂移）並驗行數守恆。
5. 權限／核准類設定改完，用**無害呼叫實際觸發一次**（唯讀查詢、不存在的目標）。該擋的要看到確認畫面、拒絕訊息或「沒有這個工具」，才算通過；呼叫有打到目標服務就是不通過，即使服務自己回錯也一樣。
6. 改到有副本的來源，要跑 Phase 0 記下的產生腳本，並比對副本已含這次的改動；手動維護的平行檔（例如內容相同、只差工具名稱的兩份指令檔）要同步改另一份，diff 只剩預期差異。
7. 重跑 Phase 1 腳本：除已判定「刻意設計／誤判／保留現狀」項外**全綠**才算完成；user 層檔案若有 dotfiles repo（如 claude-home 型）提醒回同步。

**完成判準（二元）**：重掃輸出中每一筆 FINDING 都能對應到「已修復」或「拍板保留」其一；報告檔含拍板紀錄。

## Red Flags — 想到這些就停

- 「掃描器報 P0，直接修」→ 先驗真偽；本 skill 誕生的那次健檢就有 2 筆 P0 是刻意設計與範例誤判。
- 「報告和拍板問題同回合發，省一輪」→ 回合中段文字不會顯示，報告會整份被吞。
- 「plugin source 改好了，收工」→ cache 不自動更新，未提醒使用者更新＝修了等於沒修。
- 「命名／語言不合房規，列缺陷」→ 先查使用者的慣例豁免記憶。
- 「reviewer 說有問題就照改」→ reviewer 建議也要驗證（實地查檔），確認非誤報再改。
- 「這條規則寫得像鐵律，一定有用」→ 先問它是不是內建 system prompt 已經在管。
  規則寫得越斬釘截鐵，越可能是為舊模型寫的、現在只剩下製造衝突。
- 「權限設定寫對了，就有擋」→ 要實際觸發才算數。曾有 CLI 在全域「不詢問」模式下，把逐工具的 `prompt` 設定整個略過，寫入工具照樣直接執行。
- 「只掃 Claude 就好」→ 其他 CLI 讀的是副本與自己的設定，Claude 端修好不代表它們也好了。
