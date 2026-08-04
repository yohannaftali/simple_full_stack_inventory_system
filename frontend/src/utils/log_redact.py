"""Shared credential redaction for anything printed to the app log.

Everything printed via `print()` lands in `utils/app_logger.py`'s shared
ring buffer/log file - on web that's a process-global singleton readable
by every concurrent session's Troubleshooting page (issue #80) and by
anyone with container log access, so credentials must never reach it in
plain text, on any platform.
"""

# Field names never printed in plain text - matched case-insensitively.
# Forms use short, endpoint-specific field names (c/n/f, ct/nt/ft, _tok)
# that don't match any generic keyword here; those call sites pass their
# own `sensitive_keys` instead of being folded into this default set, to
# avoid silently swallowing an unrelated future field that happens to be
# named "c" or "n".
DEFAULT_SENSITIVE_KEYS = {
    "password",
    "new_password",
    "current_password",
    "confirm_password",
    "totp",
    "secret",
    "token",
    "tok",
    "_tok",
    "pwd",
    "apikey",
    "api_key",
}


def redact_for_log(data: dict | None, sensitive_keys: set | None = None) -> dict | None:
    """Return a copy of `data` with sensitive values masked, for logging
    only - the caller's real, unmodified `data` is unaffected."""
    if not isinstance(data, dict):
        return data
    keys = DEFAULT_SENSITIVE_KEYS | (sensitive_keys or set())
    return {
        k: ("***" if str(k).lower() in keys else v) for k, v in data.items()
    }
