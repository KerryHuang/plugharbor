# 環境與版本比對

## 可驗收的環境

環境清單、網址與可寫性只來自專案設定 `.plugharbor/lifecycle.yml` 的 `qa.environments`（格式見 `${CLAUDE_PLUGIN_ROOT}/references/config.md`）：

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/config.py get qa.environments   # 缺：退出碼 2；只有舊檔 delivery-flow.yml：退出碼 3（停下請使用者改名）
```

- `qa-fixture` 判 `環境.允許寫入`：派工 URL 的 origin（scheme＋host＋port）對到清單上某一項的 `url` origin，取該項 `writable`；對不到 → `false`。`writable` 不是布林值也視為 `false` 並在回傳報告。依據寫進 `環境.依據`（如 `config qa.environments[dev].writable=true`）。不看網址長相、不看 DB 資料量。
- **不可自行推定授權**：清單標 `writable: false` 的環境要寫入，必須由使用者明示授權並寫進派工；沒帶就維持 `false`。
- `含個資` 與可寫性是兩個獨立旗標：可寫的環境也可能載著真實客戶資料。有唯讀 DB 查詢工具才能查證；沒有工具一律判 `true`（保守遮罩）並省略 `環境.查證`（`依據` 仍必填，`查證` 不寫敘事），回報「未查證（無 DB 工具）」。沒有工具**不改變** `允許寫入`：可寫性只看 `writable`，`true` 時前置資料照常走畫面建立。
- 帳密不在設定檔，見下節。

## 取帳密

帳密放專案根 `.plugharbor/qa.local.md`（本機檔、須 gitignore），一個環境兩行 `<環境名>-username`、`<環境名>-password`。**逐鍵取值，不印整檔、不印值**：

```bash
F='<ws>/.plugharbor/qa.local.md'; E='<環境名>'
U=$(sed -n "s/^${E}-username: *//p" "$F"); P=$(sed -n "s/^${E}-password: *//p" "$F")
[ -n "$U" ] && [ -n "$P" ] && echo "有帳密" || echo "無帳密"
```

值只在填登入表單的那一次呼叫出現。取不到 → 回報「無法進入畫面：<環境名> 無帳密」，不換帳號、不猜。

## 版本比對（前端）

前端若在首頁放版本 meta（例如 `<meta name=app-version content="1.2.3-<build sha>">`），尾段 build sha 可判斷交付 commit 是否已部署。交付 commit 取自 Dev 票完工留言。`<fe>` ＝前端 repo 的本機路徑。

```bash
sha=$(curl -s -m 10 https://<your-app>/ | grep -oiE 'app-version content=[^ >]*' | sed 's/.*-//')
git -C <fe> merge-base --is-ancestor <交付commit> "$sha"; echo $?   # 0＝已部署；1＝未含；128＝本機無此 sha，先 pull 再判
```

meta 讀不到（空字串）→ 判不出，照 SKILL.md Step 0 第 4 點問使用者。專案有部署狀態工具就優先用它。

## 版本比對（後端：某 commit 進了哪個版本）

`<be>` ＝後端 repo 的本機路徑。

```bash
git -C <be> for-each-ref --contains <sha> refs/tags --sort=creatordate --format='%(refname:short)' | head -1
# 印出最早含此 commit 的 tag（可能是 beta）；空＝還沒進任何 tag；exit 129「no such commit」＝本機沒有這個 sha
```

- 用 `for-each-ref`，**不要用 `git tag --contains`**：有些專案的權限設定把 `git tag *` 整個擋掉（防止建 tag），連唯讀查詢一起被拒。
- 得到 tag 後與環境實際部署版本比；腳本不能呼叫 MCP，有部署狀態工具時這一步由主 session 做。
- 本機沒有該 sha 時回報「判不出：本機無此 commit」，由使用者決定要不要 fetch，**不自行 `git fetch`**。
