#!/usr/bin/env bash
# Interactive menu to run/preview the frontend (issue #67), two ways:
#   1-6: preview a build already produced by build.sh - serves the web
#        bundle, launches a built desktop executable, or installs an APK
#        to a connected device via adb. Does NOT build anything itself -
#        run build.sh first for whichever target you want to preview.
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
#        Same convention as senar's own run.ps1 Test-Desktop/-Web/
#        -Android/-Ios functions.
set -euo pipefail

cd "$(dirname "$0")"

# Same Windows-console UnicodeEncodeError workaround as build.sh - harmless
# no-op on Linux/macOS, which already default to UTF-8.
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8

FRONTEND_DIR="$(pwd)/frontend"
BUILD_DIR="${FRONTEND_DIR}/build"

get_android_package_id() {
    # `[tool.flet]` org + `[project]` name build the Android/iOS bundle ID
    # the same way flet-cli itself does (see frontend/pyproject.toml's own
    # [tool.flet] comment) - parsed here instead of hardcoded so this stays
    # correct if either value ever changes.
    local pyproject="${FRONTEND_DIR}/pyproject.toml"
    local org name
    org=$(grep -E '^\s*org\s*=' "$pyproject" | head -1 | sed -E 's/.*"([^"]+)".*/\1/')
    name=$(grep -E '^name\s*=' "$pyproject" | head -1 | sed -E 's/.*"([^"]+)".*/\1/')
    if [ -z "$org" ] || [ -z "$name" ]; then
        return 1
    fi
    echo "${org}.${name}"
}

detect_host_os() {
    case "$(uname -s)" in
        Darwin*) echo "macos" ;;
        Linux*) echo "linux" ;;
        *) echo "unknown" ;;
    esac
}

run_web() {
    local web_dir="${BUILD_DIR}/web"
    if [ ! -d "$web_dir" ]; then
        echo "Error: no web build found at ${web_dir} - run './build.sh web' first." >&2
        exit 1
    fi
    if ! command -v uv >/dev/null 2>&1; then
        echo "Error: 'uv' was not found on PATH. Install it from https://docs.astral.sh/uv, then re-run this script." >&2
        exit 1
    fi
    cd "$FRONTEND_DIR"
    uv run flet serve "build/web"
}

run_desktop() {
    local host_os
    host_os="$(detect_host_os)"
    case "$host_os" in
        macos)
            local app_dir="${BUILD_DIR}/macos"
            if [ ! -d "$app_dir" ]; then
                echo "Error: no macOS build found at ${app_dir} - run './build.sh macos' first." >&2
                exit 1
            fi
            local app
            app=$(find "$app_dir" -maxdepth 1 -name "*.app" | head -1)
            if [ -z "$app" ]; then
                echo "Error: no .app bundle found under ${app_dir} - the build may be incomplete; try rebuilding." >&2
                exit 1
            fi
            echo "Launching ${app}..."
            # NOTE: not verified on a real macOS host in this session (no
            # macOS machine available) - `open` is the standard way to
            # launch a .app bundle, but re-check this the first time it's
            # actually run on macOS.
            open "$app"
            ;;
        linux)
            local bundle_dir="${BUILD_DIR}/linux"
            if [ ! -d "$bundle_dir" ]; then
                echo "Error: no Linux build found at ${bundle_dir} - run './build.sh linux' first." >&2
                exit 1
            fi
            local exe
            exe=$(find "$bundle_dir" -maxdepth 1 -type f -executable | head -1)
            if [ -z "$exe" ]; then
                echo "Error: no executable found under ${bundle_dir} - the build may be incomplete; try rebuilding." >&2
                exit 1
            fi
            echo "Launching ${exe}..."
            "$exe" &
            ;;
        *)
            echo "Error: desktop preview isn't supported on this host OS." >&2
            exit 1
            ;;
    esac
}

run_apk() {
    local apk_dir="${BUILD_DIR}/apk"
    if [ ! -d "$apk_dir" ]; then
        echo "Error: no APK build found at ${apk_dir} - run './build.sh apk' (or 'apk-split') first." >&2
        exit 1
    fi
    local apks=()
    while IFS= read -r -d '' f; do apks+=("$f"); done < <(find "$apk_dir" -maxdepth 1 -name "*.apk" -print0)
    if [ "${#apks[@]}" -eq 0 ]; then
        echo "Error: no .apk found under ${apk_dir} - the build may be incomplete; try rebuilding." >&2
        exit 1
    fi

    if ! command -v adb >/dev/null 2>&1; then
        echo ""
        echo "'adb' was not found on PATH - install the Android SDK platform-tools to enable automatic install+launch."
        echo "Manual install: connect a device/emulator, then run:"
        for apk in "${apks[@]}"; do
            echo "  adb install -r \"${apk}\""
        done
        exit 0
    fi

    if ! adb devices | tail -n +2 | grep -q $'\tdevice$'; then
        echo "Error: no connected/authorized Android device or emulator found (checked via 'adb devices'). Connect one and re-run." >&2
        exit 1
    fi

    local target="${apks[0]}"
    if [ "${#apks[@]}" -gt 1 ]; then
        echo "Multiple APKs found (split-per-abi build) - installing the first one:"
        for apk in "${apks[@]}"; do echo "  $(basename "$apk")"; done
    fi

    echo "Installing $(basename "$target")..."
    adb install -r "$target"

    local package
    if package=$(get_android_package_id); then
        echo "Launching ${package}..."
        adb shell monkey -p "$package" -c android.intent.category.LAUNCHER 1 >/dev/null
    else
        echo "Installed successfully - could not determine the package id to auto-launch; open it manually on the device."
    fi
}

