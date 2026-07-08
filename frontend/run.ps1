function Write-Title {
  param([string]$Message)
  Write-Host "`n$Message" -ForegroundColor Cyan
  Write-Host ("=" * $Message.Length) -ForegroundColor Cyan
}

$color = 'White'
Write-Host ("{0,-30} | {1,-10} | {2,-10}" -f $tableName, $devCount, $prodCount) -ForegroundColor $color
if ($devCount -gt 0 -or $prodCount -gt 0) {
  Write-Host "  Column differences:" -ForegroundColor Yellow
  Compare-Column $tableName
}
elseif ($devCount -eq 0 -and $prodCount -eq 0) {
  Write-Host "No columns found on either server for table '$tableName'." -ForegroundColor Yellow
}


function Test-Desktop {
  # Ensure scripts are resolved relative to this script's location
  if (-not $env:VIRTUAL_ENV) {
    if (Test-Path "$PSScriptRoot\setup_env.ps1") { . "$PSScriptRoot\setup_env.ps1" } else { Write-Host "setup_env.ps1 not found, skipping setup." -ForegroundColor Yellow }
    $activatePath = Join-Path $PSScriptRoot '.venv\Scripts\Activate.ps1'
    if (Test-Path $activatePath) {
      try { . $activatePath } catch { Write-Host "Failed to activate virtualenv: $activatePath`n$_" -ForegroundColor Red }
    } else {
      Write-Host "Activate script not found at $activatePath. If virtualenv exists, activate it manually." -ForegroundColor Yellow
    }
  }
  & uv sync
  Write-Host "Starting Flet with hot reload (watching all files recursively)..." -ForegroundColor Green
  & uv run flet run -r
}

function Test-Web {
  if (-not $env:VIRTUAL_ENV) {
    if (Test-Path "$PSScriptRoot\setup_env.ps1") { . "$PSScriptRoot\setup_env.ps1" } else { Write-Host "setup_env.ps1 not found, skipping setup." -ForegroundColor Yellow }
    $activatePath = Join-Path $PSScriptRoot '.venv\Scripts\Activate.ps1'
    if (Test-Path $activatePath) { try { . $activatePath } catch { Write-Host "Failed to activate virtualenv: $activatePath`n$_" -ForegroundColor Red } } else { Write-Host "Activate script not found at $activatePath. If virtualenv exists, activate it manually." -ForegroundColor Yellow }
  }
  & uv sync
  Write-Host "Starting Flet web with hot reload (watching all files recursively)..." -ForegroundColor Green
  & uv run flet run --web --port 8811 -r
}
function Test-Android {
  if (-not $env:VIRTUAL_ENV) {
    if (Test-Path "$PSScriptRoot\setup_env.ps1") { . "$PSScriptRoot\setup_env.ps1" } else { Write-Host "setup_env.ps1 not found, skipping setup." -ForegroundColor Yellow }
    $activatePath = Join-Path $PSScriptRoot '.venv\Scripts\Activate.ps1'
    if (Test-Path $activatePath) { try { . $activatePath } catch { Write-Host "Failed to activate virtualenv: $activatePath`n$_" -ForegroundColor Red } } else { Write-Host "Activate script not found at $activatePath. If virtualenv exists, activate it manually." -ForegroundColor Yellow }
  }
  & uv sync
  & uv run flet run --android -r
}

function Test-Ios {
  if (-not $env:VIRTUAL_ENV) {
    if (Test-Path "$PSScriptRoot\setup_env.ps1") { . "$PSScriptRoot\setup_env.ps1" } else { Write-Host "setup_env.ps1 not found, skipping setup." -ForegroundColor Yellow }
    $activatePath = Join-Path $PSScriptRoot '.venv\Scripts\Activate.ps1'
    if (Test-Path $activatePath) { try { . $activatePath } catch { Write-Host "Failed to activate virtualenv: $activatePath`n$_" -ForegroundColor Red } } else { Write-Host "Activate script not found at $activatePath. If virtualenv exists, activate it manually." -ForegroundColor Yellow }
  }
  & uv sync
  & uv run flet run --ios -r
}

function Build-Android {
  if (-not $env:VIRTUAL_ENV) {
    if (Test-Path "$PSScriptRoot\setup_env.ps1") { . "$PSScriptRoot\setup_env.ps1" } else { Write-Host "setup_env.ps1 not found, skipping setup." -ForegroundColor Yellow }
    $activatePath = Join-Path $PSScriptRoot '.venv\Scripts\Activate.ps1'
    if (Test-Path $activatePath) { try { . $activatePath } catch { Write-Host "Failed to activate virtualenv: $activatePath`n$_" -ForegroundColor Red } } else { Write-Host "Activate script not found at $activatePath. If virtualenv exists, activate it manually." -ForegroundColor Yellow }
  }
  & uv sync
  & uv run flet build apk
}

