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
# project's [dependency-groups].dev = ["flet[all]==0.86.4"]) always
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
    [PSCustomObject]@{ Category = "Build";   Number = "2";  Slug = "apk-debug";            Label = "APK (Debug)" }
    [PSCustomObject]@{ Category = "Build";   Number = "3";  Slug = "apk-split";            Label = "APK (Release, split per ABI)" }
    [PSCustomObject]@{ Category = "Build";   Number = "4";  Slug = "aab";                  Label = "AAB (Android App Bundle)" }
    [PSCustomObject]@{ Category = "Build";   Number = "5";  Slug = "ios";                  Label = "iOS (IPA)" }
    [PSCustomObject]@{ Category = "Build";   Number = "6";  Slug = "ios-simulator";        Label = "iOS Simulator (.app)" }
    [PSCustomObject]@{ Category = "Build";   Number = "7";  Slug = "windows";              Label = "Windows desktop" }
    [PSCustomObject]@{ Category = "Build";   Number = "8";  Slug = "macos";                Label = "macOS desktop" }
    [PSCustomObject]@{ Category = "Build";   Number = "9";  Slug = "linux";                Label = "Linux desktop" }
    [PSCustomObject]@{ Category = "Build";   Number = "10"; Slug = "web";                  Label = "Web" }
    [PSCustomObject]@{ Category = "Preview"; Number = "11"; Slug = "preview-web";          Label = "Web (serve build/web locally)" }
    [PSCustomObject]@{ Category = "Preview"; Number = "12"; Slug = "preview-desktop";      Label = "Windows desktop (launch built .exe)" }
    [PSCustomObject]@{ Category = "Preview"; Number = "13"; Slug = "preview-apk";          Label = "APK (install + launch on a connected device via adb)" }
    [PSCustomObject]@{ Category = "Preview"; Number = "14"; Slug = "preview-aab";          Label = "AAB (not directly previewable)" }
    [PSCustomObject]@{ Category = "Preview"; Number = "15"; Slug = "preview-ios";          Label = "iOS / IPA (not directly previewable)" }
    [PSCustomObject]@{ Category = "Preview"; Number = "16"; Slug = "preview-ios-simulator"; Label = "iOS Simulator (macOS/Xcode only)" }
    [PSCustomObject]@{ Category = "Dev mode"; Number = "17"; Slug = "dev-desktop";         Label = "Desktop (flet run, hot reload)" }
    [PSCustomObject]@{ Category = "Dev mode"; Number = "18"; Slug = "dev-web";             Label = "Web (flet run --web, hot reload)" }
    [PSCustomObject]@{ Category = "Dev mode"; Number = "19"; Slug = "dev-android";         Label = "Android (scan QR with Flet app - no SDK needed)" }
    [PSCustomObject]@{ Category = "Dev mode"; Number = "20"; Slug = "dev-ios";             Label = "iOS (scan QR with Flet app - no Xcode needed)" }
    [PSCustomObject]@{ Category = "Signing"; Number = "21"; Slug = "keystore-gen";         Label = "Generate Android upload keystore" }
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

function Get-PyprojectField([string]$Name) {
    $pyproject = Join-Path $FrontendDir "pyproject.toml"
    $content = Get-Content -Path $pyproject -Raw
    return [regex]::Match($content, "(?m)^\s*$Name\s*=\s*`"([^`"]+)`"").Groups[1].Value
}

function Get-EnvFilePassword([string]$VarName) {
    # Read a value out of the repo-root .env (not frontend/, which has no
    # .env of its own - the same file compose.yml itself reads) without
    # ever printing it. `flet build` picks this up from the process
    # environment (FLET_ANDROID_SIGNING_KEY_STORE_PASSWORD /
    # FLET_ANDROID_SIGNING_KEY_PASSWORD - see build_base.py), it never
    # reads .env files itself.
    $envPath = Join-Path (Split-Path $FrontendDir -Parent) ".env"
    if (-not (Test-Path $envPath)) {
        return $null
    }
    $line = Get-Content -Path $envPath | Where-Object { $_ -match "^\s*$VarName\s*=" } | Select-Object -First 1
    if (-not $line) {
        return $null
    }
    $value = ($line -split "=", 2)[1].Trim()
    return $value.Trim('"').Trim("'")
}

function Get-KeytoolPath {
    # Same PATH-first, then-known-install-locations discovery pattern as
    # Get-AdbPath above - `keytool` ships with any JDK, and Android
    # Studio bundles its own (the JBR - JetBrains Runtime) even on a
    # machine with no separate JDK install.
    $cmd = Get-Command keytool -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }
    $candidates = @()
    if ($env:JAVA_HOME) {
        $candidates += (Join-Path $env:JAVA_HOME "bin\keytool.exe")
    }
    $candidates += "C:\Program Files\Android\Android Studio\jbr\bin\keytool.exe"
    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path $candidate)) {
            return $candidate
        }
    }
    return $null
}

