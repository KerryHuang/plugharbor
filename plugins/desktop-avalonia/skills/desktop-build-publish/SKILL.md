---
name: desktop-build-publish
description: Avalonia 桌面應用的建置與發佈——dotnet build 驗證、跨平台單一執行檔發佈（win/osx/linux RID）、macOS .app/.dmg 打包與輸出位置。Use when 使用者說「建置」「build」「編譯」「發佈」「publish」「打包」「產生執行檔」「single file」「self-contained」或要建立 Windows/macOS/Linux 可執行檔。
---

# 桌面應用建置與發佈

Avalonia 桌面應用的建置驗證與跨平台單一執行檔發佈流程。

## 建置

執行 `dotnet build` 建置整個解決方案，作為能否編譯的快速驗證：

```bash
dotnet build
```

建置失敗時分析錯誤訊息並提供修正建議；成功後回報結果。

## 發佈為單一執行檔

將桌面應用發佈為 self-contained 單一執行檔，支援 Windows、macOS、Linux。

### 1. 判斷目標平台

由參數指定目標平台，未指定時依目前作業系統自動偵測：

- Windows → `win-x64`
- macOS → `osx-arm64`（Apple Silicon）或 `osx-x64`（Intel）
- Linux → `linux-x64`

參數與 Runtime Identifier（RID）對照：

| 參數 | RID |
|------|-----|
| `win` / `win-x64` | win-x64 |
| `win-arm64` | win-arm64 |
| `mac` / `osx-x64` | osx-x64 |
| `mac-arm` / `osx-arm64` | osx-arm64 |
| `linux` / `linux-x64` | linux-x64 |
| `linux-arm64` | linux-arm64 |

### 2. 執行發佈指令

```bash
dotnet publish <桌面專案路徑> -c Release -r <rid> --self-contained -p:PublishSingleFile=true
```

- `<桌面專案路徑>`：桌面 app 進入點專案（含 `OutputType=WinExe` 或 Avalonia app 主專案）。
- `<rid>`：上表對照的 Runtime Identifier。
- `--self-contained`：內含 .NET runtime，目標機器免安裝 runtime。
- `-p:PublishSingleFile=true`：打包成單一 exe。

### 3. macOS 額外打包（僅 `osx-*`）

macOS 平台在 `dotnet publish` 完成後，另需將 publish 產物包成原生格式。以打包腳本產生：

```bash
./scripts/create-macos-bundle.sh <version> <rid> <publish 輸出目錄> <發佈輸出目錄>
```

- `<version>` 從桌面專案 `.csproj` 的 `<Version>` 取得。
- 產出 `.app` bundle（macOS 原生應用程式格式）與 `.dmg` 安裝映像檔（使用者可直接點兩下安裝）。

> 若專案尚無此腳本：`.app` 為含 `Contents/MacOS/`、`Contents/Info.plist`、`Contents/Resources/` 的目錄結構，`.dmg` 可用 `hdiutil`（macOS 內建）從 `.app` 產生。

## 輸出位置

- **Windows / Linux**：`<桌面專案>/bin/Release/<tfm>/<rid>/publish/`
- **macOS**：發佈輸出目錄下的 `<AppName>-<version>-<rid>.dmg`

## 桌面捷徑

發佈完成後，可為使用者建立桌面捷徑指向產出的執行檔：

- **Windows**：於桌面建立 `.lnk`（指向 `publish/` 內的 `.exe`）。
- **Linux**：於 `~/.local/share/applications/` 或桌面建立 `.desktop` 檔（含 `Exec=` 指向執行檔、`Icon=` 指向圖示）。
- **macOS**：`.app` 拖入 `/Applications` 或於桌面建立 alias 即可。
