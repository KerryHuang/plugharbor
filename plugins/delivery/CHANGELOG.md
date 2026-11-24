# Changelog

格式：每次改動 `skills/`、`agents/`、`references/`、`templates/` 時，於最上方新增版本條目並同步 bump 版號（規則見 `.claude/rules/version-consistency.md`）。

## [1.3.4] - 2026-11-24

起因：同 toolkit 0.38.0（claude-api 派工路由）。
- fix：mux.py 副本同步 toolkit 0.38.0：claude-api pane 以 claude 開並清 key。

## [1.3.3] - 2026-11-23

起因：retrospective 20261123-feedback-plugin-handoff R2。
- fix：同步 toolkit 0.37.0 的 `mux.py` 副本（spawn 自動帶 cwd 的 `.mcp.json` 引用的環境變數給 worker）。

## [1.3.2] - 2026-11-23

起因：plugharbor#70。
- fix：同步 toolkit 0.35.0 的 `mux.py`、`app_layout.py` 副本（本機沒開 Herdr.app 時改擺進遠端機器的視窗；pi turn 0 誤報 blocked；Git Bash 的 `/` 開頭訊息被改寫成路徑）。

## [1.3.1] - 2026-11-23

起因：issue #67——CI 的 `skills/demo-video/scripts/env.test.mjs`「killSync：行程 exit 時同步收掉 server 並刪鎖檔（I1）」間歇失敗（`alive` 為 true）。CPU 滿載的 runner 上實測 150 次失敗 8 次：`killSync` 只同步送出 SIGTERM，行程何時消失由 OS 排程決定，測試卻在父行程結束後立刻檢查。
- test(demo-video)：`skills/demo-video/scripts/env.test.mjs` 該案例改為輪詢到 server 消失（上限 3 秒）才斷言；被測的 `lib/env.mjs` 行為不變。

## [1.3.0] - 2026-11-19

起因：使用者 2026-11-19 回報 superpowers 腦力激盪、寫計畫時向使用者丟一長串設計題，全都不經 domain 顧問；顧問桌只在 `spec` 蒐證後開，介入太晚，使用者要求設計題先過顧問，顧問決定不了的才問。
- feat：同步 lifecycle 4.3.0 的副本：`references/consultant-desk.md`、`shared-preludes.md`、`config.md`，內容是顧問的設計提問分流（`mode: triage`）與新設定鍵 `advisor.escalate`。

## [1.2.2] - 2026-11-18

- fix(skills): `operation-manual` 的 MCP 註冊提示改為 `--isolated --redact-network-headers`，和 browser-docs 0.3.6 的標準註冊一致。起因：2026-11-04 公司 workspace 跑 qa-sweep 時，`get_network_request` 把真的 `Authorization: Bearer` 原樣印進 agent 輸出；2026-11-18 用 chrome-devtools-mcp 1.13.0 實測，加這個旗標後 request／response headers 改由白名單遮罩，回應內文不遮。

## [1.2.1] - 2026-11-18

起因：Windows 桌機的 Herdr.app 終端跑 `mux.py env` 直接丟 `AttributeError: module 'socket' has no attribute 'AF_UNIX'`（`core_running()`，2026-11-18 重現），Windows 上所有經 mux.py 的派工都不能用。另外 `spawn` 用 `env -u …` 當 argv 前綴（Windows 沒有 `env`），`app_layout.py` import `fcntl`（Windows 沒有）。
- fix：`scripts/mux.py`、`scripts/app_layout.py` 同步 toolkit 0.28.2 的 Windows 支援（副本）。

## [1.2.0] - 2026-11-17

起因：使用者 2026-11-17 轉用 Herdr.app，派工流程在 app 內無法開 worker。

