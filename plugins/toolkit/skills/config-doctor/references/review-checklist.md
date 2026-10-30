# 內容品質自審清單（reviewer agents 不在時的降級方案）

user 層有 reviewer agents 時**優先並行派發**（claudemd-reviewer / rule-reviewer / skill-reviewer / subagent-reviewer / hook-reviewer）；本清單供 reviewer 不在時主線自審，或作為派發 prompt 的維度提示。

## 各元件審查面向

### CLAUDE.md（user 與 project 各審一次）
- 指令具體可執行，無「write clean code」式空話
- token 效率：每 session 常駐，procedure 應抽成 skill、細節應下放 rules 只留索引
- 與 rules 的分層：CLAUDE.md 留一句指向 vs 逐字複製（逐字複製＝雙載）
- 事實時效：列舉的子模組／路徑／檔案是否仍存在、有無漏列新增項

### rules
- frontmatter `paths` 範圍：過寬會外溢誤觸（如 `**/docs/**` 會命中 apps 內部 docs 與 plugin 鏡像）；無 paths＝全域載入，確認是否刻意
- 與 CLAUDE.md、其他 rule 的重複；跨層（user vs project）同名 rule 的分層引用是否漂移
- 指涉的路徑、工具、指令是否仍存在

### skills
- description：「做什麼＋Use when 觸發詞」，不枚舉內部步驟；語言遵循使用者慣例
- 行數：官方建議 <500，細節拆 references/（漸進式揭露）；內部相對連結存在
- frontmatter：name＝目錄名、無非標準欄位；流程用到的工具要列入 allowed-tools
- 跨 skill：觸發詞撞名、共用資料（如清單表）多處重複需收斂

### agents（subagents）
- 單一職責、tools 最小化、model 與任務複雜度相稱（注意：model 覆寫是絕對值非下限，session 用更高階模型時覆寫反成降級）
- description 足以讓主線正確派發；輸出格式有明確標度（如嚴重度定義），否則各次回報不一致

### hooks
- 契約：通知類 hook 永遠 exit 0；`set -e` 要配結尾顯式 exit 0 與逐命令 `|| true`
- 跨平台：以能力偵測（`command -v`）而非 OSTYPE 分派；音效／通知在**目標平台實測**過才算通過
- 效能：同步外部程序（PowerShell 等）要背景化；timeout 與實際耗時相稱

### settings / permissions
- allow 全放行（如 `Bash(*)`）時，deny 清單要覆蓋危險變體（`rm -fr`、`format`…——deny 是字面前綴比對）
- ask 優先序高於 allow，可作破壞性操作的守門
- 與 rules 的矛盾（rule 說只用工具 A，permissions 卻 allow 工具 B）
- `effortLevel`／`model` 與使用者工作型態相稱
- enabledPlugins vs 實際安裝對齊；plugin 安裝版 vs 源碼版落差

## 常見誤報（定案前先過這關）

| 掃描器說 | 可能真相 |
|----------|----------|
| skill 目錄無 SKILL.md | 本地 plugin 等刻意形態（查記憶／問使用者） |
| SKILL.md 斷鏈 | 文中「範例連結」文字，非真引用 |
| rule 無 paths | 刻意全域載入（如 DB 工具選擇規則） |
| 命名不合 gerund 房規 | 使用者已豁免的 local convention |
| 空的 agents/ 目錄 | 正常狀態，非缺陷 |
