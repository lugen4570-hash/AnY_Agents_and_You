# 构建正式版 Tauri 2 桌面外壳（需要 Rust 与 MSVC / Windows SDK 构建环境）
#   .\build_desktop.ps1
# 产物在 dist\CojamDesktop.exe；与 dist\CojamCore\（CojamCore.exe + _internal\）放在同一文件夹后双击。
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$cargoBin = Join-Path $env:USERPROFILE ".cargo\bin"
if ((Test-Path $cargoBin) -and -not ($env:Path -split ";" | Where-Object { $_ -eq $cargoBin })) {
    $env:Path = "$cargoBin;" + $env:Path
}
if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Write-Host "没找到 cargo。请先安装 Rust 工具链（rustup + MSVC Build Tools）。" -ForegroundColor Yellow
    exit 1
}

python make_icon.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$manifest = Join-Path $PSScriptRoot "desktop_tauri\src-tauri\Cargo.toml"
$iconSrc = Join-Path $PSScriptRoot "roundtable.ico"
$iconDst = Join-Path $PSScriptRoot "desktop_tauri\src-tauri\icons\icon.ico"
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $iconDst) | Out-Null
Copy-Item -Force -LiteralPath $iconSrc -Destination $iconDst

Write-Host "cargo build --release --manifest-path $manifest" -ForegroundColor Cyan
cargo build --locked --release --manifest-path $manifest
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$builtExe = Join-Path $PSScriptRoot "desktop_tauri\src-tauri\target\release\cojam-desktop.exe"
if (-not (Test-Path -LiteralPath $builtExe)) {
    throw "未找到 Tauri 构建产物：$builtExe"
}
$distDir = Join-Path $PSScriptRoot "dist"
New-Item -ItemType Directory -Force -Path $distDir | Out-Null
$outExe = Join-Path $distDir "CojamDesktop.exe"
Copy-Item -Force -LiteralPath $builtExe -Destination $outExe

& (Join-Path $PSScriptRoot "sign_exe.ps1") -ExePath "dist/CojamDesktop.exe"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "好了：dist\CojamDesktop.exe（Tauri 2）" -ForegroundColor Green
