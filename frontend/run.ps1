# Single build+preview+dev-run menu for the SFSIS frontend, merging the
# former repo-root build.ps1 + test.ps1 into one script living inside
# frontend/ (so it sits next to pyproject.toml, where frontend tooling
# actually belongs, instead of two separate scripts at the repo root).
# Named `run.ps1`/`run.sh` to match the sister senar project's own
# frontend/run.ps1 convention, so a dev who already knows that project
# recognizes this immediately. (This file replaces a stale, never-wired
# copy of senar's own run.ps1 that was accidentally committed here at
# the very first commit - it referenced setup_env.ps1/dev_reset.ps1/a
# .venv activation flow that never existed in this project.)
#
# `flet build`/`flet run`/`flet serve` (flet-cli, pinned via this
# project's [dependency-groups].dev = ["flet[all]==0.85.3"]) always
# produce a Flutter RELEASE build for `build` - there is no debug-mode
# flag in that command (a debug build instead comes from `flet run` on a
# connected device - see the Dev mode section below), so there is no
# separate "APK (Debug)" menu entry. Host-OS/target compatibility (e.g.
# iOS/macOS builds need a Mac) is validated by `flet build` itself, which
# prints its own build-matrix table and a clear error - this script
# doesn't duplicate that check.
#
# Behaviors ported from a full read-through of senar's own run.ps1:
# - `uv sync` before every build/dev-run.
# - APK preview searches both `build/apk` and flet-cli's raw Flutter
#   scaffold output (`build/flutter/build/app/outputs/flutter-apk`),
#   installing the newest by mtime.
# - `adb` discovery falls back through $env:ANDROID_HOME/
#   $env:ANDROID_SDK_ROOT/the default Android Studio SDK path, not PATH
#   only.
# - A persistent interactive menu: every selection (including a build, a
#   preview, or a dev-mode run that blocks until Ctrl+C) returns to the
#   menu afterwards when launched with no CLI arg, matching senar's own
#   `while ($true)` + "Press Enter to continue" loop exactly. A direct
#   CLI-arg invocation (`.\run.ps1 web`, scripting/CI use) still runs
#   once and exits.
$ErrorActionPreference = "Stop"

Set-Location -Path $PSScriptRoot
$FrontendDir = $PSScriptRoot
$BuildDir = Join-Path $FrontendDir "build"

# flet-cli's `rich`-based progress output writes Unicode glyphs (e.g. "●")
# that raise UnicodeEncodeError under a legacy cp1252 Windows console -
# confirmed live in PowerShell/Git Bash without this. Forcing UTF-8 I/O
# fixes it without needing the user to change their system codepage.
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$script:ExitCode = 0

$Targets = @(
    [PSCustomObject]@{ Category = "Build";   Number = "1";  Slug = "apk";                  Label = "APK (Release)" }
    [PSCustomObject]@{ Category = "Build";   Number = "2";  Slug = "apk-split";            Label = "APK (Release, split per ABI)" }
    [PSCustomObject]@{ Category = "Build";   Number = "3";  Slug = "aab";                  Label = "AAB (Android App Bundle)" }
    [PSCustomObject]@{ Category = "Build";   Number = "4";  Slug = "ios";                  Label = "iOS (IPA)" }
    [PSCustomObject]@{ Category = "Build";   Number = "5";  Slug = "ios-simulator";        Label = "iOS Simulator (.app)" }
    [PSCustomObject]@{ Category = "Build";   Number = "6";  Slug = "windows";              Label = "Windows desktop" }
    [PSCustomObject]@{ Category = "Build";   Number = "7";  Slug = "macos";                Label = "macOS desktop" }
    [PSCustomObject]@{ Category = "Build";   Number = "8";  Slug = "linux";                Label = "Linux desktop" }
    [PSCustomObject]@{ Category = "Build";   Number = "9";  Slug = "web";                  Label = "Web" }
    [PSCustomObject]@{ Category = "Preview"; Number = "10"; Slug = "preview-web";          Label = "Web (serve build/web locally)" }
    [PSCustomObject]@{ Category = "Preview"; Number = "11"; Slug = "preview-windows";      Label = "Windows desktop (launch built .exe)" }
    [PSCustomObject]@{ Category = "Preview"; Number = "12"; Slug = "preview-apk";          Label = "APK (install + launch on a connected device via adb)" }
    [PSCustomObject]@{ Category = "Preview"; Number = "13"; Slug = "preview-aab";          Label = "AAB (not directly previewable)" }
    [PSCustomObject]@{ Category = "Preview"; Number = "14"; Slug = "preview-ios";          Label = "iOS / IPA (not directly previewable)" }
    [PSCustomObject]@{ Category = "Preview"; Number = "15"; Slug = "preview-ios-simulator"; Label = "iOS Simulator (macOS/Xcode only)" }
    [PSCustomObject]@{ Category = "Dev mode"; Number = "16"; Slug = "dev-desktop";         Label = "Desktop (flet run, hot reload)" }
    [PSCustomObject]@{ Category = "Dev mode"; Number = "17"; Slug = "dev-web";             Label = "Web (flet run --web, hot reload)" }
    [PSCustomObject]@{ Category = "Dev mode"; Number = "18"; Slug = "dev-android";         Label = "Android (scan QR with Flet app - no SDK needed)" }
    [PSCustomObject]@{ Category = "Dev mode"; Number = "19"; Slug = "dev-ios";             Label = "iOS (scan QR with Flet app - no Xcode needed)" }
)

