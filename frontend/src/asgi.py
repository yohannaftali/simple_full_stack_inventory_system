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
import requests
import urllib3
from fastapi import Request
from fastapi.responses import Response
from fastapi.routing import APIRoute

# Same dev-friendly self-signed-cert tolerance as utils/http_client.py -
# this route calls the backend with verify=False too.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from main import main
from repository.server_url import DEFAULT_SERVER_URL
from utils.client_context import client_id_var
from utils.persistence import load_client_session

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
    resolved = client_id_var.get()
    print(f"[asgi before_main] client_id_var resolved to: {resolved!r}")
    page.data["client_id"] = resolved


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

        # Log websocket handshakes only (one per Flet session) - http
        # scope fires for every static asset request and drowns the log.
        if scope["type"] == "websocket":
            print(
                f"[asgi middleware] websocket {scope.get('path')} "
                f"client_id={client_id!r} is_new={is_new}"
            )

        client_id_var.set(client_id)

        if is_new:
            # Set the cookie on whichever response this connection produces:
            # - http.response.start: the normal first-visit path - the page
            #   load that serves index.html sets the cookie, and the
            #   WebSocket the app opens moments later carries it back.
            # - websocket.accept: a WS handshake that arrived with NO cookie
            #   (a stale tab from before the cookie existed, auto-reconnecting
            #   after a container restart - no page reload, so no http
            #   request ever happens for it). Without setting the cookie on
            #   the 101 response too, the id minted for that connection dies
            #   with it: a login persisted under it lands in a session file
            #   no future tab can ever reach, which looks exactly like "the
            #   app forgot my login". Browsers do store Set-Cookie from
            #   websocket handshake responses.
            cookie_value = (
                f"{_COOKIE_NAME}={client_id}; Path=/; Max-Age={_COOKIE_MAX_AGE}; "
                "HttpOnly; SameSite=Lax"
            )

            async def send_wrapper(message):
                if message["type"] in ("http.response.start", "websocket.accept"):
                    message.setdefault("headers", [])
                    message["headers"].append(
                        (b"set-cookie", cookie_value.encode("latin-1"))
                    )
                await send(message)

            await self.app(scope, receive, send_wrapper)
            return

        await self.app(scope, receive, send)


_fastapi_app = ft.run(
    main=main,
    before_main=before_main,
    assets_dir=str(_ASSETS_DIR),
    export_asgi_app=True,
)


def download_export(module: str, table_name: str, request: Request):
    """Proxies a table export download for the browser.

    The browser has no session cookie for the backend - only this Flet
    process does (see AGENTS.md's "Container networking gotcha": every
    `HttpClient` call runs server-side, here). This route resolves the
    caller's client id (query param from the launching session, else
    cookie), loads that browser's persisted server_url/http_cookies (the
    same ones `HttpClient` itself would use), forwards the request to the
    backend's `GET C_{module}/export_{table_name}`, and streams the bytes
    straight back with the backend's own `Content-Disposition`/
    `Content-Type` headers intact, so the browser downloads a
    correctly-named file.

    `table_name` is in the path because one module can hold several
    tables (stock_in's "detail" header list and its "items" sub-table,
    scoped by a header_id custom param that flows through the query
    string here) - it mirrors the `get_{name}` convention the table's
    own data endpoint follows, so `export_{name}` is its export twin.

    A sync `def` (not `async def`) so FastAPI runs the blocking
    `requests.get` call in its threadpool instead of the event loop.
    """
    # The launching Flet session passes its own client_id as a query param
    # (see components/table/export_menu.py) - prefer it over the cookie,
    # since it directly names the session file that holds the login that
    # triggered this download, regardless of what cookie state the browser
    # is in (a stale tab's session id may never have made it into a
    # cookie). The id is a per-browser random key, not a credential for
    # anything beyond this container's own session file.
    client_id = request.query_params.get("client_id") or request.cookies.get(_COOKIE_NAME)
    print(f"[download proxy] /download/{module}/{table_name} client_id={client_id!r}")
    if not client_id:
        return Response("Not authenticated", status_code=401)

    session = load_client_session(client_id)
    server_url = (session.get("server_url") or DEFAULT_SERVER_URL).rstrip("/")
    cookies = session.get("http_cookies") or {}

    backend_url = f"{server_url}/C_{module}/export_{table_name}"
    # Forward the query string minus client_id - that's frontend-proxy
    # plumbing, not something the backend export endpoint should see.
    query = "&".join(
        part
        for part in str(request.url.query).split("&")
        if part and not part.startswith("client_id=")
    )
    if query:
        backend_url = f"{backend_url}?{query}"

    try:
        backend_response = requests.get(
            backend_url, cookies=cookies, timeout=300, verify=False, allow_redirects=False
        )
    except requests.exceptions.RequestException as e:
        return Response(f"Export failed: {e}", status_code=502)

    if backend_response.status_code >= 400:
        return Response(backend_response.text, status_code=backend_response.status_code)

    return Response(
        content=backend_response.content,
        media_type=backend_response.headers.get("content-type", "application/octet-stream"),
        headers={
            "Content-Disposition": backend_response.headers.get(
                "content-disposition", f'attachment; filename="{module}_{table_name}"'
            )
        },
    )


# Flet's own web app already registered a catch-all `/{path:path}` route
# (serving the Flutter SPA's index.html for any unmatched path) before this
# module ever runs `ft.run(export_asgi_app=True)`. FastAPI/Starlette match
# routes in registration order, so a plain `@_fastapi_app.get(...)`
# decorator here would append after that catch-all and never be reached -
# insert at the front of the routing table instead.
_fastapi_app.router.routes.insert(
    0, APIRoute("/download/{module}/{table_name}", download_export, methods=["GET"])
)

app = ClientIdMiddleware(_fastapi_app)
