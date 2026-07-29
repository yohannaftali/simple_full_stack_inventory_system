# Interactive menu wrapping `uv run flet build <target>` (issue #66) -
# produces a native/non-Docker build of the frontend (mobile/desktop/web),
# alongside the existing containerized web deployment (start.ps1/start.sh).
#
# `flet build` (flet-cli, pinned via frontend/pyproject.toml's
# [dependency-groups].dev = ["flet[all]==0.85.3"]) always produces a
# Flutter RELEASE build - there is no debug-mode flag in this CLI (a debug
# build instead comes from `flet run` on a connected device, out of scope
# here), so there is no separate "APK (Debug)" menu entry.
#
# Host-OS/target compatibility (e.g. iOS/macOS builds need a Mac) is
# validated by `flet build` itself, which prints its own build-matrix
# table and a clear error - this script does not duplicate that check.
$ErrorActionPreference = "Stop"

Set-Location -Path $PSScriptRoot

# flet-cli's `rich`-based progress output writes Unicode glyphs (e.g. "●")
# that raise UnicodeEncodeError under a legacy cp1252 Windows console -
# confirmed live in PowerShell/Git Bash without this. Forcing UTF-8 I/O
# fixes it without needing the user to change their system codepage.
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$Targets = @(
    [PSCustomObject]@{ Number = "1"; Slug = "apk";           Label = "APK (Release)";               FletTarget = "apk";           ExtraArgs = @() }
    [PSCustomObject]@{ Number = "2"; Slug = "apk-split";      Label = "APK (Release, split per ABI)"; FletTarget = "apk";           ExtraArgs = @("--split-per-abi") }
    [PSCustomObject]@{ Number = "3"; Slug = "aab";            Label = "AAB (Android App Bundle)";     FletTarget = "aab";           ExtraArgs = @() }
    [PSCustomObject]@{ Number = "4"; Slug = "ios";            Label = "iOS (IPA)";                    FletTarget = "ipa";           ExtraArgs = @() }
    [PSCustomObject]@{ Number = "5"; Slug = "ios-simulator";  Label = "iOS Simulator (.app)";         FletTarget = "ios-simulator"; ExtraArgs = @() }
    [PSCustomObject]@{ Number = "6"; Slug = "windows";        Label = "Windows desktop";              FletTarget = "windows";       ExtraArgs = @() }
    [PSCustomObject]@{ Number = "7"; Slug = "macos";          Label = "macOS desktop";                FletTarget = "macos";         ExtraArgs = @() }
    [PSCustomObject]@{ Number = "8"; Slug = "linux";          Label = "Linux desktop";                FletTarget = "linux";         ExtraArgs = @() }
    [PSCustomObject]@{ Number = "9"; Slug = "web";            Label = "Web";                          FletTarget = "web";           ExtraArgs = @() }
)

function Show-Menu {
    Write-Host ""
    Write-Host "SFSIS frontend build"
    Write-Host "====================="
    foreach ($t in $Targets) {
        Write-Host ("  {0}) {1}" -f $t.Number, $t.Label)
    }
    Write-Host "  0) Cancel"
    Write-Host ""
}

$choice = $args[0]
if ($null -eq $choice) {
    # NOTE: deliberately not `-not $choice` - PowerShell's string-to-bool
    # coercion treats the *string* "0" as falsy (confirmed live:
    # `-not "0"` is `$true`), which would wrongly treat a CLI-arg "0"
    # (Cancel) the same as "no argument given" and fall through to the
    # interactive prompt instead of cancelling immediately.
    Show-Menu
    $choice = Read-Host "Select a target (number or name)"
}

if ([string]::IsNullOrWhiteSpace($choice) -or $choice -eq "0") {
    Write-Host "Cancelled."
    exit 0
}

$selected = $Targets | Where-Object { $_.Number -eq $choice -or $_.Slug -eq $choice } | Select-Object -First 1
if (-not $selected) {
    Write-Error "Unknown build target: $choice"
    exit 1
}

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Error "'uv' was not found on PATH. Install it from https://docs.astral.sh/uv, then re-run this script."
    exit 1
}

Write-Host "Building $($selected.Label)..."
Set-Location -Path (Join-Path $PSScriptRoot "frontend")
& uv run flet build $selected.FletTarget @($selected.ExtraArgs)
exit $LASTEXITCODE
