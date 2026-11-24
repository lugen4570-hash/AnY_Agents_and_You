$ErrorActionPreference = 'Stop'

$BaseUrl = 'https://lugen4570-hash.github.io/AnY_Agents_and_You/'
if ($env:ANY_CLI_TEST_SOURCE -match '^http://127\.0\.0\.1:[0-9]+/$') {
  $BaseUrl = $env:ANY_CLI_TEST_SOURCE
}

function Test-Python311 {
  param([string]$Exe, [string[]]$PrefixArgs = @())
  if (-not $Exe) { return $null }
  try {
    $resolved = (Get-Command $Exe -ErrorAction Stop).Source
    if ($resolved -like '*\WindowsApps\*') { return $null }
    $probe = & $resolved @PrefixArgs -c "import sys; print(sys.executable if sys.version_info >= (3, 11) else '')" 2>$null
    if ($LASTEXITCODE -eq 0 -and $probe -and (Test-Path -LiteralPath $probe.Trim())) {
      return $probe.Trim()
    }
  } catch {}
  return $null
}

function Find-Uv {
  $cmd = Get-Command uv -ErrorAction SilentlyContinue
  if ($cmd) { return $cmd.Source }
  foreach ($candidate in @(
    (Join-Path $env:LOCALAPPDATA 'AnYCLI\bootstrap\uv.exe'),
    (Join-Path $env:USERPROFILE '.local\bin\uv.exe'),
    (Join-Path $env:LOCALAPPDATA 'uv\uv.exe')
  )) {
    if (Test-Path -LiteralPath $candidate) { return $candidate }
  }
  return $null
}

function Find-Python311 {
  $py = Test-Python311 'py' @('-3.12')
  if ($py) { return $py }
  $py = Test-Python311 'py' @('-3.11')
  if ($py) { return $py }
  $py = Test-Python311 'py' @('-3')
  if ($py) { return $py }
  foreach ($cmd in @('python', 'python3')) {
    $py = Test-Python311 $cmd
    if ($py) { return $py }
  }
  foreach ($dir in @('Python313', 'Python312', 'Python311')) {
    $candidate = Join-Path $env:LOCALAPPDATA "Programs\Python\$dir\python.exe"
    if (Test-Path -LiteralPath $candidate) {
      $py = Test-Python311 $candidate
      if ($py) { return $py }
    }
  }
  $uv = Find-Uv
  if ($uv) {
    foreach ($ver in @('3.12', '3.11', '3.13')) {
      try {
        $found = & $uv python find $ver 2>$null
        if ($LASTEXITCODE -eq 0 -and $found) {
          $py = Test-Python311 $found.Trim()
          if ($py) { return $py }
        }
      } catch {}
    }
  }
  return $null
}

