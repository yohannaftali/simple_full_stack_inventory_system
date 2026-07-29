#!/usr/bin/env bash
# Single build+preview+dev-run menu for the SFSIS frontend, merging the
# former repo-root build.sh + test.sh into one script living inside
# frontend/ (so it sits next to pyproject.toml, where frontend tooling
# actually belongs, instead of two separate scripts at the repo root).
# Named `run.ps1`/`run.sh` to match the sister senar project's own
# frontend/run.ps1 convention, so a dev who already knows that project
# recognizes this immediately.
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
# - `adb` discovery falls back through $ANDROID_HOME/$ANDROID_SDK_ROOT/
#   the default macOS/Linux SDK install locations, not PATH only.
# - A persistent interactive menu: every selection returns to the menu
#   afterwards when launched with no CLI arg, matching senar's own
#   `while (true)` + "Press Enter to continue" loop. A direct CLI-arg
#   invocation (`./run.sh web`, scripting/CI use) still runs once and
#   exits.
set -uo pipefail

cd "$(dirname "$0")"
FRONTEND_DIR="$(pwd)"
BUILD_DIR="${FRONTEND_DIR}/build"

# flet-cli's `rich`-based progress output writes Unicode glyphs (e.g. "●")
# that raise UnicodeEncodeError under a legacy cp1252 Windows console when
# running under Git Bash/MSYS - confirmed live without this. Forcing
# UTF-8 I/O fixes it without needing the user to change their system
# codepage; harmless no-op on Linux/macOS, which already default to UTF-8.
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8

EXIT_CODE=0

# category:number:slug:label
TARGETS=(
    "Build:1:apk:APK (Release)"
    "Build:2:apk-split:APK (Release, split per ABI)"
    "Build:3:aab:AAB (Android App Bundle)"
    "Build:4:ios:iOS (IPA)"
    "Build:5:ios-simulator:iOS Simulator (.app)"
    "Build:6:windows:Windows desktop"
    "Build:7:macos:macOS desktop"
    "Build:8:linux:Linux desktop"
    "Build:9:web:Web"
    "Preview:10:preview-web:Web (serve build/web locally)"
    "Preview:11:preview-desktop:Desktop, current host (launch built app)"
    "Preview:12:preview-apk:APK (install + launch on a connected device via adb)"
    "Preview:13:preview-aab:AAB (not directly previewable)"
    "Preview:14:preview-ios:iOS / IPA (not directly previewable)"
    "Preview:15:preview-ios-simulator:iOS Simulator (macOS/Xcode only)"
    "Dev mode:16:dev-desktop:Desktop (flet run, hot reload)"
    "Dev mode:17:dev-web:Web (flet run --web, hot reload)"
    "Dev mode:18:dev-android:Android (scan QR with Flet app - no SDK needed)"
    "Dev mode:19:dev-ios:iOS (scan QR with Flet app - no Xcode needed)"
)

show_menu() {
    echo ""
    echo "SFSIS frontend"
    echo "=============="
    local last_category=""
    for entry in "${TARGETS[@]}"; do
        IFS=":" read -r category number slug label <<< "$entry"
        if [ "$category" != "$last_category" ]; then
            echo ""
            echo "${category}:"
            last_category="$category"
        fi
        echo "  ${number}) ${label}"
    done
    echo ""
    echo "  0) Exit"
    echo ""
}

require_uv() {
    if command -v uv >/dev/null 2>&1; then
        return 0
    fi
    echo "'uv' was not found on PATH. Install it from https://docs.astral.sh/uv, then re-run this script." >&2
    EXIT_CODE=1
    return 1
}

get_adb_path() {
    # Same discovery order as senar's own run.ps1 Install-Android-WithAdb -
    # PATH first, then $ANDROID_HOME/$ANDROID_SDK_ROOT, then the default
    # Android Studio install locations on macOS/Linux.
    if command -v adb >/dev/null 2>&1; then
        command -v adb
        return 0
    fi
    local candidates=()
    [ -n "${ANDROID_HOME:-}" ] && candidates+=("${ANDROID_HOME}/platform-tools/adb")
    [ -n "${ANDROID_SDK_ROOT:-}" ] && candidates+=("${ANDROID_SDK_ROOT}/platform-tools/adb")
    candidates+=("${HOME}/Library/Android/sdk/platform-tools/adb")
    candidates+=("${HOME}/Android/Sdk/platform-tools/adb")
    for candidate in "${candidates[@]}"; do
        if [ -x "$candidate" ]; then
            echo "$candidate"
            return 0
        fi
    done
    return 1
}

