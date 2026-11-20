# 打成 Windows 便携单文件 exe（dist\Cojam.exe）及桌面目录版核心（dist\CojamCore\）
# 需要先装 PyInstaller：pip install pyinstaller
#   .\build_exe.ps1                 默认同时构建便携单文件版与桌面 --onedir 核心
#   .\build_exe.ps1 -Mode onefile   只打 dist\Cojam.exe（浏览器/便携单文件版）
#   .\build_exe.ps1 -Mode onedir    只打 dist\CojamCore\（桌面安装版目录核心）
# 注意：exe 里自带 Python，但 claude / codex / gemini 这些命令还得用户自己装在 PATH 里。
param([ValidateSet('all', 'onefile', 'onedir')][string]$Mode = 'all')
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python make_icon.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python -m bridge.member_package
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    Write-Host "没装 PyInstaller。先跑：pip install pyinstaller" -ForegroundColor Yellow
    exit 1
}

$commonArgs = @(
    "--noconfirm", "--clean", "--windowed",
    "--icon", "roundtable.ico",
    "--add-data", "index.html;.",
    "--add-data", "static;static",
    "--add-data", "bridge\presets;bridge\presets",
    "--add-data", "bridge\catalog;bridge\catalog",
    "--hidden-import", "bridge.web",
    "--hidden-import", "bridge.acp",
    "--hidden-import", "bridge.discovery",
    "--hidden-import", "bridge.conn_settings",
    "--hidden-import", "bridge.mcp_stdio",
    "roundtable.py"
)

function Invoke-CoreBuild([string]$KindFlag, [string]$OutName, [string]$BuiltRel) {
    $args = @($KindFlag, "--name", $OutName) + $commonArgs
    Write-Host "pyinstaller $($args -join ' ')" -ForegroundColor Cyan
    pyinstaller @args
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & (Join-Path $PSScriptRoot "sign_exe.ps1") -ExePath $BuiltRel
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if ($Mode -in @('all', 'onefile')) {
    Invoke-CoreBuild "--onefile" "Cojam" "dist/Cojam.exe"
    Write-Host "好了：dist\Cojam.exe" -ForegroundColor Green
}
if ($Mode -in @('all', 'onedir')) {
    Invoke-CoreBuild "--onedir" "CojamCore" "dist/CojamCore/CojamCore.exe"
    Write-Host "好了：dist\CojamCore\CojamCore.exe" -ForegroundColor Green
}
