FROM nginx:alpine

# Templated with entrypoint.sh's own explicit envsubst pass (not the base
# image's built-in /docker-entrypoint.d/ templating mechanism - that only
# processes files into /etc/nginx/conf.d/, which is included from the
# `http` context alone, but this config also needs a top-level `stream`
# block for the TLS-passthrough ports - see nginx.conf.template's own
# comments). Explicit entrypoint.sh matches this repo's existing
# per-service convention (backend/frontend each write their own plain
# entrypoint.sh rather than relying on image-specific auto-behavior).
COPY nginx/nginx.conf.template /etc/nginx/nginx.conf.template
COPY nginx/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

CMD ["entrypoint.sh"]
