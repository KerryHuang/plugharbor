# 實作錨點檔 `analysis/impl-anchors/{規格檔名}.yml`（每份規格一檔）

記錄「規格的每條規則在程式哪裡執行、最後一次跟程式比對是哪個 commit」。
`sample-verify` 每跑完一輪就寫回；下一輪讀它，只重驗錨點 commit 之後有變動的檔案。

**為什麼不寫進規格正文**：規格書技術中立（plugin `CLAUDE.md` `<law>`），不得出現類別、方法命名。
錨點是「完工後實際落在哪」的事實紀錄，不是對 Dev 的指示，所以放 `analysis/` 機器檔，規格不動。

> 做法借自 ECC `agents/spec-miner`（`enforced` 執行位置＋`Last verified` commit）。

## 格式

```yaml
_meta:
  spec: docs/<模組>/<功能>/<功能>_後端功能規格書.md   # 相對專案根目錄
  spec_blob: 9e1f0c3b...        # 寫回當下規格檔的 git blob hash（git hash-object <規格>），完整 40 碼
  verified_at: 2026-10-01      # 僅供人讀，增量判定不用它
  repos:                       # 每個被取樣的 repo 一行：路徑 → 該輪比對時的 HEAD commit（完整 hash）
    apps/backend-api: 3f9c2a1e...
  scope:                       # 本輪實際取樣的檔案（相對專案根目錄；目錄照 ls 實況寫，不猜 src/）
    - apps/backend-api/<實際目錄>/CreateReportHandler.cs
anchors:
  - rule: VR-003               # 規格內的規則編號（VR／BR／BL-ID）
    enforced: apps/backend-api/<實際目錄>/CreateReportHandler.cs:Handle   # 檔案:方法（或 檔案:行號）
    status: accurate           # accurate | inaccurate
uncertain:                     # 程式看不出意圖、不能斷言的區塊——不升格為 MISSING，不自己編規則
  - where: apps/backend-api/<實際目錄>/ReportCalculator.cs:88
    reason: 兩個分支結果相同，看不出是刻意還是殘留
deferred: []                   # 範圍內沒讀到的檔（下一輪優先讀）
```

- `rule` 只登記規格**已有**的編號；`MISSING_BUSINESS` 還沒有編號，不進 `anchors`，只出現在落差報告。
- 一條規則可對多個 `enforced`（前後端各擋一次），各寫一列。
- 檔案 ≤ 30KB；只放指標，不放程式摘要（同 `_context.yml` 的原則）。

## 增量判定（Step 0 用）

1. 檔名取規格檔名去掉 `.md`（如 `<功能>_後端功能規格書.yml`）——同一功能目錄的 BFS、FFS 各自一檔，互不覆蓋。檔案不存在 → 走全量。
2. 對 `_meta.repos` 每一行：`git -C <repo> cat-file -e <commit>` 失敗（被 rebase／淺 clone）→ 該 repo 走全量。
3. 變動檔 ＝ `git -C <repo> diff --name-only <commit> HEAD`（輸出相對 repo 根，先補上 `<repo>/` 前綴），取與 `_meta.scope` 的交集，再加上：
   - `deferred` 全部；
   - 規格改過的章節所含規則的 `enforced` 檔：`git hash-object <規格>` ≠ `spec_blob` 即規格有改，
     以 `git cat-file -p <spec_blob>` 取舊版、與現行檔逐行 diff，變動行往上找最近的 `## ` 標題即該章；
     `spec_blob` 缺欄或 `git cat-file -e` 失敗（舊格式、該版本從未進版控）→ 視為整份規格有改；
   - `_meta.scope` 中已被刪除或改名的檔（改名要追到新路徑）。
4. 交集為空且規格沒改 → 直接回報「自 <commit 前 7 碼> 以來無變動，錨點仍有效」，不派工。

## 寫回（Step 4 後）

- `_meta.repos` 更新為本輪各 repo 的 `git -C <repo> rev-parse HEAD`；`verified_at` 為今天。
- `spec_blob` 更新為**寫回當下**規格檔的 `git hash-object`。本輪若依落差報告修了規格，要在**改完規格之後**
  才算 hash，並與規格同一個 commit 提交——否則下一輪會把自己剛修的內容當成「規格有改」而重驗。

> 為什麼不用日期或 commit：`git log --since=<verified_at>` 以日為單位，規格與錨點在同一天 commit
> 就永遠被判「之後有改」；記規格的 commit hash 則有自我參照問題——錨點檔與修好的規格同一個 commit，
> 寫錨點時那個 commit 還不存在。blob hash 只看內容，兩個問題都沒有。
- 本輪有重驗的規則：覆寫其 `anchors` 列；沒重驗的保留原列。
- 寫完必驗解析：`python3 -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))" <檔>`，回報「解析通過」。
