# SFSIS app

> **This is the current app, running on Flet 0.85.3.**

## Install UV

https://docs.astral.sh/uv/getting-started/installation/

Using powershell
```
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## Build, Preview, and Dev-Run using the script

Run with no arguments for an interactive menu (loops back after every
action - `0` to exit), or pass an option directly for one-shot/scripting
use (e.g. `.\run.ps1 apk-debug`, `./run.sh dev-web`).

Windows:
```
.\run.ps1
```

macOS/Linux:
```
./run.sh
```

Available options:
```
Build:
  1) APK (Release)
  2) APK (Debug)
  3) APK (Release, split per ABI)
  4) AAB (Android App Bundle)
  5) iOS (IPA)
  6) iOS Simulator (.app)
  7) Windows desktop
  8) macOS desktop
  9) Linux desktop
  10) Web

Preview:
  11) Web (serve build/web locally)
  12) Desktop, current host (launch built app)
  13) APK (install + launch on a connected device via adb)
  14) AAB (not directly previewable)
  15) iOS / IPA (not directly previewable)
  16) iOS Simulator (macOS/Xcode only)

Dev mode:
  17) Desktop (flet run, hot reload)
  18) Web (flet run --web, hot reload)
  19) Android (scan QR with Flet app - no SDK needed)
  20) iOS (scan QR with Flet app - no Xcode needed)

  0) Exit
```

Requires [uv](https://docs.astral.sh/uv/) on `PATH` - the script runs
`uv sync` automatically before every build/dev-run.

**APK (Release) vs APK (Debug)**: `flet build apk` (option 1) always
builds a signed release APK - this is the normal way to build, and is
what you want for anything you intend to actually distribute or install
long-term. **If a release build fails with a Gradle error mentioning a
locked file** (`FileSystemException`, "the process cannot access the
file because it is being used by another process"), it's almost always
a leftover Gradle daemon from an earlier build attempt - the script
already tries to stop it automatically before each build, but if it
still happens, close any other terminal/IDE that might be running a
Flutter/Gradle build and try again. Option 2 (APK Debug) is useful for a
quick local test build without needing to fully debug that.


## Run the app

### uv

Run as a desktop app:

```
uv run flet run
```

Run as a web app:

```
uv run flet run --web
```

### Poetry

Install dependencies from `pyproject.toml`:

```
poetry install
```

Run as a desktop app:

```
poetry run flet run
```

Run as a web app:

```
poetry run flet run --web
```

For more details on running the app, refer to the [Getting Started Guide](https://flet.dev/docs/getting-started/).

## Build the app

### Android

```
flet build apk -v
```

For more details on building and signing `.apk` or `.aab`, refer to the [Android Packaging Guide](https://flet.dev/docs/publish/android/).

### iOS

```
flet build ipa -v
```

For more details on building and signing `.ipa`, refer to the [iOS Packaging Guide](https://flet.dev/docs/publish/ios/).

### macOS

```
flet build macos -v
```

For more details on building macOS package, refer to the [macOS Packaging Guide](https://flet.dev/docs/publish/macos/).

### Linux

```
flet build linux -v
```

For more details on building Linux package, refer to the [Linux Packaging Guide](https://flet.dev/docs/publish/linux/).

### Windows

```
flet build windows -v
```

For more details on building Windows package, refer to the [Windows Packaging Guide](https://flet.dev/docs/publish/windows/).