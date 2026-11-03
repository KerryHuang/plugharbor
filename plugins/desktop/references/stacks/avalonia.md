# Avalonia 附錄

適用：`*.csproj` 引用 `Avalonia`，MVVM 使用 CommunityToolkit.Mvvm。供 `mvvm`、`build-publish` skill 共用。

## MVVM（CommunityToolkit.Mvvm）

### ViewModel 結構

- ViewModel 為 `partial class`，繼承共用基底（如 `ObservableObject` 或專案自訂的 `ViewModelBase`）。
- 可觀察屬性：用 `[ObservableProperty]` 標註私有欄位（`_camelCase`），由 source generator 產生對應的公開屬性。
- 命令：用 `[RelayCommand]`；需啟用／停用時以 `CanExecute` 連結布林屬性。
- 屬性變更側效應：實作 partial method `partial void OnXxxChanged(T value)`，不在屬性 setter 內手寫邏輯。

```csharp
public partial class ExampleViewModel : ObservableObject
{
    [ObservableProperty]
    private string _keyword = string.Empty;

    [ObservableProperty]
    [NotifyCanExecuteChangedFor(nameof(SearchCommand))]
    private bool _canSearch;

    [RelayCommand(CanExecute = nameof(CanSearch))]
    private async Task SearchAsync()
    {
        // ...
    }

    partial void OnKeywordChanged(string value)
    {
        CanSearch = !string.IsNullOrWhiteSpace(value);
    }
}
```

### 設計時支援

每個 ViewModel 同時提供兩種建構函式：

- **無參數建構函式**：設計時（designer preview）用，可塞假資料。
- **DI 建構函式**：執行時用，由 DI 容器注入依賴。

View 的 `DataContext` 一律透過 DI 注入取得 ViewModel 實例，不在 AXAML 中硬編碼具體型別。

### View 與 ViewModel 對應

- View 透過 DI 取得對應的 ViewModel 實例。
- AXAML binding 盡量使用 compiled bindings：在根節點宣告 `x:DataType="vm:XxxViewModel"`，享有編譯期型別檢查與較佳效能。
- 避免 `MultiBinding` + `BoolConverters.And` 等在 XAML 層堆疊邏輯，改用 ViewModel 上的計算屬性承載，讓判斷邏輯可測試。
- 對話框（dialog）透過 code-behind 的事件處理開啟，操作結果回傳給 ViewModel，不讓 ViewModel 直接依賴視窗型別。

### AXAML 特殊情境

- **DataGrid 內按鈕綁定命令**：DataGrid 的資料列 DataContext 是列項目而非外層 ViewModel，需以具名元素回指外層 ViewModel：

  ```xml
  Command="{Binding #DataGridName.((vm:ExampleViewModel)DataContext).RemoveCommand}"
  ```

- **資料列著色**：在 code-behind 處理 DataGrid 的 `LoadingRow` 事件，依列資料狀態套用樣式，不在 XAML 內用複雜 converter 硬湊。

### 資源嵌入

Avalonia 資源（icon、圖片等）必須在 `.csproj` 以 `<AvaloniaResource>` 宣告，才會嵌入發佈包；否則發佈後執行時找不到資源：

```xml
<ItemGroup>
  <AvaloniaResource Include="Assets/**" />
</ItemGroup>
```

## 建置與發佈（dotnet）

### 建置

```bash
dotnet build
```

建置失敗時分析錯誤訊息並提供修正建議；成功後回報結果。

### 發佈為單一執行檔

將桌面應用發佈為 self-contained 單一執行檔，支援 Windows、macOS、Linux。

**1. 判斷目標平台**：由參數指定，未指定時依目前作業系統自動偵測：

- Windows → `win-x64`
- macOS → `osx-arm64`（Apple Silicon）或 `osx-x64`（Intel）
- Linux → `linux-x64`

| 參數 | RID |
|------|-----|
| `win` / `win-x64` | win-x64 |
| `win-arm64` | win-arm64 |
| `mac` / `osx-x64` | osx-x64 |
| `mac-arm` / `osx-arm64` | osx-arm64 |
| `linux` / `linux-x64` | linux-x64 |
| `linux-arm64` | linux-arm64 |

**2. 執行發佈指令**

```bash
dotnet publish <桌面專案路徑> -c Release -r <rid> --self-contained -p:PublishSingleFile=true
```

- `<桌面專案路徑>`：桌面 app 進入點專案（含 `OutputType=WinExe` 或 Avalonia app 主專案）。
- `<rid>`：上表對照的 Runtime Identifier。
- `--self-contained`：內含 .NET runtime，目標機器免安裝 runtime。
- `-p:PublishSingleFile=true`：打包成單一 exe。

**3. macOS 額外打包（僅 `osx-*`）**：`dotnet publish` 完成後，另需將產物包成原生格式：

```bash
./scripts/create-macos-bundle.sh <version> <rid> <publish 輸出目錄> <發佈輸出目錄>
```

- `<version>` 從桌面專案 `.csproj` 的 `<Version>` 取得。
- 產出 `.app` bundle 與 `.dmg` 安裝映像檔（使用者可直接點兩下安裝）。

> 若專案尚無此腳本：`.app` 為含 `Contents/MacOS/`、`Contents/Info.plist`、`Contents/Resources/` 的目錄結構，`.dmg` 可用 `hdiutil`（macOS 內建）從 `.app` 產生。

### 輸出位置

- **Windows / Linux**：`<桌面專案>/bin/Release/<tfm>/<rid>/publish/`
- **macOS**：發佈輸出目錄下的 `<AppName>-<version>-<rid>.dmg`

### 桌面捷徑

- **Windows**：於桌面建立 `.lnk`（指向 `publish/` 內的 `.exe`）。
- **Linux**：於 `~/.local/share/applications/` 或桌面建立 `.desktop` 檔（含 `Exec=`、`Icon=`）。
- **macOS**：`.app` 拖入 `/Applications` 或於桌面建立 alias。

### 跨平台寫法

.NET 路徑、換行、平台判斷的跨平台做法見 workspace plugin 的 `cross-platform` skill 與其 .NET 附錄（可選；沒裝時：路徑用 `Path.Combine`，平台判斷用 `OperatingSystem.IsWindows()` 等）。

## 常見坑

- **症狀**：發佈後執行時找不到 icon、圖片或字型。
  **原因**：資源沒在 `.csproj` 宣告為 `<AvaloniaResource>`，沒嵌入發佈包。
  **修法**：加 `<AvaloniaResource Include="Assets/**" />` 並重新發佈。
- **症狀**：DataGrid 列內按鈕的命令按了沒反應。
  **原因**：資料列 `DataContext` 是列項目，不是外層 ViewModel。
  **修法**：用 `#DataGridName.((vm:XxxViewModel)DataContext).XxxCommand` 回指外層。
- **症狀**：設計時預覽器空白或報錯。
  **原因**：ViewModel 只有 DI 建構函式，預覽器無法建立。
  **修法**：補無參數建構函式並塞假資料。
- **症狀**：binding 拼錯屬性名，執行時靜默失敗。
  **原因**：沒啟用 compiled bindings，缺 `x:DataType`。
  **修法**：根節點宣告 `x:DataType="vm:XxxViewModel"`，建置時就會報錯。
- **症狀**：macOS 發佈只得到一堆檔案，沒有 `.app`／`.dmg`。
  **原因**：`dotnet publish` 只輸出可執行檔，不產生 bundle。
  **修法**：publish 後跑打包腳本，或手動組 `.app` 再用 `hdiutil` 產 `.dmg`。
