---
name: worktree
description: 適用於需要同時在多個分支平行工作、建立新 git worktree、切換到既有 worktree、安全移除單一已知 worktree（含 preflight 檢查與移除後驗證）。觸發語：「開 worktree」「切到某個 worktree」「移除 worktree」「平行分支開發」「create/switch/remove worktree」。（跨多個 branch/worktree 的盤點級清理決策請走 triage-branch-cleanup skill。）
---

# Git Worktree 管理

在同一個 repository 下建立多個工作目錄，每個目錄可以 checkout 到不同分支，同時進行開發，彼此互不干擾。

## 為什麼用 worktree

- 手上功能做到一半，臨時要修別的分支 → 不用 stash、不用切分支，另開 worktree 即可。
- 多個 ticket 平行開發，各自獨立目錄，build 產物、設定檔互不污染。
- Review 別人的分支時，不必動到自己的工作區。

## 兩種操作模式

worktree 的日常操作分兩類，互斥：

| 模式 | 用途 | 典型情境 |
|------|------|---------|
| 建立新 worktree | 新增工作目錄 + 新分支 | 開始一個新 ticket / 功能 |
| 切換既有 worktree | 進入已存在的工作目錄 | 在多個 worktree 之間切換 |

> 若你的環境有內建的 worktree 進入工具（例如編輯器或 CLI 提供的 `EnterWorktree` 之類的指令），優先使用它——它通常會把 session context 一併切過去，並可掛 hook 自動處理設定檔複製。以下以純 git 指令描述，任何環境皆適用。

## 建立新 Worktree

建議建在**主目錄的 sibling 層**（`../` 同層目錄），而非巢狀於 repo 內部——避免 Windows 路徑長度限制，也避免 worktree 被自己的 repo 掃描到。

```bash
# 從遠端最新的整合分支長出新分支 + 新 worktree
git fetch origin <base-branch>
git worktree add ../<repo>-<name> -b <branch> origin/<base-branch>
```

命名對照（範例，依團隊 Git Flow 慣例調整）：

| 類型 | worktree 目錄 | 分支命名 |
|-----|--------------|---------|
| Feature | `../<repo>-feature-101` | `feature/101` |
| Bugfix | `../<repo>-bugfix-102` | `bugfix/102` |
| Hotfix | `../<repo>-hotfix-urgent` | `hotfix/urgent` |
| Release | `../<repo>-release-1.4` | `release/1.4` |

### 設定檔與本機依賴的複製

新 worktree 是乾淨的 checkout，**不含 gitignore 掉的本機檔案**（環境設定、密鑰、本機 CLI 依賴等）。建立後需手動或以 hook 複製：

```bash
MAIN_DIR=$(git rev-parse --show-toplevel)
WORKTREE_DIR="../<repo>-<name>"

# 依專案實際情況複製本機設定檔（範例：環境設定、啟動設定）
cp "$MAIN_DIR/<path>/<local-config>" "$WORKTREE_DIR/<path>/<local-config>"
```

> 若某些 CLI 工具依賴主目錄特定檔案（config、快取目錄等），在 worktree 直接跑會失敗。兩種解法：(1) 把依賴檔一併複製進 worktree；(2) 用 subshell 回主目錄跑 `(cd "$MAIN_DIR" && <tool> ...)`。新增這類工具時，記得把複製邏輯補進建立流程。

## 切換到既有 Worktree

當 worktree 已存在（自己先前建立、或協作者留下），直接切換工作目錄：

```bash
# 1. 先查出現有 worktree
git worktree list
# /repos/myapp            d5cde19 [develop]
# /repos/myapp-feature-101  f0062cb [feature/101]

# 2. 進入目標目錄
cd ../myapp-feature-101
```

**前置檢查**：切換目標必須在 `git worktree list` 的輸出中；不是本 repo 的 registered worktree 就切不過去。

> **持久化 cwd 的陷阱**：若你的 shell / tool 的工作目錄跨指令持久，任何 `cd <其他目錄> && cmd` 都會把 cwd 留在那裡。切 worktree 後若又 `cd` 去別處，後續指令可能不在你以為的 worktree 內——動關鍵操作前先 `pwd` 確認。

## 查詢與管理

```bash
# 列出所有 worktree（主目錄本身也算一個 worktree）
git worktree list

# 移除 worktree
git worktree remove ../<repo>-<name>
git branch -d <branch>

# 清理已刪除目錄的孤兒 metadata
git worktree prune
```

## Cleanup 前 preflight 檢查

`git worktree remove` **回報 success ≠ 真的移除**。實務常見失敗：

1. **cwd lock**：當前 shell 的 cwd 仍在該 worktree 內 → remove 跳過或卡住。
2. **IDE / 編輯器 lock**：編輯器開著該目錄 → 檔案系統鎖（Windows 尤其明顯）。
3. **submodule / 未提交殘留**：worktree 內有未 commit / 未 push 的變更 → 強制移除會遺失。

**強制流程**：

```bash
TARGET="../<repo>-<name>"

# 1. 釋放 cwd（切回主目錄或任何非 TARGET 路徑）
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
pwd   # 確認不在 $TARGET 內

# 2. 未提交變更 preflight（含 submodule）
git -C "$TARGET" status --porcelain
git -C "$TARGET" submodule status 2>&1
# 任何 dirty 內容或 submodule 的 +/-/U 前綴 → 先處理（commit / push / discard）再刪

# 3. 執行移除
git worktree remove "$TARGET"

# 4. 移除後三方驗證（observable end state，不靠 remove 的回傳值）
git worktree list | grep -F "$TARGET" && echo "❌ 仍在清單" || echo "✅ 已移除"
test -d "$TARGET" && echo "❌ 資料夾仍在（檔案鎖）" || echo "✅ 資料夾已消失"
git branch -a | grep -E "feature/$NAME|bugfix/$NAME|hotfix/$NAME"   # 確認 branch 狀態符合預期
```

**若 §4 顯示資料夾未消失**（IDE / shell 鎖住）：
1. 關閉編輯器對該目錄的 window。
2. 確認沒有背景 shell 的 cwd 停在裡面。
3. 仍鎖 → `git worktree remove --force` + `mv "$TARGET" "${TARGET}.del"` 改名 workaround，待 lock 釋放後人工刪。
4. 切忌假裝移除成功就跳下一步。

## 注意事項

- 每個分支只能有一個 worktree；主目錄也算一個 worktree。
- 新 worktree 是乾淨 checkout，gitignore 的本機檔案需自行複製。
- 移除前務必跑 preflight（釋放 cwd + 檢查未提交變更），且以 observable end state 驗證，不信 remove 的回傳值。

## 快速參考

```bash
# 建立新 worktree（sibling 層 + 從遠端整合分支長出）
git fetch origin develop
git worktree add ../myapp-feature-101 -b feature/101 origin/develop
# 複製本機設定檔...
cd ../myapp-feature-101

# 切換既有（先 list 確認路徑）
git worktree list
cd ../myapp-feature-101

# 移除（走 preflight）
cd "$(git rev-parse --show-toplevel)"
git worktree remove ../myapp-feature-101
git branch -d feature/101
git worktree prune
```