function Install-Android-WithAdb {
  $adbExe = $null
  $adbCmd = Get-Command adb -ErrorAction SilentlyContinue
  if ($adbCmd) {
    $adbExe = $adbCmd.Source
  }
  else {
    $adbCandidates = @()

    if ($env:ANDROID_HOME) {
      $adbCandidates += (Join-Path $env:ANDROID_HOME "platform-tools\adb.exe")
    }
    if ($env:ANDROID_SDK_ROOT) {
      $adbCandidates += (Join-Path $env:ANDROID_SDK_ROOT "platform-tools\adb.exe")
    }
    if ($env:LOCALAPPDATA) {
      $adbCandidates += (Join-Path $env:LOCALAPPDATA "Android\Sdk\platform-tools\adb.exe")
    }

    foreach ($candidate in $adbCandidates) {
      if ($candidate -and (Test-Path $candidate)) {
        $adbExe = $candidate
        break
      }
    }
  }

  if (-not $adbExe) {
    Write-Host "adb not found. Install Android platform-tools or set ANDROID_SDK_ROOT/ANDROID_HOME." -ForegroundColor Red
    Write-Host "Expected adb location example: $env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe" -ForegroundColor Yellow
    return
  }

  $adbOutput = & $adbExe devices
  $connectedDevices = $adbOutput | Select-Object -Skip 1 | Where-Object {
    $_.Trim() -ne "" -and $_ -match "\tdevice$"
  }

  if (-not $connectedDevices -or $connectedDevices.Count -eq 0) {
    Write-Host "No connected Android device detected. Enable USB debugging and reconnect your phone." -ForegroundColor Yellow
    return
  }

  $apkCandidates = @()
  $buildApkDir = Join-Path $PSScriptRoot "build\apk"
  if (Test-Path $buildApkDir) {
    $apkCandidates += Get-ChildItem -Path $buildApkDir -Filter *.apk -Recurse -File -ErrorAction SilentlyContinue
  }

  $flutterApkDir = Join-Path $PSScriptRoot "build\flutter\build\app\outputs\flutter-apk"
  if (Test-Path $flutterApkDir) {
    $apkCandidates += Get-ChildItem -Path $flutterApkDir -Filter *.apk -Recurse -File -ErrorAction SilentlyContinue
  }

  if (-not $apkCandidates -or $apkCandidates.Count -eq 0) {
    Write-Host "No APK found. Please run option 5 (Build Android) first." -ForegroundColor Yellow
    return
  }

  $apkPath = ($apkCandidates | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName
  Write-Host "Installing APK: $apkPath" -ForegroundColor Green
  & $adbExe install -r "$apkPath"

  if ($LASTEXITCODE -eq 0) {
    Write-Host "APK installed successfully." -ForegroundColor Green
  }
  else {
    Write-Host "APK installation failed. Check device connection and ADB output above." -ForegroundColor Red
  }
}

function Show-Menu {
  Write-Title "🗃️  SFSIS Mobile Companion Application"
  Write-Host ""
  Write-Host "📋 Available Actions:" -ForegroundColor Yellow
  Write-Host ""
  Write-Host "  1: 🚀 Testing Desktop"
  Write-Host "  2: 📊 Testing Web Port 8811"
  Write-Host "  3: 📊 Testing Android"
  Write-Host "  4: 📊 Testing iOS"
  Write-Host "  5: 📊 Build Android"
  Write-Host "  6: 📱 Install Android with ADB"
  Write-Host "  7: 🧹 Dev Reset (clear pycache + app storage)"
  Write-Host "  q: ❌ Exit"
  Write-Host ""
}

while ($true) {
  Show-Menu
  $choice = Read-Host "Please select"
  Write-Host ""
  if ($choice -eq "q") {
    Write-Host "👋 Goodbye!"
    exit
  }
  switch ($choice) {
    "1" { Test-Desktop }
    "2" { Test-Web }
    "3" { Test-Android }
    "4" { Test-Ios }
    "5" { Build-Android }
    "6" { Install-Android-WithAdb }
    "7" { & (Join-Path $PSScriptRoot "dev_reset.ps1") }
    default { Write-Host "❌ Invalid option: $choice" -ForegroundColor Red }
  }
  Write-Host ""
  Read-Host "Press Enter to continue..."
}