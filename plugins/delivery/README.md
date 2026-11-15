# delivery

交付文件：操作手冊（Word／PDF／簡報）與示範影片。
自 `lifecycle` 3.0.0 拆出（1.0.0），命名空間一律 `delivery:`。

## 定位

`[workflow]` 專案層 plugin，用 `setup/install-project.sh <專案根> delivery` 依專案安裝；可單獨使用，不需要 lifecycle。

## 安裝

```bash
claude plugin marketplace add https://github.com/KerryHuang/plugharbor.git
cd <專案> && claude plugin install delivery@plugharbor --scope local
```

## 設定

專案根 `.plugharbor/lifecycle.yml`，鍵與預設值見 `references/config.md`（手冊封面品牌用 `manual-brand`）。

## 可選依賴

`browser-docs`（實機操作與截圖標註）、`toolkit`、`superpowers`、`lifecycle`、`tickets` 都是可選，沒裝時照 `references/shared-preludes.md`「可選依賴」降級。
截圖標註與換假資料工具（`annotate.py`、`anonymize-page.js` 等）本 plugin 為 canonical，browser-docs 帶副本（validate 的共用副本檢查驗內容相同）。

## Skills（2）

| Skill | 用途 |
|-------|------|
| `operation-manual` | 產出交付客戶的操作手冊與教育訓練簡報：實機探索 → 標註截圖 → 撰寫 → 審查 → 出 PDF／PPTX，並把過程中發現的規格落差整理成待開票清單（手動） |
| `demo-video` | 把旁白加操作步驟的腳本錄成有配音、字幕的操作示範影片（MP4＋SRT）：寫稿 → 審稿 → 配音 → 依語音長度錄操作 → 字幕 → 合成 → 驗證，最後由使用者試聽；預設語音 Edge TTS 非正式授權，對外發布前要先確認 |

## Agents（3）

| Agent | 用途 |
|-------|------|
| `manual-explorer` | 操作手冊探索：用瀏覽器逐畫面記錄可操作元素／預設值／驗證訊息到 inventory.yml 並截乾淨圖；第二模式回頭加紅框重拍 |
| `manual-reviewer` | 操作手冊交付前七項審查（圖文比、內部資訊、個資遮罩、圖片完整、與 inventory 一致、模式純度、整批一致），並整理規格落差 |
| `manual-writer` | 操作手冊撰寫：讀 inventory.yml 與截圖清單，依範本產手冊 markdown 與 Marp 簡報，列出需加紅框的截圖 |
