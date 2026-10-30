# 瀏覽器 profile lock 協定（分平台）

> ⚠ **本檔描述的是自生／附掛共用 Chrome 模式。MCP 註冊標準為 `--isolated`
> （[browser-setup.md](browser-setup.md)），下述 lock／PID／9222 判準全部不適用。**
> 保留供尚未切換註冊的機器診斷；`browser-doctor` 報 FAIL 時先改註冊，不要照本檔協調 lock。

派 `browser-surveyor`（或任何用 `chrome-devtools` MCP 的 agent）前後要做的事。
本檔是全 plugin 的唯一權威，各 skill 引用不複製。

<law>
⚠️ **先確認兩件事，再決定要讀哪幾節**：

1. **你在哪個平台**——macOS 與 Windows 的鎖機制**完全不同**（見 §一）。
   把 mac 的診斷指令搬到 Windows 不是「查不到」，是**查錯東西**。
2. **你在哪個模式**——自生 vs 附掛（見 §二）。同一條指令在兩種模式下結論相反。

| 你的情況 | 要讀 |
|---|---|
| 附掛模式（Windows 已是、mac 使用者已裁決改） | §二、§三、§五 |
| 自生模式 | 全部 |
</law>

---

## 一、鎖機制：mac 與 Windows 完全不同

實測：macOS、Windows 各一輪。

| 面向 | **macOS** | **Windows** |
|---|---|---|
| 鎖形式 | `SingletonLock` **symlink** | `lockfile` **0-byte regular file** |
| 含 PID | ✅ 內容為 `<hostname>-<PID>` | ❌ **完全空白** |
| 另有 | `SingletonSocket`／`SingletonCookie` | 三者皆無 |
| 套件怎麼判 | 比對 Chrome stderr 的 `Failed to create a ProcessSingleton…` | **`existsSync(userDataDir/lockfile)`**——純存在性，不驗 PID、不驗是否真被佔用 |
| **程序死後** | **symlink 殘留** | **OS 自動刪**（`DELETE_ON_CLOSE`） |
| 診斷法 | `ls -la SingletonLock` 讀 PID | `Get-CimInstance Win32_Process` 查 CommandLine |
| Chrome 層撞衝突 | launch 失敗 | **exit 0、靜默交棒後自退，第二個除錯埠根本不開** |
| 錯誤訊息字面 | 相同（同一份打包 JS） | 相同，但**觸發路徑不同** |
| profile 路徑 | `~/.cache/chrome-devtools-mcp/chrome-profile` | `C:\Users\<u>\.cache\…`（用 `os.homedir()`，**非 AppData**） |

套件原始碼的平台分支（打包進去的 puppeteer）：

```js
if (logs.includes('Failed to create a ProcessSingleton for your profile directory') ||
    (process.platform === 'win32' && existsSync(join(launchArgs.userDataDir, 'lockfile')))) {
    throw new Error(`The browser is already running for ${launchArgs.userDataDir}. …`);
}
```

<law>
**「Windows 的鎖比較髒」是錯的直覺，方向相反。**

Windows 以 `DELETE_ON_CLOSE` 開 `lockfile`，程序死掉 OS 釋放 handle 即刪——
強殺 12 個 chrome.exe 後 lockfile 立即消失（實測）。

**mac 的 `SingletonLock` 是普通 fs 物件，程序沒了會留在磁碟上**——
那正是「閒置 26 小時仍佔著 profile」的機制成因。

唯一未測情境：整機當機／斷電，Windows 的 OS 沒機會清 handle。標為理論風險。
</law>

### 各平台的正確診斷

**macOS**（自生模式才需要）：

```bash
ls -la ~/.cache/chrome-devtools-mcp/chrome-profile/SingletonLock   # -> ...-<PID>
ps -o pid,ppid,lstart,command= -p <PID> | head -c 300
ps -o command= -p <該 PID 的 PPID>                                  # 往上追到哪個 MCP server
```

三態：**不存在**＝可用｜**存在且 PID 活著**＝被佔用｜**存在但 PID 已死**＝stale（手動刪 lock 檔）。

**Windows**——**查程序命令列，不是查檔案**（`lockfile` 不含 PID，查它得不到任何資訊）：

```powershell
Get-CimInstance Win32_Process -Filter "Name='chrome.exe'" |
  Where-Object { $_.CommandLine -like '*--user-data-dir*' } |
  Select-Object ProcessId, ParentProcessId, CommandLine
```

browser process ＝**父程序不是 chrome 的那個**；子程序一律帶 `--type=`。

> Git Bash 陷阱：`taskkill //F //IM`（**雙斜線**，單斜線會被 MSYS 轉成路徑）；
> `iconv` 不存在，Chrome 的 cp950 中文訊息要用 `powershell Get-Content -Encoding Default` 解。

---

## 二、兩種模式：判準隨模式而變，結論相反

| 模式 | 怎麼認 | 連不上代表 |
|---|---|---|
| **自生** | MCP 註冊**無** `--browserUrl`；Chrome 帶 `--remote-debugging-pipe` | profile 被佔——**叫使用者開 Chrome 是白忙** |
| **附掛** | MCP 註冊帶 `--browserUrl`；Chrome 帶 `--remote-debugging-port` | 常駐 Chrome 沒開／掛了——**才需要請使用者開** |

<law>
**先確定模式，再選判準。用錯的那條會給你一個有自信的錯誤答案。**

