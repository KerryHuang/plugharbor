---
name: avalonia-mvvm
description: Avalonia + CommunityToolkit.Mvvm 桌面專案的 MVVM 慣例——ViewModel 結構、ObservableProperty/RelayCommand、compiled bindings、設計時支援與 AXAML 特殊情境。Use when 撰寫或修改 Avalonia View/ViewModel、寫 AXAML binding、處理對話框回傳、DataGrid 命令綁定、avalonia mvvm、observableproperty、relaycommand。
---

# Avalonia MVVM 慣例

以 CommunityToolkit.Mvvm 實作 MVVM。以下慣例適用任何 Avalonia + CommunityToolkit.Mvvm 桌面專案。

## ViewModel 結構

- ViewModel 為 `partial class`，繼承共用基底（如 `ObservableObject` 或專案自訂的 `ViewModelBase`）。
- 可觀察屬性：用 `[ObservableProperty]` 特性標註私有欄位（`_camelCase`），由 source generator 產生對應的公開屬性。
- 命令：用 `[RelayCommand]` 特性；需啟用/停用時以 `CanExecute` 連結布林屬性。
- 屬性變更側效應：實作 partial method `partial void OnXxxChanged(T value)`，不要在屬性 setter 內手寫邏輯。

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

## 設計時支援

每個 ViewModel 同時提供兩種建構函式：

- **無參數建構函式**：設計時（designer preview）用，可塞假資料。
- **DI 建構函式**：執行時用，由 DI 容器注入依賴。

View 的 `DataContext` 一律透過 DI 注入取得 ViewModel 實例，不在 AXAML 中硬編碼具體型別。

## View 與 ViewModel 對應

- View 透過 DI 取得對應的 ViewModel 實例。
- AXAML binding 盡量使用 compiled bindings：在根節點宣告 `x:DataType="vm:XxxViewModel"`，享有編譯期型別檢查與較佳效能。
- 避免 `MultiBinding` + `BoolConverters.And` 等在 XAML 層堆疊邏輯，改用 ViewModel 上的計算屬性（computed property）承載，讓判斷邏輯可測試。
- 對話框（dialog）透過 code-behind 的事件處理開啟，操作結果回傳給 ViewModel，不讓 ViewModel 直接依賴視窗型別。

## AXAML 特殊情境

- **DataGrid 內按鈕綁定命令**：DataGrid 的資料列 DataContext 是列項目而非外層 ViewModel，需以具名元素回指外層 ViewModel：

  ```xml
  Command="{Binding #DataGridName.((vm:ExampleViewModel)DataContext).RemoveCommand}"
  ```

- **資料列著色**：在 code-behind 處理 DataGrid 的 `LoadingRow` 事件，依列資料狀態套用樣式，不在 XAML 內用複雜 converter 硬湊。

## 資源嵌入

Avalonia 資源（icon、圖片等）必須在 `.csproj` 以 `<AvaloniaResource>` 宣告，才會嵌入發佈包；否則發佈後執行時找不到資源：

```xml
<ItemGroup>
  <AvaloniaResource Include="Assets/**" />
</ItemGroup>
```
