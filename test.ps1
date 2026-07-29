# Interactive menu to run/preview the frontend (issue #67), two ways:
#   1-6: preview a build already produced by build.ps1 - serves the web
#        bundle, launches a built desktop executable, or installs an APK
#        to a connected device via adb. Does NOT build anything itself -
#        run build.ps1 first for whichever target you want to preview.
#   7-9: dev mode - `uv run flet run [-r]`, running the app directly from
#        source with hot reload, no build step at all. `--android`/`--ios`
#        print a QR code (scanned with the phone's Camera app) that opens
#        the free "Flet" companion app (App Store/Play Store), which
#        connects back over the LAN and renders the live UI - confirmed by
#        reading flet-cli's own run.py (`print_qr_code`/`flet://`,
#        `https://android.flet.dev/...`). This needs NO Xcode/macOS and NO
#        Android SDK - it's a genuinely different, much lighter mechanism
#        than options 3/5/6 above (which preview a *compiled* `flet build`
#        artifact, where the Xcode/macOS requirement for iOS is real).
#        Same convention as senar's own `run.ps1` Test-Desktop/-Web/
#        -Android/-Ios functions.
$ErrorActionPreference = "Stop"

Set-Location -Path $PSScriptRoot

# Same Windows-console UnicodeEncodeError workaround as build.ps1 - `flet
# serve`'s own `rich` console can hit it too.
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$FrontendDir = Join-Path $PSScriptRoot "frontend"
$BuildDir = Join-Path $FrontendDir "build"

function Get-AndroidPackageId {
    # `[tool.flet]` org + `[project]` name build the Android/iOS bundle ID
    # the same way flet-cli itself does (see frontend/pyproject.toml's own
    # [tool.flet] comment) - parsed here instead of hardcoded so this stays
    # correct if either value ever changes.
    $pyproject = Join-Path $FrontendDir "pyproject.toml"
    $content = Get-Content -Path $pyproject -Raw
    $org = [regex]::Match($content, 'org\s*=\s*"([^"]+)"').Groups[1].Value
    $name = [regex]::Match($content, '(?m)^name\s*=\s*"([^"]+)"').Groups[1].Value
    if (-not $org -or -not $name) {
        return $null
    }
    return "$org.$name"
}

function Invoke-Web {
    $webDir = Join-Path $BuildDir "web"
    if (-not (Test-Path $webDir)) {
        Write-Error "No web build found at $webDir - run '.\build.ps1 web' first."
        exit 1
    }
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        Write-Error "'uv' was not found on PATH. Install it from https://docs.astral.sh/uv, then re-run this script."
        exit 1
    }
    Set-Location -Path $FrontendDir
    & uv run flet serve "build/web"
    exit $LASTEXITCODE
}

function Invoke-Desktop {
    $winDir = Join-Path $BuildDir "windows"
    if (-not (Test-Path $winDir)) {
        Write-Error "No Windows build found at $winDir - run '.\build.ps1 windows' first."
        exit 1
    }
    $exe = Get-ChildItem -Path $winDir -Filter "*.exe" -File | Select-Object -First 1
    if (-not $exe) {
        Write-Error "No .exe found under $winDir - the build may be incomplete; try rebuilding with '.\build.ps1 windows'."
        exit 1
    }
    Write-Host "Launching $($exe.FullName)..."
    Start-Process -FilePath $exe.FullName
}