| 要判什麼 | **自生模式** | **附掛模式** |
|---|---|---|
| 用什麼判 | 平台對應的鎖診斷（§一） | **`curl -s -m 2 http://127.0.0.1:9222/json/version`** |
| `curl 9222` | **無意義**——走 pipe 不走 port，那個埠永遠沒回應 | **唯一有效判準** |
| 鎖檔 | 唯一有效判準 | 幾乎無意義——Chrome 用人指定的 `--user-data-dir`，MCP 只連 port |
| 處置 | 診斷持有者 → 回報 PID 由人決定 | 請使用者開常駐 Chrome |
</law>

> 這條是踩出來的：mac 第一天用 `curl 9222` 判斷「有沒有 Chrome」，得到「沒有」——
> 實際上 Chrome 好好活著、走的是 pipe。後來把「curl 判不出來」寫成**通則**，
> 而 attach 一上線它又反過來成為唯一判準。
>
> **沒有標明適用範圍的判準，比沒有判準更危險**——它會讓人有自信地走錯方向。

---

## 三、附掛模式：多 session 真的可以並行

```bash
# macOS
nohup "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --remote-debugging-port=9222 --user-data-dir="$HOME/.cache/claude-shared-chrome" >/dev/null 2>&1 &

# Windows（Git Bash）
(nohup "/c/Program Files/Google/Chrome/Application/chrome.exe" \
  --remote-debugging-port=9222 --user-data-dir="C:\Users\<u>\.cache\claude-shared-chrome" about:blank &)

curl -s -m 3 http://127.0.0.1:9222/json/version    # 通了才算成功
```

```jsonc
// ~/.claude.json 的 chrome-devtools 條目（Codex 的 config.toml 也要同步）
{"command": "npx",
 "args": ["-y", "chrome-devtools-mcp@latest",
          "--browserUrl", "http://127.0.0.1:9222",
          "--viewport", "1680x1000"]}
```

改完**要重啟 session**（MCP 設定在啟動時讀取）。
`--viewport` 設初始尺寸，**agent 就不需要 `resize_page`**（那會改整個 window，平行時干擾其他 agent）。

### 並行實證

| 情境 | 自生模式 | 附掛模式 |
|---|:--:|:--:|
| 同一 session 內多 agent | ✅（mac 實測） | ✅ |
| **跨 session** | ❌ 撞 profile lock | ✅ **（Windows 實測）** |

Windows 實測：兩個獨立 MCP client 各自完成握手後同時 `new_page`，**兩個都成功，
各自維持獨立的 `[selected]` 指標（互不搶），且都看得到對方的分頁**。
CDP 本來就是多 client 協定——這是附掛模式解掉跨 session 問題的根本原因。

<law>
平行時**每次工具呼叫都要明確帶自己的 `pageId`**——mac 自生模式實測中
「當前選中分頁」是全域的會被切走。附掛模式下 Windows 實測各 client 指標獨立，
**但不要依賴這個差異**：帶 pageId 在兩種模式、兩個平台都正確。

平行時**禁用 `resize_page`**（改整個 window 尺寸）。有尺寸需求用 `--viewport`。
</law>

### 為什麼要改附掛：兩個平台的理由不同

<law>
**mac 是「必須」**：`SingletonLock` symlink 程序死後殘留，鎖持有期＝整個 session 生命週期，
跨 session 死鎖無解，只能靠人協調或 kill。

**Windows 是「較優但非必須」**：`lockfile` 會自清，自生模式的衝突代表
「這一刻真的有另一個 Chrome 在跑」，沒有殭屍鎖。
附掛的價值在**多 session 真能並行** ＋ Chrome 由人開由人關、狀態可預測。

寫文件時要講清楚理由不同，否則 Windows 的人會以為自己也有 mac 那種死鎖問題。
</law>

---

## 四、自生模式下的補救（附掛模式可略過本節）

### 派工前：確認鎖是自己的或不存在

依 §一的平台診斷。被別的 session 佔用時：

<law>
**不要自行 `kill`**——那可能是進行中的工作。回報 PID／啟動時間／目前頁面，
列選項讓**人**決定：① 請持有的 session 釋放 ② 由使用者 kill ③ 本次改走非瀏覽器途徑。

**口頭交接不等於鎖釋放。** 對方說「我用完了」只代表它不再操作，
**不代表 Chrome 關了**——mac 上鎖的持有期是整個 session。一律以實際診斷為準。
</law>

### 派工後：這一輪結束就釋放

agent 回報帶 `browser_pid`。本輪瀏覽器任務結束、且確定無後續派工時 `kill <browser_pid>`。

<law>
**「結束」指的是「這一輪瀏覽器任務結束」，不是「session 結束」。**

> 實測：一次平行測試完成後，Chrome 留了四十多分鐘才被下一個撞到的 session 發現；
> 另一次同樣形狀的殘留鎖了 26 小時。

**還要續派下一棒時不要 kill**——重開要重登入、重導航。
判準是「接下來還會不會用瀏覽器」，不是「這一棒做完了沒」。
</law>

---

## 五、Chrome 層的靜默行為（兩平台都要知道）

**Windows 實測**：同 profile 再開一個 Chrome、指定不同 port（9333）——

```
exit code = 0
訊息：正於現有瀏覽器工作階段中開啟。
curl 9333 -> exit=7 ；netstat | grep 9333 -> 無
```

**exit 0、不報錯、靜默交棒給既有實例後自退，第二個除錯埠根本不會開。**

<law>
「開 Chrome 的指令成功了」**不代表除錯埠起來了**——一律用 `curl` 驗，不要看 exit code。
錯誤是 puppeteer 等不到 CDP endpoint 才拋的，Chrome 自己完全不給。
</law>

> 另註：常駐 Chrome 只有 `about:blank` 時 `list_pages` 回空輸出，**不是故障**。
