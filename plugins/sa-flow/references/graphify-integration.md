# Graphify Integration（選配）

Graphify 為選配整合，供 sa-flow skills 引用。所有區塊執行前先做安裝檢查，失敗時靜默跳過，不影響 skill 主流程。

---

## 安裝檢查

> 直譯器一律用 `${GRAPHIFY_PYTHON:-python}`：若 graphify 裝在特定的 Python 環境，
> 以環境變數 `GRAPHIFY_PYTHON` 指向它；未設時退回 `python`。勿寫死 `python`。

```bash
${GRAPHIFY_PYTHON:-python} -c "import graphify" 2>/dev/null
```

- Exit 0 → 繼續執行對應區塊
- 非 0 → 靜默跳過，回到原本 skill 流程，不提示使用者

---

## Query 區塊

**使用者**：`system-analysis`、`specify-backend`、`specify-frontend`

**觸發時機**：取得功能名稱 / 讀取輸入參數之後，讀取任何 MD 文件之前。

**執行步驟**：

1. 執行安裝檢查；失敗則跳過本區塊
2. 決定要查詢的 graph 清單：
   - 讀取當前專案 `CLAUDE.local.md` 或 `CLAUDE.md` 裡的 `graphify.graphs` 設定
   - 有設定 → 使用清單中所有路徑
   - 無設定 → fallback 到 `./graphify-out/graph.json`
3. 逐一對每個存在的 graph 執行 BFS query：
   ```bash
   ${GRAPHIFY_PYTHON:-python} -m graphify query "{功能名稱}" --graph {graph路徑}
   ```
   - graph 檔案不存在 → 靜默跳過該項
4. 合併所有 query 結果作為「現有系統參考上下文」注入本次分析
   - 有結果 → 在分析時優先參考，減少重複讀 MD
   - 無結果 → 繼續原本讀文件流程

**失敗處理**：任何錯誤（graph 損毀、query 指令失敗）→ 靜默跳過該 graph，不中斷 skill。

---

## Update 區塊

**使用者**：`verifying-specs`（驗證後規格已修正時）

**觸發時機**：該 skill 的文件寫入全部落地之後，在完成報告末段。

**執行步驟**：

1. 執行安裝檢查；失敗則跳過本區塊
2. 決定更新對象：讀取 `CLAUDE.local.md` 或 `CLAUDE.md` 的 `graphify.graphs` 設定，取得圖譜；更新路徑用**圖譜建置時的來源根目錄**（如整個 `docs`，非單一功能目錄——manifest 是以來源根目錄為基準的增量比對）。無設定且 `./graphify-out/graph.json` 不存在 → 靜默跳過
3. 在報告末尾詢問：
   > 「本輪文件已更新完成，我可以增量更新知識圖譜（只重抽新增/變更的檔案）。**要更新嗎？**」
4. 使用者確認（是／完成／ok 等肯定回應）→ 以 Skill 工具呼叫 **graphify skill**：
   ```
   /graphify {來源根目錄} --update
   ```
   > ⚠️ 不要用 `${GRAPHIFY_PYTHON:-python} -m graphify update {路徑}`——該 CLI 只重抽 **code 檔**（免 LLM），對 MD 文件不做語意重抽，docs 類圖譜必須走 skill 的 `--update` 增量管線。
5. 使用者否定 → 不執行任何動作，不再提醒

**失敗處理**：更新失敗 → 提示「graph 更新失敗，可稍後手動執行 `/graphify {來源根目錄} --update`」，不中斷流程。