get_android_package_id() {
    # `[tool.flet]` org + `[project]` name build the Android/iOS bundle ID
    # the same way flet-cli itself does - parsed here instead of
    # hardcoded so this stays correct if either value ever changes.
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

run_build_target() {
    local flet_target="$1" label="$2"
    shift 2
    require_uv || return
    cd "$FRONTEND_DIR"
    uv sync
    echo "Building ${label}..."
    uv run flet build "$flet_target" "$@"
    EXIT_CODE=$?
}

run_preview_web() {
    local web_dir="${BUILD_DIR}/web"
    if [ ! -d "$web_dir" ]; then
        echo "No web build found at ${web_dir} - build it first (option 9)." >&2
        EXIT_CODE=1
        return
    fi
    require_uv || return
    cd "$FRONTEND_DIR"
    uv run flet serve "build/web"
    EXIT_CODE=$?
}

run_preview_desktop() {
    local host_os
    host_os="$(detect_host_os)"
    case "$host_os" in
        macos)
            local app_dir="${BUILD_DIR}/macos"
            if [ ! -d "$app_dir" ]; then
                echo "No macOS build found at ${app_dir} - build it first (option 7)." >&2
                EXIT_CODE=1
                return
            fi
            local app
            app=$(find "$app_dir" -maxdepth 1 -name "*.app" | head -1)
            if [ -z "$app" ]; then
                echo "No .app bundle found under ${app_dir} - the build may be incomplete; try rebuilding (option 7)." >&2
                EXIT_CODE=1
                return
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
                echo "No Linux build found at ${bundle_dir} - build it first (option 8)." >&2
                EXIT_CODE=1
                return
            fi
            local exe
            exe=$(find "$bundle_dir" -maxdepth 1 -type f -executable | head -1)
            if [ -z "$exe" ]; then
                echo "No executable found under ${bundle_dir} - the build may be incomplete; try rebuilding (option 8)." >&2
                EXIT_CODE=1
                return
            fi
            echo "Launching ${exe}..."
            "$exe" &
            ;;
        *)
            echo "Desktop preview isn't supported on this host OS." >&2
            EXIT_CODE=1
            ;;
    esac
}

