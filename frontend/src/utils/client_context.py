"""
Per-connection client identity, bridged from a browser cookie into Flet.

Flet's `Page` API exposes no way to read the underlying HTTP/WebSocket
request (no headers, no cookies) from inside a `main(page)`/`before_main`
callback. `asgi.py` (the containerized deployment's entrypoint) sets
`client_id_var` from the raw ASGI `cookie` header in middleware wrapping the
whole Flet web app, before calling through to Flet's own ASGI app. That
middleware runs in the same asyncio task as `before_main` - no
`asyncio.create_task` happens in between anywhere in Flet's own connection
handling before `before_main` is awaited (see `flet_web.fastapi.flet_app.
FletApp.__on_message`'s `REGISTER_CLIENT` handling) - so a `ContextVar` set
in that middleware is reliably visible when `before_main` reads it, without
needing to change any of Flet's own call signatures.

Only used by the ASGI deployment path (`asgi.py`); the plain `flet run
--web` CLI (local dev) never sets this, so `client_id_var.get()` stays
`None` there and `utils/persistence.py` falls back to SharedPreferences.
"""

from contextvars import ContextVar

client_id_var: ContextVar[str | None] = ContextVar("sfsis_client_id", default=None)
