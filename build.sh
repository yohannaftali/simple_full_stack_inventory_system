#!/usr/bin/env bash
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
set -euo pipefail

cd "$(dirname "$0")"

# flet-cli's `rich`-based progress output writes Unicode glyphs (e.g. "●")
# that raise UnicodeEncodeError under a legacy cp1252 Windows console when
# running under Git Bash/MSYS - confirmed live without this. Forcing
# UTF-8 I/O fixes it without needing the user to change their system
# codepage; harmless no-op on Linux/macOS, which already default to UTF-8.
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8

# number:slug:label:flet-target:extra-args (extra-args space-separated, empty if none)
TARGETS=(
    "1:apk:APK (Release):apk:"
    "2:apk-split:APK (Release, split per ABI):apk:--split-per-abi"
    "3:aab:AAB (Android App Bundle):aab:"
    "4:ios:iOS (IPA):ipa:"
    "5:ios-simulator:iOS Simulator (.app):ios-simulator:"
    "6:windows:Windows desktop:windows:"
    "7:macos:macOS desktop:macos:"
    "8:linux:Linux desktop:linux:"
    "9:web:Web:web:"
)

show_menu() {
    echo ""
    echo "SFSIS frontend build"
    echo "====================="
    for entry in "${TARGETS[@]}"; do
        IFS=":" read -r number slug label _ _ <<< "$entry"
        echo "  ${number}) ${label}"
    done
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

selected=""
for entry in "${TARGETS[@]}"; do
    IFS=":" read -r number slug label flet_target extra_args <<< "$entry"
    if [ "$choice" = "$number" ] || [ "$choice" = "$slug" ]; then
        selected="$entry"
        break
    fi
done

if [ -z "$selected" ]; then
    echo "Error: unknown build target: $choice" >&2
    exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
    echo "Error: 'uv' was not found on PATH. Install it from https://docs.astral.sh/uv, then re-run this script." >&2
    exit 1
fi

IFS=":" read -r number slug label flet_target extra_args <<< "$selected"
echo "Building ${label}..."
cd frontend
if [ -n "$extra_args" ]; then
    # shellcheck disable=SC2086
    uv run flet build "$flet_target" $extra_args
else
    uv run flet build "$flet_target"
fi