function Invoke-KeystoreGen {
    # Loads FLET_ANDROID_SIGNING_KEY_STORE_PASSWORD from the repo-root
    # .env so keytool can run fully non-interactively (-storepass/
    # -keypass), matching this script's existing --yes/non-interactive
    # philosophy for flet build. Uses that same password for both the
    # store and the key (build_base.py's own fallback already treats a
    # single password as valid for both, see pyproject.toml's own
    # [tool.flet.android.signing] comment) - add a separate
    # FLET_ANDROID_SIGNING_KEY_PASSWORD to .env if you ever want them to
    # differ.
    $keyDir = Join-Path $FrontendDir "key"
    $keystorePath = Join-Path $keyDir "upload-keystore.jks"
    $alias = "upload"

    if (Test-Path $keystorePath) {
        Write-Host "A keystore already exists at $keystorePath." -ForegroundColor Yellow
        Write-Host "Refusing to overwrite it - a signing key can never be swapped once an app has been published under it." -ForegroundColor Yellow
        Write-Host "Delete it yourself first if you really intend to generate a brand-new one." -ForegroundColor Yellow
        $script:ExitCode = 1
        return
    }

    $password = Get-EnvFilePassword "FLET_ANDROID_SIGNING_KEY_STORE_PASSWORD"
    if (-not $password) {
        Write-Host "FLET_ANDROID_SIGNING_KEY_STORE_PASSWORD is not set in the repo-root .env - add it first (see example.env), then re-run this option." -ForegroundColor Red
        $script:ExitCode = 1
        return
    }

    $keytoolPath = Get-KeytoolPath
    if (-not $keytoolPath) {
        Write-Host "'keytool' was not found on PATH, `$env:JAVA_HOME\bin, or Android Studio's bundled JBR location - install a JDK (or Android Studio) to generate a keystore." -ForegroundColor Red
        $script:ExitCode = 1
        return
    }

    New-Item -ItemType Directory -Force -Path $keyDir | Out-Null

    $org = Get-PyprojectField "org"
    $company = Get-PyprojectField "company"
    $product = Get-PyprojectField "product"
    $dname = "CN=$product, OU=$org, O=$company, L=Unknown, ST=Unknown, C=US"

    Write-Host "Generating upload keystore at $keystorePath (alias '$alias')..." -ForegroundColor Green
    & $keytoolPath -genkeypair -v -keystore $keystorePath -storetype JKS -keyalg RSA -keysize 2048 -validity 10000 -alias $alias -storepass $password -keypass $password -dname $dname
    $script:ExitCode = $LASTEXITCODE
    if ($script:ExitCode -eq 0) {
        Write-Host ""
        Write-Host "Keystore created. This file (and its password in .env) are the ONLY way to publish an update to this app under the same identity - back both up somewhere safe outside this repo." -ForegroundColor Yellow
    }
}

