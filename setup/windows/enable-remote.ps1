# 重灌後第一件事：讓 Mac 能 SSH 進來，其餘交給 Mac 上的 Claude 遠端建置。
# 用法（以系統管理員身分開 Windows PowerShell）：
#   irm https://raw.githubusercontent.com/KerryHuang/plugharbor/main/setup/windows/enable-remote.ps1 | iex
# 公鑰取自 https://github.com/<帳號>.keys；換帳號先設 $env:PH_GITHUB_USER。冪等，可重跑。

$ErrorActionPreference = 'Stop'
$GitHubUser = if ($env:PH_GITHUB_USER) { $env:PH_GITHUB_USER } else { 'KerryHuang' }

$principal = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw '請用「以系統管理員身分執行」開 PowerShell 再跑一次。'
}

Write-Host '== 開發人員模式（plugharbor 建 symlink 要用）'
reg add 'HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock' /v AllowDevelopmentWithoutDevLicense /t REG_DWORD /d 1 /f | Out-Null

Write-Host '== 接電源時不睡眠（遠端建置中途睡著會斷線）'
powercfg /change standby-timeout-ac 0

Write-Host '== OpenSSH Server'
$cap = Get-WindowsCapability -Online -Name 'OpenSSH.Server*' | Select-Object -First 1
if ($cap.State -ne 'Installed') { Add-WindowsCapability -Online -Name $cap.Name | Out-Null }
Set-Service sshd -StartupType Automatic
Start-Service sshd
if (-not (Get-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -DisplayName 'OpenSSH Server (sshd)' `
        -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22 | Out-Null
}
New-Item -Path 'HKLM:\SOFTWARE\OpenSSH' -Force | Out-Null
New-ItemProperty -Path 'HKLM:\SOFTWARE\OpenSSH' -Name DefaultShell -PropertyType String -Force `
    -Value "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" | Out-Null

Write-Host "== 從 github.com/$GitHubUser.keys 寫入管理員公鑰"
$keys = (Invoke-RestMethod "https://github.com/$GitHubUser.keys").Trim()
if (-not $keys) { throw "github.com/$GitHubUser.keys 沒有公鑰，先把 Mac 的公鑰加到 GitHub。" }
$authFile = "$env:ProgramData\ssh\administrators_authorized_keys"
Set-Content -Path $authFile -Value $keys -Encoding ascii
# 管理員群組的公鑰檔只能讓 Administrators 與 SYSTEM 存取，否則 sshd 不讀；用 SID 避開中文群組名
icacls $authFile /inheritance:r /grant '*S-1-5-32-544:F' /grant '*S-1-5-18:F' | Out-Null
Restart-Service sshd

Write-Host '== Tailscale'
winget install --id Tailscale.Tailscale -e --silent --accept-package-agreements --accept-source-agreements --disable-interactivity
if ($LASTEXITCODE -ne 0) { Write-Warning "Tailscale 安裝回傳 $LASTEXITCODE；同一個區網可以先略過。" }

$ip = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.PrefixOrigin -in 'Dhcp', 'Manual' -and $_.IPAddress -notlike '169.254*' } |
    Select-Object -ExpandProperty IPAddress) -join ', '
Write-Host ''
Write-Host '完成。接下來：'
Write-Host '  1. 從右下角 Tailscale 圖示登入（同一個區網可略過）'
Write-Host "  2. 在 Mac 上：ssh $env:USERNAME@$env:COMPUTERNAME   （區網 IP：$ip）"
Write-Host '  3. 連得上就交給 Mac 上的 Claude，照 setup/windows/README.md 往下做'
