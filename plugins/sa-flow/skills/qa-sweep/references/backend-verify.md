# 後端驗證（qa-sweep 類別 2）

純後端／Job 的 Bug 票沒有畫面，`qa-verify` 不打 API（M3），由 qa-sweep 主 session 驗。**結果一律進 S5 確認批，不自動改狀態。**

## 1. 取 TC

讀 QA 票與 Dev 子票描述，每條「預期結果／修正後行為」一條 TC（`TC-B-001` 起）。抽不出 → 該票歸待人工。

## 2. 取 token（打 API 才需要）

- 帳密與網址只從 `<ws>/.claude/live-drive.local.md` 取（`live-drive-url`／`live-drive-username`／`live-drive-password`），**值不得出現在指令字面或任何輸出**——指令一出現字面值就進了對話紀錄。查鍵是否存在只印鍵名：`grep -o '^live-drive-[a-z]*' <檔>`。
- 取 token 的端點、client 與參數依專案的認證方式（OIDC／自有登入 API）而定，host 從 `live-drive-url` 推，不自行拼環境；專案沒寫明 → 問使用者，不猜。
- 由 shell 讀檔進變數再帶入，例：

  ```bash
  F='<ws>/.claude/live-drive.local.md'
  U=$(sed -n 's/^live-drive-username: *//p' "$F"); P=$(sed -n 's/^live-drive-password: *//p' "$F")
  # 以 OIDC password grant 為例；端點與 client_id 依專案
  curl -s -o '<scratchpad>/token.json' -X POST "<token 端點>" \
    --data-urlencode grant_type=password --data-urlencode client_id=<client_id> \
    --data-urlencode "username=$U" --data-urlencode "password=$P"
  ```

  token 只存 scratchpad，用完刪，不 cat 出來。

## 3. 部署確認

後端版本端點的版號常常**不能**對到 commit。能對到就照 `${CLAUDE_PLUGIN_ROOT}/skills/qa-verify/references/environments.md`「版本比對（後端）」判；對不到就改用行為證據：新端點打不存在的 id 看是否回 handler 的 JSON 404；Job 類看修正後才會出現的 DB 狀態。判不出 → 該票歸未部署。

## 4. 驗證

- DB 只走專案提供的唯讀查詢工具，只送純 SELECT；連線名先對名，不憑印象拼。沒有唯讀 DB 工具 → 依賴 DB 的 TC 記 BLOCKED。
- 寫入類驗證：內部環境可自行操作；客戶副本環境先 `AskUserQuestion` 取得同意，Dev 已留的實測資料可直接引用。
- 每條 TC 記：預期（票面原句）、證據（請求方法＋路徑＋狀態碼＋回應摘要，或 SQL＋結果列數／值）、結果 PASS／FAIL／BLOCKED。

## 5. 輸出

寫 `<qa-sweep 工作區>/<票號小寫>-backend.yml`：

```yaml
票號: BUG-822
總計: {PASS: 2, FAIL: 0, 前端未擋: 0, BLOCKED: 0, 未執行: 0, 無法比對: 0}
cases:
  - id: TC-B-001
    預期: "<票面原句>"
    證據: "<請求或 SQL 摘要>"
    結果: PASS
```

`總計` 鍵與 `qa-verify` 的 `verdict.json` 相同，S4 嚴格 PASS 判定共用。報告不含內網 IP（同 qa-verify Step 6 檢查）。
