FROM python:3.13-slim

# libzbar0 - native shared library pyzbar (issue #64) loads via ctypes to
# decode barcode/QR photos picked through ft.FilePicker; without it, pyzbar
# raises ImportError("Unable to find zbar shared library") at first use.
RUN apt-get update \
    && apt-get install -y --no-install-recommends openssl socat zenity libzbar0 \
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
