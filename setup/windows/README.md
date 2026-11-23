# setup/windows：重灌後由 Mac 遠端建置 Windows

前提：Mac 的 SSH 公鑰已登記在 GitHub（`github.com/KerryHuang.keys` 拿得到）。

## 1. Windows 本機（唯一要親手做的一步）

以系統管理員身分開 Windows PowerShell：

```powershell
irm https://raw.githubusercontent.com/KerryHuang/plugharbor/main/setup/windows/enable-remote.ps1 | iex
```

會開啟開發人員模式、關掉接電時的睡眠、啟用 OpenSSH Server（預設 shell 為 Windows PowerShell）、
把 GitHub 公鑰寫進 `administrators_authorized_keys`、裝 Tailscale。之後從 Tailscale 圖示用個人帳號登入。

> 只用 `irm | iex` 跑：腳本沒有 BOM，Windows PowerShell 5.1 以 `-File` 讀會把中文當 cp950。

## 2. Mac 上的 Claude 接手（`ssh <使用者>@<主機>`）

1. `git clone https://github.com/KerryHuang/plugharbor.git $HOME\plugharbor`
   （Git 還沒裝就先 `winget install --id Git.Git -e --silent`）
2. 套件：`powershell -ExecutionPolicy Bypass -File $HOME\plugharbor\setup\windows\install-packages.ps1 core`，
   要的話再加 `optional`、`personal`。新開一個 SSH 連線讓 PATH 生效。
3. Node：`nvm install 22; nvm use 22`。
4. agent CLI：
   - Claude Code：`irm https://claude.ai/install.ps1 | iex`
   - codex：`npm i -g @openai/codex`
   - pi、herdr、agy：⚠️ 安裝方式尚未寫成腳本，照各自官方文件裝
5. Git：`git config --global user.name …`、`user.email …`；新產 SSH key 登記到新公司的 Git 主機。
6. 設定：在 Git Bash 跑 `bash $HOME/plugharbor/setup/bootstrap.sh`，再跑 `--check` 確認 exit 0。

## 3. 本人要做的

- 各 CLI 登入（`claude`、`gh auth login`、`codex login`）：走瀏覽器或 device code，可以在 Mac 上完成授權。
- `optional` 層的 WSL、Docker 裝完要重開機；Docker 首次啟動要在 GUI 同意條款。

## 套件清單

`packages/core.txt`（通用）、`optional.txt`（看工作需要）、`personal.txt`（桌面偏好）。
`install-packages.ps1` 用 `winget list` 判斷是否已裝；不是用 winget 裝的（scoop、官方安裝程式）偵測不到，會再裝一份。