function Invoke-Apk {
    $apkDir = Join-Path $BuildDir "apk"
    if (-not (Test-Path $apkDir)) {
        Write-Error "No APK build found at $apkDir - run '.\build.ps1 apk' (or 'apk-split') first."
        exit 1
    }
    $apks = Get-ChildItem -Path $apkDir -Filter "*.apk" -File
    if ($apks.Count -eq 0) {
        Write-Error "No .apk found under $apkDir - the build may be incomplete; try rebuilding."
        exit 1
    }

    if (-not (Get-Command adb -ErrorAction SilentlyContinue)) {
        Write-Host ""
        Write-Host "'adb' was not found on PATH - install the Android SDK platform-tools to enable automatic install+launch."
        Write-Host "Manual install: connect a device/emulator, then run:"
        foreach ($apk in $apks) {
            Write-Host "  adb install -r `"$($apk.FullName)`""
        }
        exit 0
    }

    $devices = & adb devices | Select-Object -Skip 1 | Where-Object { $_ -match "\tdevice$" }
    if (-not $devices) {
        Write-Error "No connected/authorized Android device or emulator found (checked via 'adb devices'). Connect one and re-run."
        exit 1
    }

    $target = $apks | Select-Object -First 1
    if ($apks.Count -gt 1) {
        Write-Host "Multiple APKs found (split-per-abi build) - installing the first one:"
        $apks | ForEach-Object { Write-Host "  $($_.Name)" }
    }

    Write-Host "Installing $($target.Name)..."
    & adb install -r $target.FullName
    if ($LASTEXITCODE -ne 0) {
        Write-Error "adb install failed (exit $LASTEXITCODE)."
        exit $LASTEXITCODE
    }

    $package = Get-AndroidPackageId
    if ($package) {
        Write-Host "Launching $package..."
        & adb shell monkey -p $package -c android.intent.category.LAUNCHER 1 | Out-Null
    } else {
        Write-Host "Installed successfully - could not determine the package id to auto-launch; open it manually on the device."
    }
}

function Invoke-NotApplicable([string]$label, [string]$reason) {
    Write-Host ""
    Write-Host "$label cannot be previewed by this script:"
    Write-Host "  $reason"
    Write-Host ""
}

function Invoke-DevRun([string[]]$FletRunArgs) {
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        Write-Error "'uv' was not found on PATH. Install it from https://docs.astral.sh/uv, then re-run this script."
        exit 1
    }
    Set-Location -Path $FrontendDir
    # `flet run` (the dev-mode runner) lives in flet-cli, same as `flet
    # build`/`flet serve` - only in the dev dependency group (see
    # pyproject.toml's own comment on why bare `flet` excludes it). `uv
    # sync` here (default group set, i.e. including dev) matches senar's
    # own run.ps1 convention of syncing before every dev-mode run.
    & uv sync
    Write-Host "Starting Flet with hot reload (Ctrl+C to stop)..."
    & uv run flet run -r @FletRunArgs
    exit $LASTEXITCODE
}

$Targets = @(
    [PSCustomObject]@{ Number = "1"; Slug = "web";     Label = "Web (serve build/web locally)" }
    [PSCustomObject]@{ Number = "2"; Slug = "windows";  Label = "Windows desktop (launch built .exe)" }
    [PSCustomObject]@{ Number = "3"; Slug = "apk";      Label = "APK (install + launch on a connected device via adb)" }
    [PSCustomObject]@{ Number = "4"; Slug = "aab";      Label = "AAB (not directly previewable)" }
    [PSCustomObject]@{ Number = "5"; Slug = "ios";      Label = "iOS / IPA (not directly previewable)" }
    [PSCustomObject]@{ Number = "6"; Slug = "ios-simulator"; Label = "iOS Simulator (macOS/Xcode only)" }
    [PSCustomObject]@{ Number = "7"; Slug = "dev-desktop"; Label = "Dev mode: Desktop (flet run, hot reload)" }
    [PSCustomObject]@{ Number = "8"; Slug = "dev-web";     Label = "Dev mode: Web (flet run --web, hot reload)" }
    [PSCustomObject]@{ Number = "9"; Slug = "dev-android"; Label = "Dev mode: Android (scan QR with Flet app - no SDK needed)" }
    [PSCustomObject]@{ Number = "10"; Slug = "dev-ios";     Label = "Dev mode: iOS (scan QR with Flet app - no Xcode needed)" }
)

function Show-Menu {
    Write-Host ""
    Write-Host "SFSIS frontend test/preview"
    Write-Host "============================"
    foreach ($t in $Targets) {
        Write-Host ("  {0}) {1}" -f $t.Number, $t.Label)
    }
    Write-Host "  0) Cancel"
    Write-Host ""
}

$choice = $args[0]
if ($null -eq $choice) {
    # See build.ps1's own note on why this must be `$null -eq $choice`,
    # not `-not $choice` - PowerShell treats the string "0" as falsy.
    Show-Menu
    $choice = Read-Host "Select a target (number or name)"
}

if ([string]::IsNullOrWhiteSpace($choice) -or $choice -eq "0") {
    Write-Host "Cancelled."
    exit 0
}

$selected = $Targets | Where-Object { $_.Number -eq $choice -or $_.Slug -eq $choice } | Select-Object -First 1
if (-not $selected) {
    Write-Error "Unknown preview target: $choice"
    exit 1
}

switch ($selected.Slug) {
    "web" { Invoke-Web }
    "windows" { Invoke-Desktop }
    "apk" { Invoke-Apk }
    "aab" { Invoke-NotApplicable "AAB" "Android App Bundles aren't directly installable. Upload to Play Console (internal testing track), or use Google's 'bundletool' to generate installable APKs from it. Use the APK preview option instead for local testing." }
    "ios" { Invoke-NotApplicable "iOS / IPA" "IPA files need a provisioning profile, a registered device, or TestFlight to install - not something this script can automate. On macOS, use Xcode's Devices and Simulators window, or 'xcrun devicectl'." }
    "ios-simulator" { Invoke-NotApplicable "iOS Simulator" "The iOS Simulator only runs on macOS with Xcode installed - not available on this host." }
    "dev-desktop" { Invoke-DevRun @() }
    "dev-web" { Invoke-DevRun @("--web") }
    "dev-android" { Invoke-DevRun @("--android") }
    "dev-ios" { Invoke-DevRun @("--ios") }
}
