#!/bin/bash
set -e

CERT_DIR="certs"
CERT_FILE="$CERT_DIR/cert.pem"
KEY_FILE="$CERT_DIR/key.pem"
COMBINED_PEM="$CERT_DIR/combined.pem"

mkdir -p "$CERT_DIR"

if [ ! -f "$CERT_FILE" ] || [ ! -f "$KEY_FILE" ]; then
  echo "No TLS certificate found, generating a self-signed one for local development..."
  openssl req -x509 -newkey rsa:2048 -nodes \
    -keyout "$KEY_FILE" -out "$CERT_FILE" \
    -days 3650 -subj "/CN=localhost"
fi

# socat wants cert+key combined in one PEM file
cat "$CERT_FILE" "$KEY_FILE" > "$COMBINED_PEM"

# src/asgi.py (not the `flet run --web` CLI - see its docstring for why)
# needs the same FLET_APP_STORAGE_DATA/TEMP env vars the CLI would normally
# set itself (flet_cli/commands/run.py: `<script's dir>/storage/data` /
# `.../storage/temp`) - utils/app_logger.py reads these for its log
# directory and falls back to a generic temp dir without them.
export FLET_APP_STORAGE_DATA="$(pwd)/src/storage/data"
export FLET_APP_STORAGE_TEMP="$(pwd)/src/storage/temp"

# No built-in TLS support here either, so HTTPS is a socat TLS relay in
# front of it: terminates TLS on FRONTEND_PORT_SSL, forwards the plain bytes
# to the plain-HTTP ASGI server on FRONTEND_PORT. Works for the WebSocket
# traffic Flet's UI updates ride on too, since socat operates at the raw TCP
# level and doesn't need to understand HTTP.
uv run uvicorn asgi:app --app-dir src --host "${FRONTEND_HOST:-0.0.0.0}" --port "${FRONTEND_PORT:-8000}" &

socat OPENSSL-LISTEN:${FRONTEND_PORT_SSL:-8443},cert="$COMBINED_PEM",verify=0,fork,reuseaddr \
  TCP:127.0.0.1:${FRONTEND_PORT:-8000} &

wait -n
