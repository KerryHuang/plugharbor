# desktop

桌面應用開發 plugin — MVVM 分層原則與建置發佈流程。SKILL.md 寫不綁技術的通用方法，技術寫法放附錄，換技術棧只要補一份附錄。

## 定位

`[desktop]` 任何桌面專案適用；跨平台路徑、換行、shell 差異見 workspace plugin 的 `cross-platform`（可選）。

## 技術棧附錄

位置：`references/stacks/<stack>.md`。skill 開頭會偵測專案並載入對應附錄，回報第一行寫「附錄：<檔名>」。

| 附錄 | 偵測線索 |
|---|---|
| `avalonia.md` | `*.csproj` 引用 `Avalonia`（含 CommunityToolkit.Mvvm、`dotnet publish` 寫法） |

WPF（`UseWPF`）、WinUI、Electron、Tauri 目前無附錄：照 skill 的通用方法，加上專案既有程式的寫法，做完會問要不要整理成新附錄。

## Skills（2）

| Skill | 用途 |
|-------|------|
| `mvvm` | MVVM 通用原則：View／ViewModel 分工、可觀察屬性、命令、繫結、導覽與對話框、設計時支援 |
| `build-publish` | 建置發佈通用流程：版號來源、目標平台矩陣、產出型態、安裝包、簽章與公證、桌面捷徑 |

## License

MIT
