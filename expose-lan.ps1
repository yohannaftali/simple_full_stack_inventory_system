# Exposes SFSIS's podman-published ports (backend 5000/5443, frontend
# 8000/8443 by default) to the rest of the LAN, so a phone/tablet on the
# same WiFi can reach them for testing (Server Config screen, or a browser
# hitting the containerized frontend directly).
#
# WHY THIS IS NEEDED: `compose.yml` already binds each service to
# 0.0.0.0 inside its container and publishes the port (`podman ps` shows
# "0.0.0.0:5000->5000/tcp"), but a WSL-backed podman machine on Windows
# (`UserModeNetworking: false`, the default - check with
# `podman machine inspect`) only forwards published ports to 127.0.0.1 on
# the Windows host itself, regardless of what `podman ps` claims -
# confirmed live via `netstat -ano | findstr :5000` showing a
# `127.0.0.1:5000` listener, not `0.0.0.0:5000`. This script adds a
# `netsh interface portproxy` rule (forward 0.0.0.0:<port> on every
# interface -> 127.0.0.1:<port>, where podman actually listens) plus a
# matching inbound firewall rule, for each port. This is a
# Windows/WSL-networking gotcha, not a bug in this repo's compose.yml.
#
# Run as ADMINISTRATOR (portproxy/firewall changes need elevation).
# Usage:
#   .\expose-lan.ps1                # expose the default port set
#   .\expose-lan.ps1 -Ports 5000     # expose just one port
#   .\expose-lan.ps1 -Remove         # undo (remove the rules added above)
param(
    [int[]]$Ports = @(5000, 5443, 8000, 8443),
    [switch]$Remove
)

$ErrorActionPreference = "Stop"

$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error "This script must be run as Administrator (portproxy/firewall changes require elevation). Right-click PowerShell -> 'Run as Administrator', then re-run this script."
    exit 1
}

$FirewallRuleName = "SFSIS LAN access"

if ($Remove) {
    foreach ($port in $Ports) {
        Write-Host "Removing portproxy rule for port $port..."
        & netsh interface portproxy delete v4tov4 listenaddress=0.0.0.0 listenport=$port 2>&1 | Out-Null
    }
    $existing = Get-NetFirewallRule -DisplayName $FirewallRuleName -ErrorAction SilentlyContinue
    if ($existing) {
        Write-Host "Removing firewall rule '$FirewallRuleName'..."
        Remove-NetFirewallRule -DisplayName $FirewallRuleName
    }
    Write-Host "Done - LAN exposure removed."
    exit 0
}

foreach ($port in $Ports) {
    # Delete-then-add makes this idempotent - re-running the script (e.g.
    # after a reboot, or to add a port) never fails on an "already exists"
    # error the way a bare `add` would.
    & netsh interface portproxy delete v4tov4 listenaddress=0.0.0.0 listenport=$port 2>&1 | Out-Null
    & netsh interface portproxy add v4tov4 listenaddress=0.0.0.0 listenport=$port connectaddress=127.0.0.1 connectport=$port
    Write-Host "Forwarding 0.0.0.0:$port -> 127.0.0.1:$port"
}

$existingRule = Get-NetFirewallRule -DisplayName $FirewallRuleName -ErrorAction SilentlyContinue
if ($existingRule) {
    Remove-NetFirewallRule -DisplayName $FirewallRuleName
}
New-NetFirewallRule -DisplayName $FirewallRuleName -Direction Inbound -Protocol TCP -LocalPort $Ports -Action Allow | Out-Null
Write-Host "Firewall rule '$FirewallRuleName' allows inbound TCP on: $($Ports -join ', ')"

# A dev machine commonly has several IPv4 adapters (Ethernet, WiFi, WSL's
# own vEthernet, podman/Docker's virtual switch, ...) - only the one on
# the SAME subnet as the phone/tablet actually works, and picking the
# wrong one (a real mistake hit live while diagnosing this) silently
# fails with no useful error. List every real candidate so the dev picks
# correctly, rather than guessing at "the" IP.
Write-Host ""
Write-Host "Candidate LAN addresses on this machine (pick the one on the SAME WiFi/subnet as your test device):"
Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object {
        $_.IPAddress -notlike "127.*" -and
        $_.IPAddress -notlike "169.254.*" -and
        $_.InterfaceAlias -notmatch "Loopback|vEthernet|WSL"
    } |
    ForEach-Object {
        Write-Host ("  {0,-20} {1}" -f $_.IPAddress, $_.InterfaceAlias)
    }

Write-Host ""
Write-Host "Example: point the app's Server Config screen (or a browser) at http://<chosen-ip>:5000"
Write-Host "Undo with: .\expose-lan.ps1 -Remove"