function Stop-StaleGradleDaemon {
    # Real, recurring failure found live: a Gradle daemon left running by
    # ANY earlier build attempt keeps a lock on files under
    # build/flutter/build/... (confirmed: `FileSystemException` on a
    # file_picker lint-cache jar, "the process cannot access the file
    # because it is being used by another process"), which then fails the
    # NEXT build too - happened twice in the same dev session. Gradle
    # daemons are designed to be stoppable/restartable freely, so a
    # defensive `gradlew --stop` against the *previous* build's generated
    # project (if one still exists) before starting a new one is safe and
    # directly prevents this recurring - deliberately not a blind
    # `taskkill java.exe`, which could kill an unrelated Java process the
    # user has open (Android Studio, another IDE, ...).
    $gradlew = Join-Path $BuildDir "flutter\android\gradlew.bat"
    if (Test-Path $gradlew) {
        & $gradlew --stop 2>&1 | Out-Null
    }
}

function Set-AndroidSigningEnv {
    # `flet build` reads FLET_ANDROID_SIGNING_KEY_STORE/
    # _KEY_STORE_PASSWORD/_KEY_PASSWORD from the process environment
    # (build_base.py), not from any .env file itself, and not from
    # pyproject.toml for the store PATH specifically - see
    # pyproject.toml's [tool.flet.android.signing] comment for why a
    # relative key_store there resolves against the wrong directory
    # (confirmed live via a real failed build). Computing an ABSOLUTE
    # path here, fresh at build time, sidesteps that entirely. All of
    # this is a harmless no-op for a non-Android build target, or if the
    # keystore/passwords don't exist yet.
    $keystorePath = Join-Path $FrontendDir "key\upload-keystore.jks"
    if (Test-Path $keystorePath) {
        $env:FLET_ANDROID_SIGNING_KEY_STORE = $keystorePath
    }
    $storePw = Get-EnvFilePassword "FLET_ANDROID_SIGNING_KEY_STORE_PASSWORD"
    if ($storePw) {
        $env:FLET_ANDROID_SIGNING_KEY_STORE_PASSWORD = $storePw
    }
    $keyPw = Get-EnvFilePassword "FLET_ANDROID_SIGNING_KEY_PASSWORD"
    if ($keyPw) {
        $env:FLET_ANDROID_SIGNING_KEY_PASSWORD = $keyPw
    }
}

function Invoke-BuildTarget([string]$Slug, [string]$Label, [string[]]$ExtraArgs) {
    if (-not (Test-Uv)) { return }
    Set-AndroidSigningEnv
    Stop-StaleGradleDaemon
    & uv sync
    Write-Host "Building $Label..." -ForegroundColor Green
    # flet-cli 0.86 manages its own pinned Flutter/Android SDK version and
    # prompts "It will be installed now. Proceed? [y/n]" the first time the
    # machine's own toolchain doesn't match (confirmed live: a system
    # Flutter 3.16.4 vs flet-cli's required 3.44.8) - with no TTY attached,
    # that prompt EOFs and crashes the build instead of hanging. --yes is
    # flet-cli's own documented bypass ("Re-run with --yes to install
    # automatically"), required for this script's non-interactive build path.
    & uv run flet build $Slug --yes @ExtraArgs
    $script:ExitCode = $LASTEXITCODE
}

