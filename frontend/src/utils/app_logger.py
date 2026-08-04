"""App-wide log capture for the Troubleshooting page.

The app has no structured logging today - it's all scattered `print()`
calls. Rather than refactor every call site, this module patches
`builtins.print` to also feed an in-memory ring buffer (and, when a
writable app directory is available, a rotating log file), so the
Troubleshooting page's "Show Logs" button has something to display -
including in a packaged/production build where there's no attached
terminal to read `flet run` output from.

Deliberately does NOT touch sys.stdout/sys.stderr themselves: an earlier
version of this module replaced them with a custom stream object, which
turned out to break silently whenever something other than a plain
print() touched the stream - notably asyncio's own internal exception
reporting (e.g. a failing task scheduled via `page.run_task`) and Flet's
messaging layer both write to the real stdout/stderr directly, and a
custom stream missing some expected behavior there can swallow the
exception entirely instead of printing it, making the app look like it
just silently stopped. Patching `print` itself avoids that risk - every
other consumer of the streams keeps using the untouched, real objects.

Per-client-session scoped (see AGENTS.md's "App Logs Are a Security
Boundary" guardrail, issue #80): a single container process serves every
concurrent web session, so a process-global log buffer/file used to mean
one user's captured print() output (including, before issue #80's own
redaction fix, credentials) was readable by any other logged-in user.
Every log line is now bucketed by `utils.client_context.client_id_var` -
the same per-connection id `asgi.py`'s middleware already threads through
for session persistence - so each web session gets its own isolated
memory buffer and on-disk file. Desktop/mobile builds never set that
ContextVar (it's only populated by the ASGI deployment path), so they
fall back to one shared `_GLOBAL_KEY` bucket - correct there, since a
desktop/mobile process is already single-user by construction.
"""

import builtins
import logging
import logging.handlers
import os
import tempfile
from collections import deque
from pathlib import Path

from utils.client_context import client_id_var

_MAX_MEMORY_LINES = 2000
# Caps how many distinct web clients' buffers/file handles this process
# tracks over its lifetime - without a bound, a long-lived container
# serving many short-lived browser sessions would leak memory/file
# handles for clients that never come back to clear their own bucket.
_MAX_TRACKED_CLIENTS = 200

_GLOBAL_KEY = "__global__"  # desktop/mobile, or no session context yet

_memory_logs: dict[str, deque] = {}
_file_handlers: dict[str, logging.handlers.RotatingFileHandler] = {}
_configured = False
_original_print = print
_formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"
)


def _log_dir() -> Path:
    """Writable, per-app directory.

    Flet's CLI (`flet run`) sets FLET_APP_STORAGE_DATA to a
    platform-appropriate app data directory for both dev and packaged
    builds (see flet_cli/commands/run.py) - this is the same mechanism
    backing this project's local `storage/data` dev folder. Falls back to
    a temp dir if unset (e.g. running main.py directly, without the flet
    CLI wrapper).
    """
    base = os.environ.get("FLET_APP_STORAGE_DATA") or os.environ.get(
        "FLET_APP_STORAGE_TEMP"
    )
    if base:
        return Path(base)
    return Path(tempfile.gettempdir()) / "sfsis_flet"


def _bucket_key(client_id: str | None = None) -> str:
    """Resolve which bucket a log line/lookup belongs to. `client_id`,
    when given explicitly (Troubleshooting page, logout), always wins;
    otherwise falls back to whatever the ASGI connection context has set
    (see module docstring) or the shared desktop/mobile bucket."""
    if client_id:
        return client_id
    return client_id_var.get() or _GLOBAL_KEY


def _log_path_for(key: str) -> Path:
    log_dir = _log_dir()
    if key == _GLOBAL_KEY:
        return log_dir / "sfsis.log"
    return log_dir / "sessions" / f"{key}.log"


