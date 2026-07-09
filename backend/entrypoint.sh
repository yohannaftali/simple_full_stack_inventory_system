#!/bin/bash
set -e

CERT_DIR="certs"
CERT_FILE="$CERT_DIR/cert.pem"
KEY_FILE="$CERT_DIR/key.pem"

mkdir -p "$CERT_DIR"

if [ ! -f "$CERT_FILE" ] || [ ! -f "$KEY_FILE" ]; then
  echo "No TLS certificate found, generating a self-signed one for local development..."
  openssl req -x509 -newkey rsa:2048 -nodes \
    -keyout "$KEY_FILE" -out "$CERT_FILE" \
    -days 3650 -subj "/CN=localhost"
fi

alembic upgrade head

uvicorn src.main:app --host "${UVICORN_HOST:-0.0.0.0}" --port "${UVICORN_PORT:-5000}" &
uvicorn src.main:app --host "${UVICORN_HOST:-0.0.0.0}" --port "${UVICORN_PORT_SSL:-5443}" \
  --ssl-keyfile "$KEY_FILE" --ssl-certfile "$CERT_FILE" &

wait -n
