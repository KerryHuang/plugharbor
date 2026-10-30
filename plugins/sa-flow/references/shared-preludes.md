# Shared Preludes — 常駐卡

> 每棒都載，故只留要點；案例與細節在 `shared-preludes-details.md`（同名節，命中才讀）。

## 核心原則：問題漏斗——實證 → 顧問 → 使用者
每個要決定的問題依序過三層，前一層解得掉就不往下送：
1. **實證**：先用真實證據驗證**問題本身**。除了查現行方案（①同族既有產出 ②專案慣例 ③上游文件／`analysis/` ④現行 codebase），涉及資料語意或行為的一定要拿一手證據：舊系統原始碼（附行號）、測試環境 DB 實查（SELECT 帶 `DB_NAME()`）、實機畫面／列印／匯出、現行系統行為。證據推翻問題前提 → 撤題；證據直接給出答案（對齊舊系統、平台先例）→ 採用並標依據。
2. **顧問**：實證後仍有判斷空間的（domain 邊界、口徑取捨、方案選擇），交 domain 顧問（`domain-advisor`）判斷並提出解法；顧問能裁定的就定案（`拍板`＝顧問）。舊系統移植以舊系統為最終驗收基準，顧問只能往對齊舊系統裁定。
3. **使用者**：只剩前兩層解不了的——偏離舊系統、業務／商業取捨、不可逆、顧問與 SA 意見相左、證據不足。題目附「實證查到什麼、顧問怎麼看」。
**平台／UI 慣例以現行 codebase 為準**（分頁與每頁筆數、空值與數字格式、對話框開法、匯出與列印管道等）：照既有先例直接採用並標檔案路徑，不提問、不記暫定、不以舊系統對齊為由偏離；無先例或先例互相衝突才問。清單見 details 同名節。

## 互動詢問規範
必用 `AskUserQuestion`；推薦項置首標「（推薦）」；**一律一次一題**（每個裁決一次 `AskUserQuestion`，不列清單讓人批次勾選，回報結尾的提問也一樣）；長內容先以文字收尾一回合再問。**題目要讓沒跟上前文的人一看就懂**：交代背景、白話先行代碼放括號、選項寫選了會怎樣（細則見 details 第 5 條）。

## 核心原則：不猜測
先找答案→找不到才問（附建議）→確認後才寫→寫前總清查。禁 `[需要澄清]`。

## 核心原則：分析嚴謹度閘
下結論（需新建／沒有／根因是 X）前逐項過六條閘：來源查齊、深度到源頭、現況對齊、維度齊全、domain 邊界必叫顧問、證據優先；結論標 Confirmed／Likely／Unknown。全文與踩雷索引見 `analysis-rigor.md`。

## 核心原則：權威來源優先序
①範本與一手證據定格式與結論 ②既有同類產出只給在地化參數 ③`analysis/*.yml`／他人結論只是線索。動手前問：我照的是範本，還是某人上次的產出？

## 核心原則：決策回寫的掃描義務
回寫前列全部落點（四份規格含索引與 CHANGELOG、`analysis/*.yml`、上游既定敘述）。硬性四條：契約異動先枚舉現行契約；yml 與規格同批更新；以語意全檔 grep 不用行號；**取代不追加**——舊敘述必刪，回寫後正文淨增 >10% 記 `decisions.md`。

## Step 0.3: Plugin 版本對版
鏈起頭與每個硬性停點，比對已載入的 plugin 版本與 marketplace（`kerryhuang-plugins`）最新版本。跨 patch 一行告知；跨 minor 以上停下建議 `/reload-plugins`。查不到 marketplace 資訊則略過。

## 核心原則：技術中立
只寫做什麼、輸入輸出、規則與**約束**；選型與**手段**（framework、快取、鎖、佇列、儲存位置、併發原語、重試做法）由 RD／PG 決定——規格遇到手段層問題寫成 **TD 留置**（約束＋現況＋陷阱，見 `decision-record.md`），不定案；完工後回寫、TD 轉已定案並註「完工回寫：實作對齊」。

## Step 0.5: Docs 同步
若 docs 在獨立 repo，開工前先 pull 一次（每 session 一次）；docs 在本 repo 則略過。

## Step 0.6: 落檔位置
規格一律落 `{docs-root}/{模組}/{功能}/`。**模組名取自專案既有的第一階模組目錄，禁止自創**——
不在清單內時先確認是不是既有模組的子功能，真要新增先問使用者。
會議記錄、開發流程產物（ADR／code review／debug／brainstorming 草稿）依專案既有目錄慣例落檔；
**一律不得自建 docs 第一階目錄**，都不適用就問使用者。
> 教訓：agent 自由填 `_context.yml` 的模組欄位會長出平行目錄與重複規格，演進多日才被發現——模組名只能取自既有目錄。

## Step 0.7: Graphify 查詢（選配）
依 `graphify-integration.md` Query 區塊，同功能每 session 一次，未安裝靜默跳過。

## Step 0.8: 分析落檔與共用
勘察一律落 `analysis/`（`db-analysis.yml`／`reuse-scan.yml`／`ui-survey.md`／`consultant-notes.md`／`_context.yml`），下游先讀只補缺。每筆記 `source`／`scanned_at`；否定結論標 `confirmed`／`not_found_by`。**`_context.yml` ≤5KB 純路徑指標，禁放分析內容**；**`db-analysis.yml` 首段 `_index:` 列 tables，下游 `grep -n '^  {TABLE}:'` 只讀該表段**。

## 顧問桌
唯一定義在 `consultant-desk.md`。

## PDF 轉檔通則
一律 `sa-flow:pdf-converter`，產出放功能 docs 目錄。

## 引用方式（在 SKILL.md 中）
`> 核心原則 / 前置步驟：依 ${CLAUDE_PLUGIN_ROOT}/references/shared-preludes.md。`
