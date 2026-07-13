"""
Session persistence backend.

Flet 0.85 removed the synchronous `page.client_storage` and replaced it with
the async `SharedPreferences` *service*, whose client-side method-channel
listener must mount before any get/set works. On desktop cold-starts that
listener isn't ready inside our fail-fast budget, so every call times out and
the whole session (cookies, server url, login) is silently lost on the next
process restart. See CHANGE_HISTORY.md (2026-07-06/07) and issues #646-#648.

Fix: on **native** platforms (desktop / Android / iOS) don't touch the flaky
service at all - persist to a plain JSON file with ordinary, synchronous file
I/O. It's instant, reliable, and durable *immediately* (no fire-and-forget
race), so a restart mid-navigation no longer logs the user out.

**Web** mode has no local filesystem *in the browser*, but the containerized
deployment (`asgi.py`) runs Flet as a server - the Python process itself has
a real disk. `asgi.py` bridges a durable per-browser `client_id` cookie into
`page.data` (see `utils/client_context.py`), and `make_session_store()`
below uses that to pick `_ServerFileStore` (one JSON file per browser,
same reliable sync I/O as native) over `SharedPreferences` whenever it's
available. The plain `flet run --web` CLI (local dev) has no such bridge, so
it still falls back to `SharedPreferences` with the existing fail-fast
retry - real log evidence (`frontend/src/storage/data/sfsis.log`) shows
that path failing routinely, not just on cold start, which is exactly what
the cookie bridge exists to avoid for the deployment that actually matters.

Both file stores live in the OS user-data dir, deliberately **outside** the
project/app source tree: `flet run -r` watches the app dir recursively and a
write inside it would trigger a hot-reload restart - the very failure we're
trying to survive.
"""
import json
import os
import sys
from pathlib import Path

from utils.storage_compat import sp_call_with_retry


def _native_store_path() -> Path:
    """A writable, persistent JSON path in the OS user-data dir.

    Never returns a path inside the project tree (see module docstring).
    """
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")

    store_dir = Path(base) / "sfsis"
    store_dir.mkdir(parents=True, exist_ok=True)
    return store_dir / "session.json"


class _JsonFileStore:
    """Synchronous JSON-file key/value store - a plain sync file write
    can't time out the way a not-yet-mounted browser service can, so this
    backs both `_NativeFileStore` (one file per install) and
    `_ServerFileStore` (one file per browser client_id, for the web ASGI
    deployment - see asgi.py)."""

    def __init__(self, path: Path):
        self._path = path
        self._data = self._read_all()

    def _read_all(self) -> dict:
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except (FileNotFoundError, ValueError, OSError):
            return {}

    def _write_all(self):
        # Atomic replace so a crash mid-write can't corrupt the session file.
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._data), encoding="utf-8")
        os.replace(tmp, self._path)

    async def load(self, key: str):
        return self._data.get(key)

    def persist(self, key: str, value):
        self._data[key] = value
        try:
            self._write_all()
        except OSError as e:
            print(f"Could not persist {key} to session file: {e}")

    def forget(self, key: str):
        if key in self._data:
            self._data.pop(key, None)
            try:
                self._write_all()
            except OSError as e:
                print(f"Could not remove {key} from session file: {e}")


class _NativeFileStore(_JsonFileStore):
    """One session file per install - fine on native, where only one user
    is ever using a given install at a time."""

    def __init__(self):
        super().__init__(_native_store_path())


class _ServerFileStore(_JsonFileStore):
    """One session file per browser, keyed by the `client_id` cookie
    asgi.py bridges into `page.data` (see that module's docstring and
    utils/client_context.py). Unlike a single shared file, this keeps
    concurrent users of the same containerized web deployment from
    clobbering each other's login."""

    def __init__(self, client_id: str):
        store_dir = _native_store_path().parent / "sessions"
        store_dir.mkdir(parents=True, exist_ok=True)
        # client_id is a uuid4().hex asgi.py generated itself - always
        # filesystem-safe, no sanitization needed.
        super().__init__(store_dir / f"{client_id}.json")


class _WebSharedPrefsStore:
    """SharedPreferences-backed store for web mode (async, fail-fast)."""

    def __init__(self, page, sp):
        self._page = page
        self._sp = sp

    async def load(self, key: str):
        return await sp_call_with_retry(self._sp.get, key)

    def persist(self, key: str, value):
        # Web can't do durable sync writes; keep the existing fire-and-forget.
        self._page.run_task(self._async_persist, key, value)

    async def _async_persist(self, key: str, value):
        try:
            await sp_call_with_retry(self._sp.set, key, value)
        except Exception as e:
            print(f"Could not persist {key} to client_storage: {e}")

    def forget(self, key: str):
        self._page.run_task(self._async_forget, key)

    async def _async_forget(self, key: str):
        try:
            await sp_call_with_retry(self._sp.remove, key)
        except Exception as e:
            print(f"Could not remove {key} from client_storage: {e}")


def make_session_store(page, sp=None):
    """Pick the persistence backend for the current platform/deployment.

    - Web, served through asgi.py's cookie bridge (`client_id` present in
      `page.data`, set by its `before_main` - see utils/client_context.py)
      → a per-browser server-side JSON file (`_ServerFileStore`). Reliable
      sync file I/O, no async browser-service round trip to race, and safe
      for multiple concurrent users of the same container.
    - Web, served through the plain `flet run --web` CLI (local dev, no
      cookie bridge, no `client_id`) → SharedPreferences, same as before.
    - Native (desktop/Android/iOS) → one JSON file (single-install, no
      concurrent-user concern).
    """
    is_web = bool(getattr(page, "web", False))
    if is_web:
        client_id = None
        if hasattr(page, "data") and isinstance(page.data, dict):
            client_id = page.data.get("client_id")
        if client_id:
            return _ServerFileStore(client_id)
        if sp is not None:
            return _WebSharedPrefsStore(page, sp)
    return _NativeFileStore()
