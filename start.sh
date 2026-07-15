#!/usr/bin/env bash
# Detects podman or docker and brings up the SFSIS stack (compose.yml).
# Prefers podman (this project's primary supported engine); falls back to
# docker if podman isn't installed.
set -euo pipefail

cd "$(dirname "$0")"

if command -v podman >/dev/null 2>&1; then
    ENGINE=podman
elif command -v docker >/dev/null 2>&1; then
    ENGINE=docker
else
    echo "Error: neither 'podman' nor 'docker' was found on PATH." >&2
    echo "Install Podman (https://podman.io) or Docker Desktop, then re-run this script." >&2
    exit 1
fi

echo "Using ${ENGINE} to start SFSIS..."
"${ENGINE}" compose -f compose.yml up -d --build
