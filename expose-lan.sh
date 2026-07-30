#!/usr/bin/env bash
# Exposes SFSIS's nginx passthrough ports (backend 5001/5444, frontend
# 8001/8444 - issue #69) to the rest of the LAN, so a phone/tablet on the
# same WiFi can reach them for testing (Server Config screen, or a
# browser hitting the containerized frontend directly). These are the
# ports a real mobile/external client should use (see AGENTS.md's Big
# Picture section) - the original direct backend/frontend ports
# (5000/5443/8000/8443) are deliberately NOT in this script's default
# set, since they're for local host-side debugging only, not LAN/
# external exposure.
#
# WHY THIS IS NEEDED (see expose-lan.ps1's own header for the Windows/WSL
# version of this problem): `compose.yml` already binds each service to
# 0.0.0.0 inside its container and publishes the port, but some podman/
# Docker networking setups still only end up listening on 127.0.0.1 on
# the HOST side - this script checks which case you're in and only takes
# action if actually needed, rather than assuming.
#
# On Linux this is usually already fine (native podman binds the real
# host interfaces directly) - the more common blocker is a firewall
# (ufw) not allowing the port through, which this script can fix with
# sudo. On macOS, Podman Desktop runs containers inside its own VM;
# this script has NOT been verified against a real macOS host in this
# session (none available) - it still runs the same diagnostic/relay
# logic, but treat its macOS path as best-effort until confirmed.
#
# Usage:
#   ./expose-lan.sh                 # check + fix the default (nginx) port
#                                    # set, read from .env (falls back to
#                                    # example.env's own defaults if .env
#                                    # is missing or a var is unset)
#   ./expose-lan.sh 8001             # just one port
#   sudo ./expose-lan.sh             # needed if ufw/pf changes are required
#   ./expose-lan.sh --remove         # stop any relay this script started
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env"

# Reads a port from .env rather than hardcoding it a second time here -
# that file is the single source of truth for NGINX_EXPOSED_*, and
# duplicating those numbers as literals would silently drift out of sync
# the moment .env changes. `tail -n1` picks the last match if a var is
# ever defined twice; `tr -d '\r'` guards a CRLF-saved .env on Windows.
get_env_port() {
    local name="$1" default="$2" val=""
    if [ -f "$ENV_FILE" ]; then
        val="$(grep -E "^${name}=" "$ENV_FILE" | tail -n1 | cut -d= -f2- | tr -d '\r' | xargs)"
    fi
    echo "${val:-$default}"
}

PORTS=(
    "$(get_env_port NGINX_EXPOSED_BACKEND_PORT 5001)"
    "$(get_env_port NGINX_EXPOSED_BACKEND_PORT_SSL 5444)"
    "$(get_env_port NGINX_EXPOSED_FRONTEND_PORT 8001)"
    "$(get_env_port NGINX_EXPOSED_FRONTEND_PORT_SSL 8444)"
)
RELAY_PID_DIR="/tmp/sfsis-expose-lan"

