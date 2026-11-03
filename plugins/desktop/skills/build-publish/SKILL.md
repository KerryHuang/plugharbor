---
name: build-publish
description: 桌面應用的建置與發佈通用流程——建置驗證、版號來源、目標平台矩陣、簽章與公證、安裝包（msi／dmg／AppImage 等）、輸出位置與桌面捷徑；附 Avalonia／dotnet publish 附錄。Use when 使用者說「建置」「build」「編譯」「發佈」「publish」「打包」「安裝包」「簽章」「產生執行檔」「single file」「self-contained」「release build」或要建立 Windows／macOS／Linux 可執行檔。
---

# 桌面應用建置與發佈

流程：建置驗證 → 決定版號 → 決定目標平台 → 產出 → 打包安裝包 → 簽章 → 驗收。

## 0. 偵測技術棧與附錄

先看專案的 `*.csproj`、`package.json`（electron-builder／tauri）、`Cargo.toml`，對照下表載入附錄，並在回報第一行寫「附錄：<檔名>」。

| 偵測到 | 附錄 |
|---|---|
| `*.csproj` 引用 `Avalonia` | `${CLAUDE_PLUGIN_ROOT}/references/stacks/avalonia.md` |
| `UseWPF`、WinUI、Electron、Tauri | 目前無附錄，走下方退路 |

沒有對應附錄：照本 skill 的通用方法，加上專案既有的建置腳本與 CI 設定（先找 2–3 個同類檔當樣板；有裝 workspace 就照 `workspace:convention-first`（可選））。做完問使用者要不要把這次的寫法整理成新附錄 `references/stacks/<stack>.md`，回報寫「附錄：無（照既有程式）」。

## 1. 建置驗證

先跑專案的標準建置與測試指令（README、CI、`Makefile`、`package.json` scripts 找得到的那支），確認能編譯、測試過再發佈。失敗時分析錯誤並提出修正，不帶著失敗發佈。

## 2. 版號

- 版號只有一個來源（專案檔的 version 欄位或單一 `VERSION` 檔），安裝包檔名、About 畫面、更新檢查都從它讀。
- 遵循 semver；發佈前確認版號已更新，且與 git tag、CHANGELOG 一致。
- 不手動改多處再靠記憶對齊；發現不一致就修成單一來源。

## 3. 目標平台

使用者指定就用指定的；未指定時依目前作業系統與實際使用者環境挑選，不一次全發。

| 平台 | 常見架構 |
|---|---|
| Windows | x64、arm64 |
| macOS | arm64（Apple Silicon）、x64（Intel） |
| Linux | x64、arm64 |

- 交叉編譯受限時（例如 macOS 簽章需在 macOS 上做），把該平台交給對應的 CI runner，不硬在本機湊。
- 每個目標平台各自在乾淨環境驗證能啟動，不只驗建置成功。

## 4. 產出型態

- 自含式（self-contained）：內含執行環境，目標機免安裝；體積大但部署簡單。
- 依賴框架（framework-dependent）：體積小，要求目標機已有執行環境；僅在可控環境使用。
- 單一檔案：方便散布，但首次啟動較慢，原生函式庫的處理要確認。
- 修剪（trimming）會移除反射用到的程式碼，啟用後必須實跑全功能驗證。

## 5. 安裝包

| 平台 | 常見格式 |
|---|---|
| Windows | `.msi`／`.exe` 安裝程式（Inno Setup、WiX、MSIX）、免安裝 zip |
| macOS | `.app` bundle → `.dmg` 映像檔 |
| Linux | AppImage、`.deb`、`.rpm`、tar.gz |

macOS `.app` 是含 `Contents/MacOS/`、`Contents/Info.plist`、`Contents/Resources/` 的目錄；`.dmg` 可用內建 `hdiutil` 從 `.app` 產生。專案已有打包腳本就用它，沒有再補。

## 6. 簽章與公證

- Windows：Authenticode 簽章；未簽章會觸發 SmartScreen 警告。
- macOS：Developer ID 簽章＋公證（notarization）＋staple，否則 Gatekeeper 會擋。
- 憑證與密碼只放 CI secret 或系統鑰匙圈，不進 repo、不進命令列歷史。
- 沒有憑證時照常產出未簽章版本，並在回報明講「未簽章」與使用者首次開啟要做的動作。

## 7. 輸出位置與驗收

- 輸出集中到單一目錄（專案慣例優先），檔名含應用名、版號、平台與架構，例如 `<App>-<version>-<platform>-<arch>.<ext>`。
- 回報：產出檔清單與大小、版號、平台、簽章狀態。
- 驗收各自宣稱：建置通過、測試通過、產出檔存在、本機可啟動、已簽章、已發佈；沒做到的標「未驗證」。

## 8. 桌面捷徑（可選）

- Windows：`.lnk` 指向執行檔。
- Linux：`~/.local/share/applications/<app>.desktop`，含 `Exec=`、`Icon=`。
- macOS：`.app` 拖入 `/Applications` 或建立 alias。