- 同上：`references/advisor-discussion.md`、`consultant-desk.md`、`shared-preludes.md`、`scripts/advisor_last_reply.py` 從 lifecycle 4.2.0 的同名檔依對照表同步（只差 agent 名稱）；新增 `scripts/mux.py`、`scripts/app_layout.py`、`scripts/herdr_layout.py`（版面腳本，與 toolkit `agent-dispatch` 正本位元組相同；顧問 pane 排進主 session 旁；版面不依賴 toolkit，hc 下讀顧問 transcript 需 toolkit 的 SessionStart hook，沒有就改走 subagent 模式）。
- 同上（最終審查）：同步 lifecycle 4.2.0 的 `advisor-discussion.md` 修正（`session` 為 null 最多重試 3 次，缺 hook 改走 subagent 模式）與 `mux.py`、`app_layout.py` 副本更新。
- fix（實機驗收）：`app_layout.py` 副本同步（見 toolkit 0.25.0：spawn 後立刻放置會回 `no running terminal`，改為重試）。
- fix（實機驗收）：`mux.py` 副本同步（見 toolkit 0.25.0：hc send exit 9 改回 blocked）。

## [1.1.0] - 2026-11-16

起因：demo-video 第一次實戰（兩支影片）的摩擦集中在起站與重置、選擇器試錯、操作超時三處。設計見 `docs/superpowers/specs/2026-11-16-demo-video-optimization-design.md`。

- 錄影環境配方 `video/env.mjs`：引擎自動 build、reset、自選空埠、驗證聽埠的程序是自己起的才算就緒、只關自己的程序（POSIX 用 process group）；新增 `env-check` 指令；預設目錄由 `.tmp/demo-video/` 改為進版控的 `video/`；`ensure-tools.sh` 檢查 gitignore；有配方時先拿鎖再配音，同一支影片同時 build 第二個直接被拒；引擎崩潰或收到 SIGHUP 也會收掉 detached 的 server 與鎖檔。
- 新增 `dry-run`（不配音不錄影，印每段語音估計與操作秒數；失敗印可互動元素清單）與配音快取（`video/.tts-cache/`；`--base` 模式在 `video/<名稱>/.tts-cache/`）。
- 操作員新增 `a.upload`、`a.select`、`a.as`；每段可寫 `expect`；contact sheet 改抓操作完成那一刻；`base` 改為選填。
- 回報分開寫成片長度與製作時間；配音來源與授權寫進 MP4 metadata，未確認授權時提醒對外發布前要確認。
- 範例 `examples/leave-request` 的 `run.sh` 改為 `examples/env.mjs`＋`serve.mjs`；SKILL 與 references 同步更新。

## [1.0.1] - 2026-11-16

起因：lifecycle 4.1.0 把設計文件改成新章節格式（設計見 `docs/superpowers/specs/2026-11-15-lifecycle-split-design.md`，第三批），本 plugin 的共用 references 副本跟著改讀新章節。

**改動**

- `references/` 共用副本（config、shared-preludes、shared-preludes-details、analysis-rigor、consultant-desk、legacy-parity）改讀新章節，舊章節以「（舊範本 §n）」括號別名保留。

## [1.0.0] - 2026-11-15

起因：lifecycle 22 個 skill 兩週內實際只用到 7 個；只想要操作手冊或示範影片的人得裝整包。設計見 `docs/superpowers/specs/2026-11-15-lifecycle-split-design.md`，第二批「拆 plugin」，delivery 是第三個拆出來的（tickets、discovery 之後）。

- 自 lifecycle 3.0.0 搬入：skills `operation-manual`、`demo-video`；agents `manual-explorer`、`manual-reviewer`、`manual-writer`；references `annotate-spec.md`、`anonymize-before-capture.md`；scripts `annotate.py`、`anonymize-page.js`、`build-deck.sh`、`build-manual-docx.sh`、`build-manual-pdf.py`、`check-deck-overflow.py`、`check-inventory-rects.py`、`ensure-tools.sh`、`make-docx-reference.py`、`manual_brand.py`、`manual-print.css`、`manual-reference.docx`、`prep-docx-cover.py`、`text-image-ratio.py` 與 `test_manual_brand.py`、`test_check_inventory_rects.py`。叫用名由 `lifecycle:<名稱>` 改為 `delivery:<名稱>`。
- 能單獨安裝，所以帶一份共用 references／scripts 副本（`harness-terms`、`config`、`shared-preludes*`、`consultant-desk` 等核心包）；canonical 在 lifecycle，漂移由 validate 的共用副本檢查擋。
- `annotate-spec.md`、`anonymize-before-capture.md`、`annotate.py`、`anonymize-page.js` 的 canonical 改為 delivery，browser-docs 的副本照舊。
