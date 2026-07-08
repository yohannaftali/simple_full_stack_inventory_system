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
"""

import builtins
import logging
import logging.handlers
import os
import tempfile
from collections import deque
from pathlib import Path

_MAX_MEMORY_LINES = 2000
_memory_log: deque = deque(maxlen=_MAX_MEMORY_LINES)
_configured = False
_log_file_path: Path | None = None
_original_print = print


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


class _MemoryHandler(logging.Handler):
    """Keeps the last N formatted log lines in memory for fast display."""

    def emit(self, record: logging.LogRecord):
        try:
            _memory_log.append(self.format(record))
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
    global _configured, _log_file_path
    if _configured:
        return
    _configured = True

    logger = logging.getLogger("sfsis")
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"
    )

    memory_handler = _MemoryHandler()
    memory_handler.setFormatter(formatter)
    logger.addHandler(memory_handler)

    try:
        log_dir = _log_dir()
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "sfsis.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_path, maxBytes=1_000_000, backupCount=2, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        _log_file_path = log_path
    except OSError as e:
        logger.warning(f"Could not set up file logging: {e}")

    builtins.print = _patched_print


def get_recent_logs(n: int = 500) -> str:
    """Return the last `n` captured log lines as a single string."""
    lines = list(_memory_log)[-n:]
    return "\n".join(lines) if lines else "(no logs captured yet)"


def get_log_file_path() -> Path | None:
    """Return the on-disk log file path, if file logging is active."""
    return _log_file_path