function Install-Uv {
  $ProgressPreference = 'SilentlyContinue'
  $cpu = $env:PROCESSOR_ARCHITEW6432
  if (-not $cpu) { $cpu = $env:PROCESSOR_ARCHITECTURE }
  $target = switch ($cpu) {
    'AMD64' { 'x86_64'; break }
    'ARM64' { 'aarch64'; break }
    'x86'   { 'i686'; break }
    default { throw "AnY CLI does not support this Windows architecture: $cpu" }
  }
  $sha256 = @{
    x86_64  = 'edd61f7f5728a56cc62455386661860bdfc7bab65872f39b0c25bdcc1d8e1beb'
    aarch64 = '72eed595983a4d7d22d79f21065b0f4479cc7e5c7a89104bb410c8f47559a878'
    i686    = 'eb4bd7285a512ebc4122f65a21b72e3f7072610d62164f43ca6aca280c39f6fd'
  }
  $asset = "uv-$target-pc-windows-msvc"
  $dest = Join-Path $env:LOCALAPPDATA 'AnYCLI\bootstrap'
  $exe = Join-Path $dest 'uv.exe'
  if (Test-Path -LiteralPath $exe -PathType Leaf) { return $exe }
  $work = Join-Path ([IO.Path]::GetTempPath()) ('any-uv-' + [Guid]::NewGuid())
  New-Item -ItemType Directory -Path $work | Out-Null
  try {
    $archive = Join-Path $work "$asset.zip"
    Invoke-WebRequest "https://releases.astral.sh/github/uv/releases/download/0.13.9/$asset.zip" `
      -UseBasicParsing -TimeoutSec 120 -OutFile $archive
    if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash -ne $sha256[$target]) {
      throw 'AnY CLI runtime checksum did not match. Please retry.'
    }
    Expand-Archive -LiteralPath $archive -DestinationPath $work
    $binary = @(Get-ChildItem -LiteralPath $work -Recurse -File -Filter 'uv.exe')
    if ($binary.Count -ne 1) { throw 'uv.exe is missing from the AnY CLI runtime archive.' }
    New-Item -ItemType Directory -Path $dest -Force | Out-Null
    $pending = Join-Path $dest ('uv-' + [Guid]::NewGuid() + '.tmp')
    try {
      Copy-Item -LiteralPath $binary[0].FullName -Destination $pending
      [IO.File]::Move($pending, $exe)
    } catch [IO.IOException] {
      if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) { throw }
    } finally {
      Remove-Item -LiteralPath $pending -Force -ErrorAction SilentlyContinue
    }
    return $exe
  } finally {
    Remove-Item -LiteralPath $work -Recurse -Force
  }
}

$installOnly = $args -contains '--install-only'
$pythonExe = if ($env:ANY_CLI_MANAGED_PYTHON -ne '1') { Find-Python311 }

if (-not $pythonExe) {
  Write-Host 'Preparing a standalone Python runtime for AnY CLI...'
  $uv = Find-Uv
  if (-not $uv) {
    $uv = Install-Uv
  }
  & $uv python install --no-bin --no-registry 3.12
  if ($LASTEXITCODE -ne 0) { throw 'Could not install the standalone Python 3.12 runtime.' }
  $pythonExe = & $uv python find --managed-python 3.12
  if ($LASTEXITCODE -ne 0 -or -not $pythonExe) { throw 'Could not find the installed Python 3.12 runtime.' }
  $pythonExe = $pythonExe.Trim()
}

$tmpPy = Join-Path $env:TEMP ("any-install-cli-" + [guid]::NewGuid().ToString('N') + '.py')
try {
  Invoke-WebRequest -UseBasicParsing -Uri ($BaseUrl + 'install-cli.py') -OutFile $tmpPy
  $launcher = & $pythonExe $tmpPy --print-launcher
  if ($LASTEXITCODE -ne 0 -or -not $launcher) { throw 'AnY CLI installation failed.' }
  $launcher = $launcher.Trim()
  $binDir = Split-Path -Parent $launcher
  $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
  $segments = @()
  if ($userPath) { $segments = $userPath -split ';' | Where-Object { $_ } }
  if ($env:ANY_CLI_MANAGED_PYTHON -ne '1' -and -not ($segments | Where-Object { $_.TrimEnd('\') -ieq $binDir.TrimEnd('\') })) {
    $newUserPath = if ($userPath) { "$userPath;$binDir" } else { $binDir }
    [Environment]::SetEnvironmentVariable('Path', $newUserPath, 'User')
  }
  if (-not (($env:Path -split ';') | Where-Object { $_.TrimEnd('\') -ieq $binDir.TrimEnd('\') })) {
    $env:Path = "$binDir;$env:Path"
  }
  Write-Host "AnY CLI installed. Run any or $launcher"
  if (-not $installOnly -and -not [Console]::IsInputRedirected) {
    & $launcher
  }
} finally {
  Remove-Item -LiteralPath $tmpPy -Force -ErrorAction SilentlyContinue
}
