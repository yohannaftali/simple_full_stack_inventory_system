#!/bin/sh
set -e

# Resolver address for nginx's own `resolver` directive (nginx.conf.template),
# so `frontend`/`backend` get re-resolved instead of cached forever from
# worker startup - see that file's comment for the full "Host is
# unreachable after restarting one container" bug this fixes. Read from
# this container's own /etc/resolv.conf rather than hardcoding, since the
# embedded DNS address isn't the same across every environment (confirmed
# live: Podman's own machine here uses 10.89.2.1 - the network gateway -
# not Docker's usual 127.0.0.11). Falls back to Docker's default if
# resolv.conf has no nameserver line for some reason, rather than
# generating a config with an empty `resolver` directive (a hard nginx
# startup failure).
NGINX_RESOLVER=$(awk '/^nameserver/ {print $2; exit}' /etc/resolv.conf)
: "${NGINX_RESOLVER:=127.0.0.11}"
export NGINX_RESOLVER

# Explicit envsubst pass, not the base image's own /docker-entrypoint.d/
# templating (see nginx.conf.template's own comment for why - that
# mechanism only writes into /etc/nginx/conf.d/, which the top-level
# `stream` block this config needs isn't part of). The variable list
# passed to envsubst is deliberately explicit rather than a bare
# `envsubst < ... > ...` - an unrestricted envsubst would also try to
# substitute nginx's own runtime variables (`$http_upgrade`, `$host`,
# `$remote_addr`, ...), which look identical to environment variables in
# the template text but must reach nginx itself untouched.
envsubst '${NGINX_EXPOSED_FRONTEND_PORT} ${NGINX_EXPOSED_FRONTEND_PORT_SSL} ${NGINX_EXPOSED_BACKEND_PORT} ${NGINX_EXPOSED_BACKEND_PORT_SSL} ${FRONTEND_PORT} ${FRONTEND_PORT_SSL} ${UVICORN_PORT} ${UVICORN_PORT_SSL} ${NGINX_RESOLVER}' \
  < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf

exec nginx -g "daemon off;"
