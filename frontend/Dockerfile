FROM python:3.13-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends openssl socat zenity \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app

RUN pip install --no-cache-dir uv

COPY frontend/pyproject.toml ./pyproject.toml
RUN uv sync --no-dev

COPY frontend/src ./src

# Installed outside /usr/src/app since compose.yml bind-mounts ./frontend
# over that directory in dev - a script copied only under WORKDIR would be
# hidden by the mount instead of running.
COPY frontend/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

EXPOSE 8000
EXPOSE 8443

CMD ["entrypoint.sh"]
