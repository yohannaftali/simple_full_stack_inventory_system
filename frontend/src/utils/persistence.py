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
race), so a restart mid-navigation no longer logs the user out. Only **web**
mode (no local filesystem) keeps using SharedPreferences, with the existing
fail-fast retry.

The native file lives in the OS user-data dir, deliberately **outside** the
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


class _NativeFileStore:
    """Synchronous JSON-file key/value store for native platforms."""

    def __init__(self):
        self._path = _native_store_path()
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
    """Pick the persistence backend for the current platform.

    Native (desktop/Android/iOS) → reliable JSON file. Web → SharedPreferences.
    Defaults to native unless `page.web` is explicitly True, since file storage
    is safe everywhere except web (no filesystem).
    """
    if bool(getattr(page, "web", False)) and sp is not None:
        return _WebSharedPrefsStore(page, sp)
    return _NativeFileStore()
