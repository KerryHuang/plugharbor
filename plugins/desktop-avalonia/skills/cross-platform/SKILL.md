---
name: cross-platform
description: Avalonia 桌面專案的跨平台慣例——Windows/macOS/Linux 相容的路徑處理、平台判斷、腳本語法與 null 裝置寫法。Use when 寫檔案路徑、判斷作業系統、寫 shell 腳本或 CI workflow、避免 Windows 專用指令、cross platform、path.combine、跨平台腳本。
---

# 跨平台慣例

桌面應用常需同時支援 Windows、macOS、Linux。路徑、腳本、指令都要跨平台相容。

## 路徑處理（C#）

- 檔案路徑一律用 `Path.Combine()` 組合，不硬編碼分隔符（`\` 或 `/`）。
- 平台判斷用 `OperatingSystem.IsWindows()` / `OperatingSystem.IsMacOS()` / `OperatingSystem.IsLinux()`，不靠字串比對環境變數。
- 預設路徑集中在一個靜態方法（如 `GetDefaultPaths()`）提供，建構函式接受覆寫參數，方便測試與客製。

```csharp
public static AppPaths GetDefaultPaths()
{
    var baseDir = OperatingSystem.IsWindows()
        ? Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData)
        : Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);

    return new AppPaths(
        configFile: Path.Combine(baseDir, "MyApp", "config.json"));
}
```

## 腳本與指令（shell）

腳本以 Git Bash / Unix 語法為準，路徑分隔符統一用 `/`，換行符用 **LF**（於 `.editorconfig` 統一）。

### Null 裝置（丟棄輸出）

統一使用 `/dev/null`，不要用 Windows 的 `nul`：

```bash
command > /dev/null        # 正確
command > /dev/null 2>&1   # 正確
command > nul              # 錯誤（在 Git Bash 會實際建立一個名為 nul 的檔案）
```

### 避免使用的 Windows 專用指令

| 避免 | 跨平台替代 |
|------|-----------|
| `dir` | `ls` |
| `copy` / `move` / `del` | `cp` / `mv` / `rm` |
| `type` | `cat` |
| `set VAR=` | `export VAR=` |
| `taskkill` | 使用跨平台 SDK 方法處理程序 |

### 常用跨平台指令

```bash
dotnet build / test / run / publish   # 建置與執行皆跨平台
mkdir -p path                          # 建立目錄（含中間層）
```

## 發佈平台

發佈時同時產出各目標平台版本（如 `win-x64`、`osx-arm64`、`linux-x64`），依實際使用者環境挑選要涵蓋的 RID。發佈細節見 `desktop-build-publish` skill。