run_preview_apk() {
    # Searches both the final `build/apk` output AND flet-cli's raw
    # Flutter scaffold output (`build/flutter/build/app/outputs/
    # flutter-apk`) - ported from senar's own Install-Android-WithAdb.
    # Confirmed real by reading flet-cli's build_base.py: `flutter_dir =
    # build_dir/flutter`, and the apk target's own `outputs` glob is
    # relative to that - so a build interrupted after Flutter finishes
    # but before flet-cli's own final copy step leaves a usable APK there
    # that would otherwise go unfound.
    local apk_dir="${BUILD_DIR}/apk"
    local flutter_apk_dir="${BUILD_DIR}/flutter/build/app/outputs/flutter-apk"
    local apks=()
    if [ -d "$apk_dir" ]; then
        while IFS= read -r -d '' f; do apks+=("$f"); done < <(find "$apk_dir" -maxdepth 1 -name "*.apk" -print0)
    fi
    if [ -d "$flutter_apk_dir" ]; then
        while IFS= read -r -d '' f; do apks+=("$f"); done < <(find "$flutter_apk_dir" -maxdepth 1 -name "*.apk" -print0)
    fi
    if [ "${#apks[@]}" -eq 0 ]; then
        echo "No .apk found under ${apk_dir} or ${flutter_apk_dir} - build one first (option 1 or 2)." >&2
        EXIT_CODE=1
        return
    fi
    # Newest first - picking an arbitrary filesystem-enumeration-order
    # match could otherwise install a stale APK from an earlier build.
    # `stat`'s mtime flag differs between GNU (Linux, `-c '%Y %n'`) and
    # BSD (macOS, `-f '%m %N'`) - try GNU first, fall back to BSD.
    if [ "${#apks[@]}" -gt 1 ]; then
        local stat_out
        stat_out=$(stat -c '%Y %n' "${apks[@]}" 2>/dev/null) || stat_out=$(stat -f '%m %N' "${apks[@]}" 2>/dev/null)
        if [ -n "$stat_out" ]; then
            mapfile -t apks < <(printf '%s\n' "$stat_out" | sort -rn | cut -d' ' -f2-)
        fi
    fi

    local adb_path
    if ! adb_path=$(get_adb_path); then
        echo ""
        echo "'adb' was not found on PATH, \$ANDROID_HOME, \$ANDROID_SDK_ROOT, or the default Android Studio SDK location - install the Android SDK platform-tools to enable automatic install+launch."
        echo "Manual install: connect a device/emulator, then run:"
        for apk in "${apks[@]}"; do
            echo "  adb install -r \"${apk}\""
        done
        return
    fi

    if ! "$adb_path" devices | tail -n +2 | grep -q $'\tdevice$'; then
        echo "No connected/authorized Android device or emulator found (checked via 'adb devices'). Connect one and re-run." >&2
        EXIT_CODE=1
        return
    fi

    local target="${apks[0]}"
    if [ "${#apks[@]}" -gt 1 ]; then
        echo "Multiple APKs found - installing the newest one ($(basename "$target")):"
        for apk in "${apks[@]}"; do echo "  $(basename "$apk")"; done
    fi

    echo "Installing $(basename "$target")..."
    "$adb_path" install -r "$target"
    if [ $? -ne 0 ]; then
        EXIT_CODE=1
        return
    fi

    local package
    if package=$(get_android_package_id); then
        echo "Launching ${package}..."
        "$adb_path" shell monkey -p "$package" -c android.intent.category.LAUNCHER 1 >/dev/null
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

run_preview_ios_simulator() {
    if [ "$(detect_host_os)" != "macos" ]; then
        not_applicable "iOS Simulator" "The iOS Simulator only runs on macOS with Xcode installed - not available on this host."
        return
    fi
    local app_dir="${BUILD_DIR}/ios-simulator"
    if [ ! -d "$app_dir" ]; then
        echo "No iOS Simulator build found at ${app_dir} - build it first (option 5)." >&2
        EXIT_CODE=1
        return
    fi
    local app
    app=$(find "$app_dir" -maxdepth 1 -name "*.app" | head -1)
    if [ -z "$app" ]; then
        echo "No .app bundle found under ${app_dir} - the build may be incomplete; try rebuilding (option 5)." >&2
        EXIT_CODE=1
        return
    fi
    local package
    package=$(get_android_package_id) || package=""
    echo "Installing to the booted Simulator..."
    # NOTE: not verified on a real macOS host in this session (no macOS
    # machine available) - re-check this the first time it's actually run.
    xcrun simctl install booted "$app"
    if [ -n "$package" ]; then
        xcrun simctl launch booted "$package"
    fi
}

run_dev() {
    # `flet run` (dev-mode runner) lives in flet-cli, same as `flet
    # build`/`flet serve` - only in the dev dependency group (see
    # pyproject.toml's own comment on why bare `flet` excludes it).
    require_uv || return
    cd "$FRONTEND_DIR"
    uv sync
    echo "Starting Flet with hot reload (Ctrl+C to stop)..."
    uv run flet run -r "$@"
    EXIT_CODE=$?
}

# Dispatches $1; sets $SHOULD_CONTINUE=1 always (every selection returns
# to the interactive menu loop, matching senar's own persistent-menu
# convention - even a blocking dev-run, once Ctrl+C'd, returns here
# rather than ending the whole session). $0/blank means Exit, handled by
# the caller before this is reached.
dispatch_choice() {
    local choice="$1"
    case "$choice" in
        1|apk) run_build_target apk "APK (Release)" ;;
        2|apk-split) run_build_target apk "APK (Release, split per ABI)" --split-per-abi ;;
        3|aab) run_build_target aab "AAB (Android App Bundle)" ;;
        4|ios) run_build_target ipa "iOS (IPA)" ;;
        5|ios-simulator) run_build_target ios-simulator "iOS Simulator (.app)" ;;
        6|windows) run_build_target windows "Windows desktop" ;;
        7|macos) run_build_target macos "macOS desktop" ;;
        8|linux) run_build_target linux "Linux desktop" ;;
        9|web) run_build_target web "Web" ;;
        10|preview-web) run_preview_web ;;
        11|preview-desktop) run_preview_desktop ;;
        12|preview-apk) run_preview_apk ;;
        13|preview-aab) not_applicable "AAB" "Android App Bundles aren't directly installable. Upload to Play Console (internal testing track), or use Google's 'bundletool' to generate installable APKs from it. Use the APK preview option instead for local testing." ;;
        14|preview-ios) not_applicable "iOS / IPA" "IPA files need a provisioning profile, a registered device, or TestFlight to install - not something this script can automate. On macOS, use Xcode's Devices and Simulators window, or 'xcrun devicectl'." ;;
        15|preview-ios-simulator) run_preview_ios_simulator ;;
        16|dev-desktop) run_dev ;;
        17|dev-web) run_dev --web ;;
        18|dev-android) run_dev --android ;;
        19|dev-ios) run_dev --ios ;;
        *)
            echo "Unknown option: $choice" >&2
            EXIT_CODE=1
            ;;
    esac
}

cli_choice="${1:-}"
if [ -n "$cli_choice" ] || [ "$#" -gt 0 ]; then
    if [ -z "$cli_choice" ] || [ "$cli_choice" = "0" ]; then
        echo "Cancelled."
        exit 0
    fi
    dispatch_choice "$cli_choice"
    exit $EXIT_CODE
fi

while true; do
    show_menu
    read -r -p "Select an option (number or name, 0 to exit): " choice
    echo ""
    if [ -z "$choice" ] || [ "$choice" = "0" ]; then
        echo "Goodbye!"
        exit 0
    fi
    dispatch_choice "$choice"
    echo ""
    read -r -p "Press Enter to continue..." _
done
