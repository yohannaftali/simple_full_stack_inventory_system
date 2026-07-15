# Detects podman or docker and brings up the SFSIS stack (compose.yml).
# Prefers podman (this project's primary supported engine); falls back to
# docker if podman isn't installed.
$ErrorActionPreference = "Stop"

Set-Location -Path $PSScriptRoot

if (Get-Command podman -ErrorAction SilentlyContinue) {
    $engine = "podman"
} elseif (Get-Command docker -ErrorAction SilentlyContinue) {
    $engine = "docker"
} else {
    Write-Error "Neither 'podman' nor 'docker' was found on PATH. Install Podman (https://podman.io) or Docker Desktop, then re-run this script."
    exit 1
}

Write-Host "Using $engine to start SFSIS..."
& $engine compose -f compose.yml up -d --build
