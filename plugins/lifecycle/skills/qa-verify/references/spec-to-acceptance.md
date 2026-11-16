# 設計文件「驗收」→ 案例檔

輸入是 `lifecycle:spec`（或 `superpowers:brainstorming`）產的設計文件（`<spec.dir>/*-design.md`）時，先轉成案例檔，再走 Step 1 的案例檔模式。轉檔交腳本，主 session 不手轉、不開瀏覽器、不派 agent。

## 轉檔

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/qa-verify/scripts/spec_to_cases.py <設計文件> <ws>/.tmp/qa/<feature>.md
```

- `<feature>` 為設計文件檔名去掉 `.md`；不同功能互不覆蓋。stdout 印案例數。
- 認 `## 驗收`（案例 `###`、欄位 `####`），也認舊範本 `### 2.3`（案例 `####`、欄位 `#####`）。原樣轉：標題與清單項照抄，不改寫、不補字。
- **落檔前**先 `git check-ignore -q .tmp/`；沒被忽略就提醒一次「`.tmp/` 沒在 .gitignore，轉出的案例檔會出現在 git status」並建議加進去（不自己改 .gitignore）。
- 轉完以該路徑進 Step 1 的 `validate.py acceptance`。

## exit 4：缺欄或格式不符

stderr 逐條列「案例 id：缺什麼」（缺步驟或預期、id 不是 ASCII、預期仍是 `{…}` 佔位符、找不到驗收一節），腳本不寫輸出檔。把清單交使用者補設計文件（`lifecycle:spec --change`），不猜、不替補。

## 驗收不是案例格式

舊文件或其他來源的設計文件（例：只有 `- [ ] AC-01：給定…當…則…` 的清單，或根本沒有驗收一節）腳本會 exit 4，改走擬稿：

- 有 Given／When／Then 句子 → 擬成案例草稿（給定 → 前置條件，當 → 步驟，則 → 預期），落同一路徑，**先給使用者確認**再跑。
- 完全沒有驗收內容 → 從內文擬草稿並標「擬稿、未經確認」，同樣先確認；使用者不確認就停。

## 範例

設計文件裡：

```markdown
### AC-02 備註超過 200 字被擋 [ui]
#### 步驟
1. 開啟 SO-001，備註填 201 個字，按「儲存」
#### 預期
- 顯示「備註不可超過 200 字」
```

轉成：

```markdown
## AC-02 備註超過 200 字被擋 [ui]
### 步驟
1. 開啟 SO-001，備註填 201 個字，按「儲存」
### 預期
- 顯示「備註不可超過 200 字」
```
