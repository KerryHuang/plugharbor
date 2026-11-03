# .NET 附錄

適用：`*.csproj`／`*.sln`。通用原則見上層 SKILL.md。

## 路徑與平台判斷

- 檔案路徑一律用 `Path.Combine()` 組合，不硬編碼分隔符。
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

## 建置指令

`dotnet build / test / run / publish` 皆跨平台。腳本以 Git Bash／Unix 語法為準，換行用 LF（於 `.editorconfig` 統一）。

## 發佈平台

發佈時依實際使用者環境挑選 RID（`win-x64`、`osx-arm64`、`linux-x64` 等）。桌面應用的發佈細節見 desktop plugin 的 `build-publish`（可選；沒裝時用 `dotnet publish -c Release -r <rid> --self-contained`）。

## 常見坑

- **症狀**：Linux 上 `FileNotFoundException`，Windows 上正常。
  **原因**：程式碼或 `.csproj` 引用的檔名大小寫與磁碟不符。
  **修法**：改成與實際檔名完全一致。
- **症狀**：腳本在 Git Bash 後出現名為 `nul` 的檔案。
  **原因**：用了 Windows 的 `> nul`。
  **修法**：改 `> /dev/null 2>&1`，刪掉誤建的 `nul` 檔。
- **症狀**：Linux／macOS 上路徑含 `\` 找不到檔案。
  **原因**：手接字串用了 `\` 分隔符。
  **修法**：改用 `Path.Combine`。
- **症狀**：`.sh` 在 Linux 報 `bad interpreter` 或 `\r: command not found`。
  **原因**：checkout 時被轉成 CRLF。
  **修法**：`.gitattributes` 設 `*.sh text eol=lf`，重新 checkout。