not_applicable() {
    local label="$1"
    local reason="$2"
    echo ""
    echo "${label} cannot be previewed by this script:"
    echo "  ${reason}"
    echo ""
}

run_dev() {
    # `flet run` (the dev-mode runner) lives in flet-cli, same as `flet
    # build`/`flet serve` - only in the dev dependency group (see
    # pyproject.toml's own comment on why bare `flet` excludes it). `uv
    # sync` here (default group set, i.e. including dev) matches senar's
    # own run.ps1 convention of syncing before every dev-mode run.
    if ! command -v uv >/dev/null 2>&1; then
        echo "Error: 'uv' was not found on PATH. Install it from https://docs.astral.sh/uv, then re-run this script." >&2
        exit 1
    fi
    cd "$FRONTEND_DIR"
    uv sync
    echo "Starting Flet with hot reload (Ctrl+C to stop)..."
    uv run flet run -r "$@"
}

show_menu() {
    echo ""
    echo "SFSIS frontend test/preview"
    echo "============================"
    echo "  1) Web (serve build/web locally)"
    echo "  2) Desktop, current host (launch built app)"
    echo "  3) APK (install + launch on a connected device via adb)"
    echo "  4) AAB (not directly previewable)"
    echo "  5) iOS / IPA (not directly previewable)"
    echo "  6) iOS Simulator (macOS/Xcode only)"
    echo "  7) Dev mode: Desktop (flet run, hot reload)"
    echo "  8) Dev mode: Web (flet run --web, hot reload)"
    echo "  9) Dev mode: Android (scan QR with Flet app - no SDK needed)"
    echo "  10) Dev mode: iOS (scan QR with Flet app - no Xcode needed)"
    echo "  0) Cancel"
    echo ""
}

choice="${1:-}"
if [ -z "$choice" ]; then
    show_menu
    read -r -p "Select a target (number or name): " choice
fi

if [ -z "$choice" ] || [ "$choice" = "0" ]; then
    echo "Cancelled."
    exit 0
fi

case "$choice" in
    1|web) run_web ;;
    2|desktop|linux|macos) run_desktop ;;
    3|apk) run_apk ;;
    4|aab) not_applicable "AAB" "Android App Bundles aren't directly installable. Upload to Play Console (internal testing track), or use Google's 'bundletool' to generate installable APKs from it. Use the APK preview option instead for local testing." ;;
    5|ios) not_applicable "iOS / IPA" "IPA files need a provisioning profile, a registered device, or TestFlight to install - not something this script can automate. On macOS, use Xcode's Devices and Simulators window, or 'xcrun devicectl'." ;;
    6|ios-simulator)
        if [ "$(detect_host_os)" != "macos" ]; then
            not_applicable "iOS Simulator" "The iOS Simulator only runs on macOS with Xcode installed - not available on this host."
        else
            app_dir="${BUILD_DIR}/ios-simulator"
            if [ ! -d "$app_dir" ]; then
                echo "Error: no iOS Simulator build found at ${app_dir} - run './build.sh ios-simulator' first." >&2
                exit 1
            fi
            app=$(find "$app_dir" -maxdepth 1 -name "*.app" | head -1)
            if [ -z "$app" ]; then
                echo "Error: no .app bundle found under ${app_dir} - the build may be incomplete; try rebuilding." >&2
                exit 1
            fi
            package=$(get_android_package_id) || package=""
            echo "Installing to the booted Simulator..."
            # NOTE: not verified on a real macOS host in this session (no
            # macOS machine available) - re-check this the first time it's
            # actually run.
            xcrun simctl install booted "$app"
            if [ -n "$package" ]; then
                xcrun simctl launch booted "$package"
            fi
        fi
        ;;
    7|dev-desktop) run_dev ;;
    8|dev-web) run_dev --web ;;
    9|dev-android) run_dev --android ;;
    10|dev-ios) run_dev --ios ;;
    *)
        echo "Error: unknown preview target: $choice" >&2
        exit 1
        ;;
esac
