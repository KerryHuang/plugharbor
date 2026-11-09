# Changelog

格式：每次改動 `skills/`、`agents/`、`references/` 時，於最上方新增版本條目並同步 bump 版號（規則見 `.claude/rules/version-consistency.md`）。

## [1.0.1] - 2026-11-10

- docs: 1 個 skill 的 frontmatter 加 `triggers` 欄位（單行 JSON 陣列，不進 skill 清單、description 不變）。這個 plugin 被明確停用時，toolkit 的 `disabled-skills.py` 會拿它比對使用者訊息，提示這個 skill 存在。起因同 toolkit 0.18.0：別的專案跑 /doctor 關掉少用的 plugin 後，之後要用時找不到。

## [1.0.0] - 2026-11-03

- feat: 新 plugin，自 desktop-avalonia 0.1.0 改寫：`avalonia-mvvm` → `mvvm`（通用原則）、`desktop-build-publish` → `build-publish`（通用流程）；Avalonia／CommunityToolkit.Mvvm／`dotnet publish` 寫法完整搬入附錄 `references/stacks/avalonia.md`，並補「常見坑」。
- feat: 偵測 `*.csproj` 引用 `Avalonia` 載入附錄；WPF、WinUI、Electron、Tauri 暫無附錄，走既有程式寫法的退路。
- refactor: `cross-platform` 移至 workspace plugin，不再屬於 desktop。
- feat: 加 `package.json`（`pi.skills`）。
