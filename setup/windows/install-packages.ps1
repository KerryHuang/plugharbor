# 依層別安裝 winget 套件；已裝的略過，冪等。
# 用法：powershell -ExecutionPolicy Bypass -File install-packages.ps1 core optional personal
# 層別對應 packages/<層>.txt，一行一個 winget ID，# 開頭為註解。失敗任一項 exit 1。

$layers = if ($args.Count) { $args } else { @('core') }
$failed = @()
foreach ($layer in $layers) {
    $file = Join-Path $PSScriptRoot "packages\$layer.txt"
    if (-not (Test-Path $file)) { Write-Host "FAIL: 找不到 $file"; $failed += $layer; continue }
    foreach ($line in Get-Content $file -Encoding UTF8) {
        $line = $line.Trim()
        if (-not $line -or $line.StartsWith('#')) { continue }
        $id = ($line -split '\s+')[0]
        winget list --id $id -e --accept-source-agreements *> $null
        if ($LASTEXITCODE -eq 0) { Write-Host "SKIP: $id"; continue }
        winget install --id $id -e --silent --accept-package-agreements --accept-source-agreements --disable-interactivity
        if ($LASTEXITCODE -eq 0) { Write-Host "OK: $id" } else { Write-Host "FAIL: $id ($LASTEXITCODE)"; $failed += $id }
    }
}
if ($failed) { Write-Host "失敗：$($failed -join ', ')"; exit 1 }