function Show-Menu {
    Write-Host ""
    Write-Host "SFSIS frontend" -ForegroundColor Cyan
    Write-Host "==============" -ForegroundColor Cyan
    $lastCategory = $null
    foreach ($t in $Targets) {
        if ($t.Category -ne $lastCategory) {
            Write-Host ""
            Write-Host "$($t.Category):" -ForegroundColor Yellow
            $lastCategory = $t.Category
        }
        Write-Host ("  {0}) {1}" -f $t.Number, $t.Label)
    }
    Write-Host ""
    Write-Host "  0) Exit"
    Write-Host ""
}

function Test-Uv {
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        return $true
    }
    Write-Host "'uv' was not found on PATH. Install it from https://docs.astral.sh/uv, then re-run this script." -ForegroundColor Red
    $script:ExitCode = 1
    return $false
}

function Get-AdbPath {
    # Same discovery order as senar's own run.ps1 Install-Android-WithAdb -
    # PATH first, then $env:ANDROID_HOME/$env:ANDROID_SDK_ROOT, then the
    # default Android Studio SDK install location (confirmed live: adb.exe
    # can genuinely exist there without ever being on PATH).
    $cmd = Get-Command adb -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }
    $candidates = @()
    if ($env:ANDROID_HOME) {
        $candidates += (Join-Path $env:ANDROID_HOME "platform-tools\adb.exe")
    }
    if ($env:ANDROID_SDK_ROOT) {
        $candidates += (Join-Path $env:ANDROID_SDK_ROOT "platform-tools\adb.exe")
    }
    if ($env:LOCALAPPDATA) {
        $candidates += (Join-Path $env:LOCALAPPDATA "Android\Sdk\platform-tools\adb.exe")
    }
    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path $candidate)) {
            return $candidate
        }
    }
    return $null
}

function Get-AndroidPackageId {
    # `[tool.flet]` org + `[project]` name build the Android/iOS bundle ID
    # the same way flet-cli itself does - parsed here instead of
    # hardcoded so this stays correct if either value ever changes.
    $pyproject = Join-Path $FrontendDir "pyproject.toml"
    $content = Get-Content -Path $pyproject -Raw
    $org = [regex]::Match($content, 'org\s*=\s*"([^"]+)"').Groups[1].Value
    $name = [regex]::Match($content, '(?m)^name\s*=\s*"([^"]+)"').Groups[1].Value
    if (-not $org -or -not $name) {
        return $null
    }
    return "$org.$name"
}

function Invoke-BuildTarget([string]$Slug, [string]$Label, [string[]]$ExtraArgs) {
    if (-not (Test-Uv)) { return }
    & uv sync
    Write-Host "Building $Label..." -ForegroundColor Green
    & uv run flet build $Slug @ExtraArgs
    $script:ExitCode = $LASTEXITCODE
}

function Invoke-PreviewWeb {
    $webDir = Join-Path $BuildDir "web"
    if (-not (Test-Path $webDir)) {
        Write-Host "No web build found at $webDir - build it first (option 9)." -ForegroundColor Red
        $script:ExitCode = 1
        return
    }
    if (-not (Test-Uv)) { return }
    & uv run flet serve "build/web"
    $script:ExitCode = $LASTEXITCODE
}