if [ "${1:-}" = "--remove" ]; then
    if [ -d "$RELAY_PID_DIR" ]; then
        for pidfile in "$RELAY_PID_DIR"/*.pid; do
            [ -e "$pidfile" ] || continue
            pid=$(cat "$pidfile")
            if kill -0 "$pid" 2>/dev/null; then
                kill "$pid"
                echo "Stopped relay (pid $pid): $(basename "$pidfile" .pid)"
            fi
            rm -f "$pidfile"
        done
    fi
    if command -v ufw >/dev/null 2>&1; then
        for port in "${PORTS[@]}"; do
            sudo ufw delete allow "${port}/tcp" 2>/dev/null || true
        done
    fi
    echo "Done - LAN exposure removed."
    exit 0
fi

if [ "${1:-}" != "" ]; then
    PORTS=("$1")
fi

detect_host_os() {
    case "$(uname -s)" in
        Darwin*) echo "macos" ;;
        Linux*) echo "linux" ;;
        *) echo "unknown" ;;
    esac
}

is_listening_on_all_interfaces() {
    local port="$1"
    if command -v ss >/dev/null 2>&1; then
        ss -tln 2>/dev/null | grep -qE "(\*|0\.0\.0\.0|\[::\]):${port}\b"
    elif command -v netstat >/dev/null 2>&1; then
        netstat -an 2>/dev/null | grep -qE "(\*|0\.0\.0\.0|\.)\.${port}[[:space:]].*LISTEN"
    else
        return 1
    fi
}

list_lan_ips() {
    local host_os="$1"
    if [ "$host_os" = "macos" ]; then
        ifconfig | awk '/^[a-z]/{iface=$1} /inet /{print $2, iface}' | grep -v '^127\.' || true
    elif [ "$host_os" = "linux" ] && command -v ip >/dev/null 2>&1; then
        ip -4 addr show 2>/dev/null | awk '/inet /{print $2, $NF}' | grep -vE '^127\.|docker|podman|veth|br-' || true
    else
        # Unrecognized host (this script targets Linux/macOS - use
        # expose-lan.ps1 on Windows) or `ip` missing - nothing to list,
        # but don't let `set -e` abort the whole script over it.
        return 0
    fi
}

HOST_OS="$(detect_host_os)"
echo "Host OS: ${HOST_OS}"
if [ "$HOST_OS" = "unknown" ]; then
    echo "This script targets Linux/macOS - on Windows, use expose-lan.ps1 instead."
fi
echo ""

for port in "${PORTS[@]}"; do
    if is_listening_on_all_interfaces "$port"; then
        echo "Port ${port}: already listening on all interfaces - no relay needed."
        continue
    fi

    echo "Port ${port}: not listening on all interfaces (likely 127.0.0.1-only)."
    if ! command -v socat >/dev/null 2>&1; then
        echo "  'socat' not found - install it (apt install socat / brew install socat) to auto-relay,"
        echo "  or investigate why podman isn't binding 0.0.0.0:${port} directly (compose.yml already"
        echo "  requests 0.0.0.0 inside the container - this would be a host/VM networking issue)."
        continue
    fi

    mkdir -p "$RELAY_PID_DIR"
    pidfile="${RELAY_PID_DIR}/${port}.pid"
    if [ -f "$pidfile" ] && kill -0 "$(cat "$pidfile")" 2>/dev/null; then
        echo "  Relay already running (pid $(cat "$pidfile"))."
    else
        nohup socat TCP-LISTEN:"${port}",fork,reuseaddr TCP:127.0.0.1:"${port}" >/dev/null 2>&1 &
        echo $! > "$pidfile"
        echo "  Started relay: 0.0.0.0:${port} -> 127.0.0.1:${port} (pid $!)"
    fi
done

if command -v ufw >/dev/null 2>&1; then
    echo ""
    echo "ufw detected - opening ports (needs sudo):"
    for port in "${PORTS[@]}"; do
        sudo ufw allow "${port}/tcp" || echo "  Could not add ufw rule for ${port} - run with sudo, or add it yourself: sudo ufw allow ${port}/tcp"
    done
elif [ "$HOST_OS" = "macos" ]; then
    echo ""
    echo "macOS: the Application Firewall (System Settings > Network > Firewall) usually"
    echo "prompts on the first inbound connection rather than needing a pre-added rule -"
    echo "allow it if/when prompted."
fi

echo ""
echo "Candidate LAN addresses on this machine (pick the one on the SAME WiFi/subnet as your test device):"
list_lan_ips "$HOST_OS" | while read -r ip iface; do
    printf "  %-20s %s\n" "$ip" "$iface"
done

echo ""
echo "Example: point the app's Server Config screen (or a browser) at http://<chosen-ip>:${PORTS[0]}"
echo "Undo with: ./expose-lan.sh --remove"