function Invoke-PreviewWeb {
    $webDir = Join-Path $BuildDir "web"
    if (-not (Test-Path $webDir)) {
        Write-Host "No web build found at $webDir - build it first (option 10)." -ForegroundColor Red
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
        Write-Host "No Windows build found at $winDir - build it first (option 7)." -ForegroundColor Red
        $script:ExitCode = 1
        return
    }
    $exe = Get-ChildItem -Path $winDir -Filter "*.exe" -File | Select-Object -First 1
    if (-not $exe) {
        Write-Host "No .exe found under $winDir - the build may be incomplete; try rebuilding (option 7)." -ForegroundColor Red
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
        Write-Host "No .apk found under $apkDir or $flutterApkDir - build one first (option 1, 2, or 3)." -ForegroundColor Red
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
    $installOutput = & $adbPath install -r $target.FullName 2>&1
    $installOutput | ForEach-Object { Write-Host $_ }
    if ($LASTEXITCODE -ne 0) {
        # A real, one-time-transition error hit live: switching this app
        # from an unsigned/debug-signed build to a real upload-keystore-
        # signed one (see the Signing section above) means Android
        # refuses to "update" an already-installed copy whose signature
        # doesn't match - it isn't a bug in this script, it's Android's
        # own signature-matching security rule. Detect it specifically
        # and offer to uninstall the stale copy + retry, rather than just
        # printing a generic failure and leaving the user to work out why.
        if (($installOutput -join "`n") -match "INSTALL_FAILED_UPDATE_INCOMPATIBLE") {
            $package = Get-AndroidPackageId
            Write-Host ""
            Write-Host "The app already installed on this device was signed with a DIFFERENT key (likely from before this project's Android signing was set up) - Android won't install an update over it." -ForegroundColor Yellow
            if ($package) {
                Write-Host "Uninstalling the existing $package first will lose that copy's local app data/session on the device." -ForegroundColor Yellow
                $confirm = Read-Host "Uninstall the existing app and retry? [y/N]"
                if ($confirm -match "^[Yy]") {
                    & $adbPath uninstall $package | Out-Null
                    Write-Host "Retrying install of $($target.Name)..." -ForegroundColor Green
                    & $adbPath install -r $target.FullName
                    if ($LASTEXITCODE -ne 0) {
                        Write-Host "adb install still failed after uninstalling (exit $LASTEXITCODE)." -ForegroundColor Red
                        $script:ExitCode = $LASTEXITCODE
                        return
                    }
                } else {
                    $script:ExitCode = 1
                    return
                }
            } else {
                Write-Host "Could not determine the package id to uninstall automatically - run 'adb uninstall <package>' yourself, then retry." -ForegroundColor Red
                $script:ExitCode = 1
                return
            }
        } else {
            Write-Host "adb install failed (exit $LASTEXITCODE)." -ForegroundColor Red
            $script:ExitCode = $LASTEXITCODE
            return
        }
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

    $isQrFlow = ($FletRunArgs -contains "--android") -or ($FletRunArgs -contains "--ios")
    if ($isQrFlow) {
        # `flet run --android`/`--ios` prints its connect URL as a terminal
        # QR code (`qrcode.QRCode.print_ascii()`, real Unicode block glyphs
        # - U+2588/U+2580/U+2584/space). Two real, confirmed-live findings
        # while chasing this (2026-07-31), in order:
        # 1. Clearing this script's own `PYTHONUTF8`/`PYTHONIOENCODING`
        #    (added earlier for an unrelated `rich`-progress-output crash
        #    under a legacy cp1252 console) to match the sister senar
        #    project's own untouched `run.ps1` was WRONG - on this machine
        #    it made `qr.print_ascii()` crash outright
        #    (`UnicodeEncodeError: 'charmap' codec can't encode character
        #    '█'` - `cp1252` can't represent it at all), which is
        #    strictly worse than a blank render. `PYTHONIOENCODING=utf-8`
        #    is REQUIRED here, not the culprit - confirmed by the crash
        #    disappearing the moment it's restored.
        # 2. With the encoding vars present (no crash) but no console
        #    codepage change, the QR still didn't visually appear (blank) -
        #    a first attempt at `chcp 65001` alone also didn't resolve it.
        #    Both are applied together here, plus `[Console]::OutputEncoding`
        #    explicitly (PowerShell's own .NET Console wrapper caches this
        #    separately from the raw Win32 console codepage `chcp` sets, so
        #    setting only one of the two can leave the other still assuming
        #    the console's original codepage).
        # Root cause, confirmed live (2026-07-31): none of the encoding
        # tweaks above actually mattered - running the identical `uv run
        # flet run -r --ios` command typed directly at the prompt showed
        # the QR fine, while the *exact same command* run through this
        # function (called as `Invoke-Selection`'s return value inside
        # `if (-not (Invoke-Selection $choice))` in the menu loop below)
        # did not. Invoking an external command via `&` from inside a
        # PowerShell function whose result feeds an `if (...)` forces
        # PowerShell to capture that function's entire output stream to
        # resolve truthiness - which redirects the child process's stdout
        # through a pipe instead of a real inherited console handle. A
        # piped (non-tty) stdout is exactly why Python's encoding
        # behavior differed between the manual and scripted runs in the
        # first place (the `UnicodeEncodeError`/blank-render findings
        # above were real symptoms, just downstream of this actual cause,
        # not causes on their own). `Start-Process -NoNewWindow -Wait`
        # gives the child a genuine console handle regardless of how this
        # function's own return value is consumed by its caller, so the
        # QR-scan dev-run paths use it instead of the `&` call operator.
        chcp 65001 > $null
        try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
        $env:PYTHONUTF8 = "1"
        $env:PYTHONIOENCODING = "utf-8"
        $uvArgs = @("run", "flet", "run", "-r") + $FletRunArgs
        $proc = Start-Process -FilePath "uv" -ArgumentList $uvArgs -NoNewWindow -Wait -PassThru
        $script:ExitCode = $proc.ExitCode
        return
    }

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
        # `flet build` (flet-cli) has no dedicated --debug flag - confirmed
        # by reading its actual build_base.py source, only the always-
        # release `flutter build apk` gets invoked. `--flutter-build-args`
        # is a real, generic passthrough to the underlying `flutter build`
        # command (also confirmed in that source), so `--debug` there
        # switches Flutter's own build mode - a genuine debug APK, not a
        # flet-cli feature that doesn't exist. Must be the `=` form
        # (`--flutter-build-args=--debug`), not two separate array
        # elements - argparse's `nargs="*"` otherwise treats a bare
        # `--debug` token as its own (unrecognized) top-level flag rather
        # than this option's value, confirmed live (`flet: error:
        # unrecognized arguments: --debug` with the two-token form).
        "apk-debug" { Invoke-BuildTarget "apk" $selected.Label @("--flutter-build-args=--debug") }
        "apk-split" { Invoke-BuildTarget "apk" $selected.Label @("--split-per-abi") }
        "aab" { Invoke-BuildTarget "aab" $selected.Label @() }
        "ios" { Invoke-BuildTarget "ipa" $selected.Label @() }
        "ios-simulator" { Invoke-BuildTarget "ios-simulator" $selected.Label @() }
        "windows" { Invoke-BuildTarget "windows" $selected.Label @() }
        "macos" { Invoke-BuildTarget "macos" $selected.Label @() }
        "linux" { Invoke-BuildTarget "linux" $selected.Label @() }
        "web" { Invoke-BuildTarget "web" $selected.Label @() }
        "preview-web" { Invoke-PreviewWeb }
        "preview-desktop" { Invoke-PreviewDesktop }
        "preview-apk" { Invoke-PreviewApk }
        "preview-aab" { Invoke-NotApplicable "AAB" "Android App Bundles aren't directly installable. Upload to Play Console (internal testing track), or use Google's 'bundletool' to generate installable APKs from it. Use the APK preview option instead for local testing." }
        "preview-ios" { Invoke-NotApplicable "iOS / IPA" "IPA files need a provisioning profile, a registered device, or TestFlight to install - not something this script can automate. On macOS, use Xcode's Devices and Simulators window, or 'xcrun devicectl'." }
        "preview-ios-simulator" { Invoke-NotApplicable "iOS Simulator" "The iOS Simulator only runs on macOS with Xcode installed - not available on this host." }
        "dev-desktop" { Invoke-DevRun @() }
        "dev-web" { Invoke-DevRun @("--web") }
        "dev-android" { Invoke-DevRun @("--android") }
        "dev-ios" { Invoke-DevRun @("--ios") }
        "keystore-gen" { Invoke-KeystoreGen }
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
    # Reset before each selection so a failure doesn't wrongly report as
    # failed on the NEXT (possibly successful) action too - a real gap
    # found live: a build/preview failure previously left no visible
    # trace at all in the interactive loop (just silently looped back to
    # the menu), because $script:ExitCode was set but never checked here.
    $script:ExitCode = 0
    if (-not (Invoke-Selection $choice)) {
        Write-Host "Goodbye!"
        exit 0
    }
    if ($script:ExitCode -ne 0) {
        Write-Host ""
        Write-Host "Action failed (exit code $($script:ExitCode)) - see the output above for details." -ForegroundColor Red
    }
    Write-Host ""
    Read-Host "Press Enter to continue..." | Out-Null
}
