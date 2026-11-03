---
name: mvvm
description: 桌面應用的 MVVM 分層原則——View／ViewModel 分工、可觀察屬性、命令、繫結、導覽與對話框、設計時支援；附 Avalonia + CommunityToolkit.Mvvm 附錄。Use when 撰寫或修改桌面 View／ViewModel、寫 XAML／AXAML 繫結、處理命令或對話框回傳、導覽切換畫面、"mvvm"、"viewmodel"、"relaycommand"、"observableproperty"、"data binding"。
---

# MVVM 分層原則

桌面 UI 以 MVVM 分層：View 只管呈現，ViewModel 持有狀態與行為，Model／Service 管資料與商業邏輯。

## 0. 偵測技術棧與附錄

先看專案的 `*.csproj`、`package.json`、`Cargo.toml`／`tauri.conf.json`，對照下表載入附錄，並在回報第一行寫「附錄：<檔名>」。

| 偵測到 | 附錄 |
|---|---|
| `*.csproj` 引用 `Avalonia` | `${CLAUDE_PLUGIN_ROOT}/references/stacks/avalonia.md` |
| `UseWPF`、WinUI、Electron、Tauri | 目前無附錄，走下方退路 |

沒有對應附錄：照本 skill 的通用方法，加上專案既有程式的寫法（先找 2–3 個同類檔當樣板；有裝 workspace 就照 `workspace:convention-first`（可選））。做完問使用者要不要把這次的寫法整理成新附錄 `references/stacks/<stack>.md`，回報寫「附錄：無（照既有程式）」。

## 分工

| 層 | 負責 | 不做 |
|---|---|---|
| View | 版面、樣式、繫結宣告、純視覺互動（動畫、焦點） | 商業邏輯、直接呼叫 Service、資料驗證規則 |
| ViewModel | 畫面狀態、命令、驗證結果、呼叫 Service | 引用 View 或視窗型別、操作控制項 |
| Model／Service | 資料存取、商業規則、檔案與網路 | 知道 UI 存在 |

判斷準則：ViewModel 能不開視窗、不啟動 UI 框架就單元測試；做不到就是有 View 的東西漏進來了。

## 可觀察屬性

- 畫面上會變的值做成可通知變更的屬性（`INotifyPropertyChanged` 或框架等價機制）；用框架的 source generator 或基底類別，不手寫樣板。
- 屬性變更的側效應（連動欄位、重新計算）放在變更回呼，不在 setter 手寫。
- 集合用可通知變更的集合型別；整批替換時注意 UI 刷新成本。
- 衍生值（例如「是否可儲存」）用計算屬性放在 ViewModel，不在 XAML 用多重繫結＋轉換器堆邏輯——放 ViewModel 才測得到。

## 命令

- 使用者動作一律走命令（Command）繫結，不寫成 code-behind 事件處理（純視覺互動除外）。
- 啟用條件用 `CanExecute` 表達；條件依賴的屬性變更時通知命令重新評估。
- 長時間工作用非同步命令：執行中停用自己、顯示進度、可取消；例外在命令內接住並轉成畫面狀態，不讓它炸出 UI 執行緒。
- 命令參數保持單純（識別值），不傳整個控制項。

## 繫結

- 優先使用編譯期型別檢查的繫結（compiled／typed binding），拼錯屬性名在建置時就失敗。
- 清單項目內要觸發外層 ViewModel 的命令時，用具名元素或相對來源回指外層，不把命令複製進每個項目。
- 轉換器只做純顯示轉換（格式、可見性）；有判斷邏輯的移回 ViewModel。
- 資料列著色、特殊樣式用樣式狀態（selector／trigger）或 code-behind 的視覺事件，不用複雜轉換器硬湊。

## 導覽與對話框

- 畫面切換由導覽服務（或父 ViewModel 持有 `CurrentPage`）統一處理；ViewModel 之間不互相 new 對方。
- 對話框（開檔、確認、輸入）以介面抽象（如 `IDialogService`），ViewModel 只 `await dialog.ConfirmAsync(...)` 取結果，不依賴視窗型別。沒有抽象時，退而求其次是 code-behind 開窗再把結果回傳給 ViewModel。
- 導覽參數用強型別物件或建構子注入，不靠全域字典傳值。
- 離開畫面時釋放訂閱（事件、訊息匯流排），避免洩漏與重複觸發。

## 依賴注入與設計時

- ViewModel 以建構子注入依賴，由 DI 容器建立；View 的 `DataContext` 由容器或導覽服務指定，不在標記語言內硬編碼具體型別。
- 提供設計時用的無參數建構（假資料），讓預覽器能顯示；執行時走 DI 建構。
- 跨 ViewModel 的鬆耦合通知用訊息匯流排（messenger），只在確實需要時用，不拿來取代直接注入 Service。

## 資源

圖示、圖片、字型要依框架規定宣告為內嵌資源，否則發佈後找不到；寫法見附錄。

## 驗收

- ViewModel 有不依賴 UI 框架的單元測試（命令啟用條件、屬性連動、錯誤路徑）。
- View 的 code-behind 只剩視覺互動；`grep` View 專案內沒有商業邏輯呼叫。
- 建置零警告（含繫結型別警告）；實際跑一次畫面，確認繫結沒有靜默失敗（看 binding error 輸出）。
