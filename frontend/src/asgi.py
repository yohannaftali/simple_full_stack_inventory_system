"""
ASGI entrypoint for the containerized web deployment.

`entrypoint.sh` runs this (`uvicorn asgi:app`) instead of the `flet run
--web` CLI local dev uses. The CLI path has no hook to inject middleware,
and Flet's web-mode session persistence (`SharedPreferences`, a browser-side
service - see `utils/persistence.py`) is documented there as unreliable in
theory; in practice (see `frontend/src/storage/data/sfsis.log`) its
persist/load calls were failing routinely, not just on cold start -
`Could not persist http_cookies to client_storage` / `Could not load ...
from session store` with empty (timeout) errors, even well into an
already-running session. That's why a plain `podman compose restart
frontend` was dropping every logged-in session: nothing had actually been
saved to reload.

This wraps Flet's own FastAPI ASGI app (the exact one `flet run --web` uses
internally - `ft.run(..., export_asgi_app=True)`) with middleware that
issues a durable, per-browser `client_id` cookie (a plain `Set-Cookie` on
the first HTTP response - no JS/SharedPreferences round trip to race), then
threads that id into `before_main()` via a `ContextVar` (see
`utils/client_context.py`) so `utils/persistence.py` can persist session
data to a per-client JSON file on the container's own disk instead - a
synchronous file write can't time out the way a not-yet-mounted browser
service can, and (unlike a single shared file) a per-client file keeps
concurrent users of the same container from clobbering each other's login.

Not yet verified against a live multi-browser/restart test - see AGENTS.md's
session-persistence section for exactly what to check before trusting this
in a real deployment, and how to roll it back if something regresses.
"""

import uuid
from pathlib import Path

import flet as ft

from main import main
from utils.client_context import client_id_var

_COOKIE_NAME = "sfsis_client_id"
_COOKIE_MAX_AGE = 60 * 60 * 24 * 365  # 1 year

# asgi.py lives next to main.py (frontend/src/) - resolve assets_dir
# ourselves rather than relying on flet.run()'s default "assets" (which it
# resolves relative to CWD only when export_asgi_app=True, unlike the CLI's
# own script-relative resolution - see flet/app.py's `run()`).
_ASSETS_DIR = Path(__file__).resolve().parent / "assets"


def _get_cookie(headers: list[tuple[bytes, bytes]], name: str) -> str | None:
    for key, value in headers:
        if key.decode("latin-1").lower() != "cookie":
            continue
        for part in value.decode("latin-1").split(";"):
            part = part.strip()
            if part.startswith(f"{name}="):
                return part[len(name) + 1 :]
    return None


async def before_main(page: ft.Page):
    """Flet-native hook, called once per new session before `main(page)` -
    stash the client_id the middleware below resolved for this connection
    so utils/persistence.py's make_session_store() can find it."""
    if not hasattr(page, "data") or page.data is None:
        page.data = {}
    page.data["client_id"] = client_id_var.get()


class ClientIdMiddleware:
    """Bare ASGI middleware (not Starlette's `BaseHTTPMiddleware`, which
    doesn't support websocket scopes) - reads/sets the `client_id` cookie
    and exposes it via `client_id_var` for the rest of this request/
    connection's call chain, including Flet's own `before_main` hook."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        headers = scope.get("headers", [])
        client_id = _get_cookie(headers, _COOKIE_NAME)
        is_new = client_id is None
        if is_new:
            client_id = uuid.uuid4().hex

        client_id_var.set(client_id)

        if scope["type"] == "http" and is_new:
            # Set the cookie on the plain HTTP response that serves the
            # Flutter web app's index.html - by the time its JS opens the
            # WebSocket connection moments later, the browser already has
            # the cookie and sends it automatically, so there's no need to
            # (and no reliable way to) set it on the WS handshake itself.
            cookie_value = (
                f"{_COOKIE_NAME}={client_id}; Path=/; Max-Age={_COOKIE_MAX_AGE}; "
                "HttpOnly; SameSite=Lax"
            )

            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    message.setdefault("headers", [])
                    message["headers"].append(
                        (b"set-cookie", cookie_value.encode("latin-1"))
                    )
                await send(message)

            await self.app(scope, receive, send_wrapper)
            return

        await self.app(scope, receive, send)


app = ClientIdMiddleware(
    ft.run(
        main=main,
        before_main=before_main,
        assets_dir=str(_ASSETS_DIR),
        export_asgi_app=True,
    )
)
