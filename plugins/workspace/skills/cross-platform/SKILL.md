---
name: cross-platform
description: 跨平台（Windows／macOS／Linux）撰寫程式與腳本的通用做法——路徑與分隔符、換行（LF／CRLF）、檔名大小寫、shell 語法差異、null 裝置、環境變數與編碼；附 .NET 寫法。Use when 寫檔案路徑、判斷作業系統、寫 shell 腳本或 CI workflow、避免 Windows 專用指令、處理換行或大小寫問題、"cross platform"、"跨平台"、"path.combine"、"在 Mac／Linux 上壞掉"。
---

# 跨平台慣例

程式、腳本、CI 要在 Windows、macOS、Linux 都能跑。原則：不假設分隔符、不假設大小寫、不假設換行、不假設 shell。

## 0. 偵測技術棧與附錄

先看專案的 `*.csproj`、`package.json`、`go.mod`、`pyproject.toml`、`.editorconfig`、`.gitattributes`，對照下表載入附錄，並在回報第一行寫「附錄：<檔名>」。

| 偵測到 | 附錄 |
|---|---|
| `*.csproj`、`*.sln` | `references/dotnet.md` |

沒有對應附錄：照本 skill 的通用方法，加上專案既有程式的寫法（先找 2–3 個同類檔當樣板；照 `convention-first` skill）。做完問使用者要不要整理成新附錄 `references/<stack>.md`，回報寫「附錄：無（照既有程式）」。

## 路徑

- 用語言標準函式庫組路徑與取檔名（`Path.Combine`、`path.join`、`pathlib`、`filepath.Join`），不手接字串、不硬編碼 `\` 或 `/`。
- 使用者資料、設定、快取放各平台的標準位置（Windows `%APPDATA%`、macOS `~/Library/Application Support`、Linux `$XDG_CONFIG_HOME`），不寫死 `C:\` 或 `/home/...`。
- 預設路徑集中在一處提供，建構時可覆寫，方便測試。
- 不假設家目錄、暫存目錄位置；用標準函式取。
- 路徑比較與去重要正規化（絕對化、統一分隔符）；Windows 與 macOS 預設大小寫不敏感，Linux 敏感。

## 檔名大小寫

- 在大小寫不敏感的系統上寫的程式，到 Linux 會因 `Foo.cs` vs `foo.cs`、`import './Utils'` vs `utils.js` 壞掉。
- 引用檔案、匯入模組一律與磁碟上的實際大小寫完全一致。
- 只改大小寫的重新命名，在 git 要用 `git mv`（必要時分兩步），否則 Windows／macOS 不會偵測到。
- 不在同一目錄放只差大小寫的兩個檔案。
- 檔名避開 Windows 保留名（`con`、`nul`、`aux`、`com1`…）與結尾的點或空格。

## 換行與編碼

- repo 統一 LF：`.gitattributes` 設 `* text=auto eol=lf`（批次檔、`.ps1`、`.sln` 之類需要 CRLF 的另外指定），`.editorconfig` 設 `end_of_line = lf`。
- shell 腳本若帶 CRLF，在 Linux／macOS 會報 `bad interpreter` 或 `\r: command not found`；修法是轉 LF，不是改直譯器。
- 檔案編碼一律 UTF-8（不帶 BOM，除非工具要求）；讀寫時明確指定編碼，不依賴系統預設。
- 文字處理不假設行尾，用語言的逐行讀取而非自己切 `\n`。

## 平台判斷

- 用語言提供的平台判斷 API（如 `OperatingSystem.IsWindows()`、`process.platform`、`runtime.GOOS`、`sys.platform`），不靠環境變數或路徑字串猜。
- 平台分支集中在少數幾個封裝處，其餘程式不散落 `if windows`。
- 每個分支都要有 else：未支援的平台明確報錯，不靜默走 Windows 路徑。

## 腳本與指令（shell）

腳本以 POSIX／Git Bash 語法為準，路徑分隔符用 `/`，shebang 寫 `#!/usr/bin/env bash`，並設可執行位（`git update-index --chmod=+x`）。

### Null 裝置

統一用 `/dev/null`，不要用 Windows 的 `nul`：

```bash
command > /dev/null        # 正確
command > /dev/null 2>&1   # 正確
command > nul              # 錯誤（在 Git Bash 會實際建立一個名為 nul 的檔案）
```

### 避免 Windows 專用指令

| 避免 | 跨平台替代 |
|------|-----------|
| `dir` | `ls` |
| `copy` / `move` / `del` | `cp` / `mv` / `rm` |
| `type` | `cat` |
| `set VAR=` | `export VAR=` |
| `taskkill` | 用語言／SDK 的程序管理 API |

### 其他差異

- `sed -i`：GNU 直接 `sed -i 's/a/b/' f`，BSD（macOS）要 `sed -i '' ...`；要可攜就用 `perl -pi -e` 或臨時檔。
- `date`、`readlink -f`、`xargs -r`、`grep -P` 在 macOS 預設行為不同或不存在；用到先確認，或改用 Python／Node 腳本。
- `mkdir -p`、`rm -rf`、`cp -R` 是可攜寫法。
- 環境變數：跨 shell 設定用 `export`；CI 內用平台的語法（GitHub Actions 的 `env:`、`$GITHUB_ENV`）。
- 複雜邏輯不要寫成 shell 再硬套多平台，改寫成專案語言的腳本（Node／Python／dotnet script）。

## CI

- matrix 至少涵蓋要支援的平台（`ubuntu-latest`、`windows-latest`、`macos-latest`）。
- step 指定 `shell: bash`，讓 Windows runner 也用同一套語法。
- 快取 key 含 `runner.os`。

## 驗收

- 在每個支援平台各跑一次建置與測試（本機或 CI matrix）；只在一個平台通過不能宣稱跨平台。
- 用 grep 掃一次硬編碼路徑（`C:\\`、`/home/`、`/Users/`）與手接的反斜線。
- 未實際跑到的平台標「未驗證」。
