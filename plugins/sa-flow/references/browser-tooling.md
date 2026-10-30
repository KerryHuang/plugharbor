# 瀏覽器工具：定位、隔離模型與同 session 規則

## 誰用什麼

| 執行者 | 工具 | 理由 |
|---|---|---|
| 5 支瀏覽器 agent（browser-surveyor／manual-explorer／qa-planner／qa-fixture／qa-runner-ui） | `chrome-devtools`，固定 | Codex 也要能跑；`claude-in-chrome` 需 Claude Code `/login` 訂閱帳號，Codex 沒有 |
| 主 session 人機互動（`live-drive` 的 investigate／e2e／explore） | Claude Code 上 `claude-in-chrome` 可當捷徑（沿用使用者已登入的 Chrome、每 session 一個 tab group、跨 session 真隔離）；Codex 或沒裝擴充功能時退回 `chrome-devtools` | 兩者能力邊界不同：`claude-in-chrome` 截圖路徑由工具決定、無 fullPage、無精確尺寸 |
| 都沒有 | 協助使用者安裝（標準見 [browser-setup.md](browser-setup.md)），不要跳過瀏覽器步驟硬做 | |

## 隔離模型：每個 session 一個拋棄式 Chrome

MCP 註冊一律 `chrome-devtools-mcp --isolated`（[browser-setup.md](browser-setup.md)）。
每個 session 開自己的 Chrome＋暫存 profile（`puppeteer_dev_chrome_profile-XXXXXX`）、獨立 cookie jar、獨立視窗，session 結束自動消失。

| 舊症狀 | 為何消失 |
|---|---|
| profile lock／連不上 | 目錄名隨機，沒有人會撞同一個 |
| 登入互踢 | cookie jar 隨 profile 各自獨立 |
| 分頁被別人動到、pageId 重編 | 各 session 只看得到自己的 Chrome |
| 截圖尺寸被弄壞 | 各 session 自己的視窗；尺寸改由 per-page `emulate` 決定 |

兩平台＋Codex 實測：正常結束 1 秒內 Chrome 退出、profile 清掉；硬砍 Chrome 仍退出，profile 殘留 16–17 MB 但不構成鎖（`browser-doctor` 起手清）。mac 硬砍後 `SingletonLock` 無殘留。

> 為什麼不再附掛共用 9222：那把 cookie jar 與分頁也共用起來，09-09～09-12 多個 session 各撞過「測完沒關、lock 白鎖」，寫了冗長的協調規範碰撞照樣發生。靠紀律解不了的問題要改靠機制。

## 同 session 多 agent：四條

同一 session 的所有 agent 共用同一個 MCP＝同一個 Chrome，所以：

1. **每次呼叫帶自己的 `pageId`**（chrome-devtools-mcp ≥1.8.0 工具層強制）。看到「Page ids have changed」就 `list_pages` 用 `isolatedContext` 標記認回自己的頁。
2. **`new_page` 帶派工給的 `isolatedContext`**（契約欄位 `isolated_context`，同 session 各 agent 不同）。獨立 cookie jar，同帳號各自登入互不踢；它不擋分頁互見，第 1 條照留。
3. **開頁後第一件事 `emulate(pageId, viewport: "1680x1000x2")`**，無條件。CDP device-metrics emulation，不動視窗、不受螢幕夾住、撐得過導頁，截圖 3360×2000。`resize_page` 已從 agent 工具移除。
4. **落點**：開頁前 `list_pages` 對同 `isolatedContext` 的殘留頁不接手；收尾 `close_page` 後 `list_pages` 確認；回傳必含 `viewport：emulate … → 實讀 [w, h, dpr]；分頁已關：true/false`，證據檔（有 `_meta` 的）記 `viewport`／`page_closed`。law 沒有可驗證的落點就分不出「舊定義」和「沒遵守」——曾有舊 session 派的舊版定義 surveyor 全沒 emulate，靠這兩個欄位才回溯出真因。

`--viewport` 旗標只對第一個分頁做一次 OS 視窗 resize，isolatedContext 新視窗吃不到（Windows 1667×907、mac 1414×780、mac headed 高度被螢幕夾到 780）。註冊保留它無害，尺寸的權威是 `emulate`。

驗證：同 session 兩個 agent 同帳號各自 isolatedContext 登入、同時建單，零串頁、零重編、互不踢。

## 座標與 DPR

`getBoundingClientRect()` 給 CSS px；emulate `x2` 後截圖是 CSS px ×2（1680×1000 → 3360×2000）。寫進 annotate spec 前先乘好，詳見 [annotate-spec.md](annotate-spec.md)。

## `take_screenshot` 的 `filePath` 白名單

1.9.0 起只准存 MCP client 協商的 workspace roots 內；Claude Code／Codex 會協商，所以一律先落 workspace 的 `.tmp/…`，交付路徑由主 session 複製。裸 JSON-RPC client 沒協商 roots 只能存 temp 目錄。

## 收尾

agent 只關自己開的分頁。主 session 若為測試手動起過 Chrome，**在回報完成的同一輪關掉並驗證**（`curl -s -m 2 http://127.0.0.1:9222/json/version` 無回應、無 `puppeteer_dev_chrome_profile`／`claude-shared-chrome` 行程）。

## 舊模式

自生／附掛共用模式的 lock 診斷見 [browser-lock-protocol.md](browser-lock-protocol.md)（備查，`--isolated` 下不適用）。
