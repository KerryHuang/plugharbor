# 環境對照（不含密碼）

本檔列出可驗收的環境。依專案實況填寫，**不要放密碼**——帳密請查 workspace 的 `.claude/live-drive.local.md`（本機檔，未納版控）。
網址規則依專案而定，範例：`https://<your-app>/`。實機路由格式（hash 或 history 模式）先在實機驗一次再寫進計畫。

`資料類別` 是 `qa-fixture` 判定 `環境.允許寫入` 的依據（`內部` → true，`客戶副本` → false）——
判準是**環境歸屬**，不是 DB 資料量或公司名（那是 `含個資` 的判準，另外查 DB）：

- `內部`：團隊自有的開發／測試環境，資料可任意異動。
- `客戶副本`：含真實客戶資料（或自客戶正式環境還原）的測試環境，預設不寫入。

## 內部環境

| 環境 | 網址 | 資料類別 | DB 連線（如有唯讀 DB 工具） |
|------|------|------|------|
| `<env-name>` | https://<your-app>/ | 內部 | `<連線名>` 或 無 |

## 客戶副本環境

| 環境 | 網址 | 資料類別 | DB 連線（如有唯讀 DB 工具） |
|------|------|------|------|
| `<env-name>` | https://<your-app>/ | 客戶副本 | `<連線名>` 或 無 |

## 備註（依專案補充）

- 會定期從正式機還原的測試環境：註明還原時間，測試環境上的資料異動隔天會消失。
- 與正式環境共用資料庫伺服器的測試環境：註明風險，動手前先確認。
- 無 DB 連線的環境：`qa-fixture` 無法查可寫性，須請使用者確認。

- 判環境別看本表的 `資料類別`，**不要只看網址**——曾有 fixture agent 只看網址判環境，把可寫的站判成唯讀。「允許寫入」依本表判，「含個資」依 DB 實際資料判，兩旗標分開判。

## 版本比對（前端）

前端若在首頁放版本 meta（例如 `<meta name=app-version content="1.2.3-<build sha>">`），尾段 build sha 可用來判斷交付 commit 是否已部署。
交付 commit 取自 Dev 子票完工留言。`<fe>` ＝前端 repo 的本機路徑。

```bash
sha=$(curl -s -m 10 https://<your-app>/ | grep -oiE 'app-version content=[^ >]*' | sed 's/.*-//')
git -C <fe> merge-base --is-ancestor <交付commit> "$sha"; echo $?   # 0＝已部署；1＝未含；128＝本機無此 sha，先 pull 再判
```

meta 讀不到（空字串）→ 判不出，照 Step 0 第 5 點問使用者。

## 版本比對（後端：某 commit 進了哪個版本）

找根因或驗收時要回答「這個修正進了哪一版、部署了沒」。`<be>` ＝後端 repo 的本機路徑。

```bash
git -C <be> for-each-ref --contains <sha> refs/tags --sort=creatordate --format='%(refname:short)' | head -1
# 印出最早含此 commit 的 tag（可能是 beta）；空＝還沒進任何 tag；exit 129「no such commit」＝本機沒有這個 sha
```

- 用 `for-each-ref`，**不要用 `git tag --contains`**：有些專案的權限設定把 `git tag *` 整個擋掉（防止建 tag），連唯讀查詢一起被拒。
- 得到 tag 後，與環境實際部署版本比：專案有部署狀態工具（MCP）就用它取後端版本；腳本不能呼叫 MCP，這一步由主 session 做。
- 本機沒有該 sha 時回報「判不出：本機無此 commit」，交給使用者決定要不要 fetch，**不自行 `git fetch`**（自動模式常被擋，也會動到別人的工作區）。

## 取其他環境帳密

`live-drive-*` 三個鍵只是預設環境。其他環境的帳密在同一個 `live-drive.local.md` 的「其他環境」節表格（欄：環境名／slug／網址／帳號／密碼），按 slug 逐欄取值，**不印整表、不印值**：

```bash
F='<ws>/.claude/live-drive.local.md'; S='<slug>'
U=$(awk -F'|' -v s="$S" '{x=$3; gsub(/^[ `]+|[ `]+$/,"",x)} x==s {v=$5; gsub(/^[ `]+|[ `]+$/,"",v); print v}' "$F")
P=$(awk -F'|' -v s="$S" '{x=$3; gsub(/^[ `]+|[ `]+$/,"",x)} x==s {v=$6; sub(/（.*/,"",v); gsub(/^[ `]+|[ `]+$/,"",v); print v}' "$F")
[ -n "$U" ] && [ -n "$P" ] && echo "有帳密" || echo "無帳密"
```

密碼欄常帶全形括號註記（如「（未驗證）」），`sub(/（.*/,"",v)` 會去掉；只剩註記＝空值＝無帳密。