def _get_file_handler(key: str) -> logging.handlers.RotatingFileHandler | None:
    handler = _file_handlers.get(key)
    if handler is not None:
        return handler
    try:
        log_path = _log_path_for(key)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.handlers.RotatingFileHandler(
            log_path, maxBytes=1_000_000, backupCount=2, encoding="utf-8"
        )
        handler.setFormatter(_formatter)
    except OSError as e:
        logging.getLogger("sfsis").warning(f"Could not set up file logging for {key}: {e}")
        return None
    _file_handlers[key] = handler
    return handler


def _evict_if_over_capacity():
    """Drop the oldest tracked non-global client bucket once the process
    has accumulated more than `_MAX_TRACKED_CLIENTS` of them - a client
    that reconnects after eviction just starts a fresh, empty bucket
    (same as a brand-new session), never crosses into another client's."""
    if len(_memory_logs) <= _MAX_TRACKED_CLIENTS:
        return
    for key in list(_memory_logs.keys()):
        if key == _GLOBAL_KEY:
            continue
        del _memory_logs[key]
        old_handler = _file_handlers.pop(key, None)
        if old_handler is not None:
            old_handler.close()
        break


class _MemoryHandler(logging.Handler):
    """Keeps the last N formatted log lines in memory, per bucket."""

    def emit(self, record: logging.LogRecord):
        try:
            key = _bucket_key()
            bucket = _memory_logs.setdefault(key, deque(maxlen=_MAX_MEMORY_LINES))
            bucket.append(self.format(record))
            _evict_if_over_capacity()
        except Exception:
            pass


class _PerClientFileHandler(logging.Handler):
    """Routes each record to the on-disk file for its current bucket."""

    def emit(self, record: logging.LogRecord):
        try:
            handler = _get_file_handler(_bucket_key())
            if handler is not None:
                handler.emit(record)
        except Exception:
            pass


def _patched_print(*args, **kwargs):
    try:
        message = " ".join(str(a) for a in args)
        if message.strip():
            logging.getLogger("sfsis").info(message)
    except Exception:
        pass
    _original_print(*args, **kwargs)


def setup_logging():
    """Wire up the file + memory handlers and patch `print`. Idempotent -
    call once, as early as possible in main.py."""
    global _configured
    if _configured:
        return
    _configured = True

    logger = logging.getLogger("sfsis")
    logger.setLevel(logging.INFO)
    logger.addHandler(_MemoryHandler())
    logger.addHandler(_PerClientFileHandler())

    builtins.print = _patched_print


def get_recent_logs(client_id: str | None = None, n: int = 500) -> str:
    """Return the last `n` captured log lines for this bucket."""
    key = _bucket_key(client_id)
    lines = list(_memory_logs.get(key, ()))[-n:]
    return "\n".join(lines) if lines else "(no logs captured yet)"


def get_log_file_path(client_id: str | None = None) -> Path | None:
    """Return the on-disk log file path for this bucket, if file logging
    is active for it (i.e. at least one line has been written there)."""
    key = _bucket_key(client_id)
    handler = _file_handlers.get(key)
    return Path(handler.baseFilename) if handler is not None else None


def clear_logs(client_id: str | None = None):
    """Clear the in-memory ring buffer and on-disk log file for this
    bucket only - never another session's. Called on logout (see
    components/home/user_menu.py) so a session's captured logs don't
    persist past it, on any platform: desktop/mobile share one process
    with one user, and each web session now owns its own isolated bucket
    (see module docstring), so clearing here can never affect another
    user's logs. Swallows any file error, since a logout must never fail
    because of this housekeeping step."""
    key = _bucket_key(client_id)
    _memory_logs.pop(key, None)
    handler = _file_handlers.pop(key, None)
    if handler is None:
        return
    log_path = Path(handler.baseFilename)
    handler.close()
    try:
        log_path.write_text("", encoding="utf-8")
    except OSError as e:
        logging.getLogger("sfsis").warning(f"Could not clear log file for {key}: {e}")