function Invoke-PreviewDesktop {
    $winDir = Join-Path $BuildDir "windows"
    if (-not (Test-Path $winDir)) {
        Write-Host "No Windows build found at $winDir - build it first (option 6)." -ForegroundColor Red
        $script:ExitCode = 1
        return
    }
    $exe = Get-ChildItem -Path $winDir -Filter "*.exe" -File | Select-Object -First 1
    if (-not $exe) {
        Write-Host "No .exe found under $winDir - the build may be incomplete; try rebuilding (option 6)." -ForegroundColor Red
        $script:ExitCode = 1
        return
    }
    Write-Host "Launching $($exe.FullName)..." -ForegroundColor Green
    Start-Process -FilePath $exe.FullName
}

function Invoke-PreviewApk {
    # Searches both the final `build/apk` output AND flet-cli's raw
    # Flutter scaffold output (`build/flutter/build/app/outputs/
    # flutter-apk`) - ported from senar's own Install-Android-WithAdb.
    # Confirmed real by reading flet-cli's build_base.py: `flutter_dir =
    # build_dir/flutter`, and the apk target's own `outputs` glob is
    # relative to that - so a build interrupted after Flutter finishes
    # but before flet-cli's own final copy step leaves a usable APK there
    # that would otherwise go unfound.
    $apkDir = Join-Path $BuildDir "apk"
    $flutterApkDir = Join-Path $BuildDir "flutter\build\app\outputs\flutter-apk"
    $apks = @()
    if (Test-Path $apkDir) {
        $apks += Get-ChildItem -Path $apkDir -Filter "*.apk" -File -ErrorAction SilentlyContinue
    }
    if (Test-Path $flutterApkDir) {
        $apks += Get-ChildItem -Path $flutterApkDir -Filter "*.apk" -File -ErrorAction SilentlyContinue
    }
    if ($apks.Count -eq 0) {
        Write-Host "No .apk found under $apkDir or $flutterApkDir - build one first (option 1 or 2)." -ForegroundColor Red
        $script:ExitCode = 1
        return
    }
    # Newest first - picking an arbitrary filesystem-enumeration-order
    # match could otherwise install a stale APK from an earlier build.
    $apks = $apks | Sort-Object LastWriteTime -Descending

    $adbPath = Get-AdbPath
    if (-not $adbPath) {
        Write-Host ""
        Write-Host "'adb' was not found on PATH, `$env:ANDROID_HOME, `$env:ANDROID_SDK_ROOT, or the default Android Studio SDK location - install the Android SDK platform-tools to enable automatic install+launch." -ForegroundColor Yellow
        Write-Host "Manual install: connect a device/emulator, then run:"
        foreach ($apk in $apks) {
            Write-Host "  adb install -r `"$($apk.FullName)`""
        }
        return
    }

    $devices = & $adbPath devices | Select-Object -Skip 1 | Where-Object { $_ -match "\tdevice$" }
    if (-not $devices) {
        Write-Host "No connected/authorized Android device or emulator found (checked via 'adb devices'). Connect one and re-run." -ForegroundColor Red
        $script:ExitCode = 1
        return
    }

    $target = $apks | Select-Object -First 1
    if ($apks.Count -gt 1) {
        Write-Host "Multiple APKs found - installing the newest one ($($target.Name)):"
        $apks | ForEach-Object { Write-Host "  $($_.Name)  ($($_.LastWriteTime))" }
    }

    Write-Host "Installing $($target.Name)..." -ForegroundColor Green
    & $adbPath install -r $target.FullName
    if ($LASTEXITCODE -ne 0) {
        Write-Host "adb install failed (exit $LASTEXITCODE)." -ForegroundColor Red
        $script:ExitCode = $LASTEXITCODE
        return
    }

    $package = Get-AndroidPackageId
    if ($package) {
        Write-Host "Launching $package..." -ForegroundColor Green
        & $adbPath shell monkey -p $package -c android.intent.category.LAUNCHER 1 | Out-Null
    } else {
        Write-Host "Installed successfully - could not determine the package id to auto-launch; open it manually on the device."
    }
}

function Invoke-NotApplicable([string]$Label, [string]$Reason) {
    Write-Host ""
    Write-Host "$Label cannot be previewed by this script:" -ForegroundColor Yellow
    Write-Host "  $Reason"
    Write-Host ""
}

function Invoke-DevRun([string[]]$FletRunArgs) {
    if (-not (Test-Uv)) { return }
    # `flet run` (dev-mode runner) lives in flet-cli, same as `flet
    # build`/`flet serve` - only in the dev dependency group (see
    # pyproject.toml's own comment on why bare `flet` excludes it).
    & uv sync
    Write-Host "Starting Flet with hot reload (Ctrl+C to stop)..." -ForegroundColor Green
    & uv run flet run -r @FletRunArgs
    $script:ExitCode = $LASTEXITCODE
}

function Invoke-Selection([string]$Choice) {
    # Returns $true to keep looping (interactive mode only), $false for
    # Exit. Every branch returns to the caller instead of calling `exit`
    # directly - matches senar's own persistent-menu convention, where
    # even a blocking dev-run (Ctrl+C to stop) returns to the menu
    # afterwards rather than ending the whole session.
    if ([string]::IsNullOrWhiteSpace($Choice) -or $Choice -eq "0") {
        return $false
    }

    $selected = $Targets | Where-Object { $_.Number -eq $Choice -or $_.Slug -eq $Choice } | Select-Object -First 1
    if (-not $selected) {
        Write-Host "Unknown option: $Choice" -ForegroundColor Red
        $script:ExitCode = 1
        return $true
    }

    switch ($selected.Slug) {
        "apk" { Invoke-BuildTarget "apk" $selected.Label @() }
        "apk-split" { Invoke-BuildTarget "apk" $selected.Label @("--split-per-abi") }
        "aab" { Invoke-BuildTarget "aab" $selected.Label @() }
        "ios" { Invoke-BuildTarget "ipa" $selected.Label @() }
        "ios-simulator" { Invoke-BuildTarget "ios-simulator" $selected.Label @() }
        "windows" { Invoke-BuildTarget "windows" $selected.Label @() }
        "macos" { Invoke-BuildTarget "macos" $selected.Label @() }
        "linux" { Invoke-BuildTarget "linux" $selected.Label @() }
        "web" { Invoke-BuildTarget "web" $selected.Label @() }
        "preview-web" { Invoke-PreviewWeb }
        "preview-windows" { Invoke-PreviewDesktop }
        "preview-apk" { Invoke-PreviewApk }
        "preview-aab" { Invoke-NotApplicable "AAB" "Android App Bundles aren't directly installable. Upload to Play Console (internal testing track), or use Google's 'bundletool' to generate installable APKs from it. Use the APK preview option instead for local testing." }
        "preview-ios" { Invoke-NotApplicable "iOS / IPA" "IPA files need a provisioning profile, a registered device, or TestFlight to install - not something this script can automate. On macOS, use Xcode's Devices and Simulators window, or 'xcrun devicectl'." }
        "preview-ios-simulator" { Invoke-NotApplicable "iOS Simulator" "The iOS Simulator only runs on macOS with Xcode installed - not available on this host." }
        "dev-desktop" { Invoke-DevRun @() }
        "dev-web" { Invoke-DevRun @("--web") }
        "dev-android" { Invoke-DevRun @("--android") }
        "dev-ios" { Invoke-DevRun @("--ios") }
    }
    return $true
}

$cliChoice = $args[0]
if ($null -ne $cliChoice) {
    # NOTE: deliberately `$null -ne`, not `-not $choice`/truthiness -
    # PowerShell's string-to-bool coercion treats the *string* "0" as
    # falsy (confirmed live: `-not "0"` is `$true`), which would wrongly
    # treat a CLI-arg "0" (Exit) the same as "no argument given".
    if (-not (Invoke-Selection $cliChoice)) {
        Write-Host "Cancelled."
    }
    exit $script:ExitCode
}

while ($true) {
    Show-Menu
    $choice = Read-Host "Select an option (number or name, 0 to exit)"
    Write-Host ""
    if (-not (Invoke-Selection $choice)) {
        Write-Host "Goodbye!"
        exit 0
    }
    Write-Host ""
    Read-Host "Press Enter to continue..." | Out-Null
}
