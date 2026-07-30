#!/bin/sh
set -e

# Explicit envsubst pass, not the base image's own /docker-entrypoint.d/
# templating (see nginx.conf.template's own comment for why - that
# mechanism only writes into /etc/nginx/conf.d/, which the top-level
# `stream` block this config needs isn't part of). The variable list
# passed to envsubst is deliberately explicit rather than a bare
# `envsubst < ... > ...` - an unrestricted envsubst would also try to
# substitute nginx's own runtime variables (`$http_upgrade`, `$host`,
# `$remote_addr`, ...), which look identical to environment variables in
# the template text but must reach nginx itself untouched.
envsubst '${NGINX_EXPOSED_FRONTEND_PORT} ${NGINX_EXPOSED_FRONTEND_PORT_SSL} ${NGINX_EXPOSED_BACKEND_PORT} ${NGINX_EXPOSED_BACKEND_PORT_SSL} ${FRONTEND_PORT} ${FRONTEND_PORT_SSL} ${UVICORN_PORT} ${UVICORN_PORT_SSL}' \
  < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf

exec nginx -g "daemon off;"
