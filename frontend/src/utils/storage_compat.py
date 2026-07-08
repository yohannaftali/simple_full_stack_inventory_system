"""
Compatibility helpers for values persisted by the pre-0.85 Flet client_storage
"""
import asyncio
import json


async def sp_call_with_retry(
    coro_func,
    *args,
    retries: int = 2,
    delay: float = 0.5,
    per_call_timeout: float = 2.0,
    **kwargs,
):
    """
    Call an async method that round-trips to the client, failing fast and
    retrying. Despite the name, nothing here is SharedPreferences-specific -
    it wraps any bound async callable (e.g. `page.push_route`) in the same
    fail-fast-and-retry shape.

    SharedPreferences is registered as a page service and the client needs a
    moment to mount it and register its method-channel listener. Invoking a
    method before that mount completes raises a client-side "Timeout waiting
    for invoke method listener" error. On native platforms (desktop, Android,
    iOS) the Flutter engine is in-process, so this mount is effectively
    instant and the first call succeeds immediately. In **web mode**
    (`flet run --web`), however, the JS-side listener registration over the
    WebSocket handshake is unreliable and frequently never completes for a
    given service instance - a known upstream Flet bug (flet-dev/flet#6250 /
    #6251, same issue as web-mode FilePicker/UrlLauncher), with no
    `ensure_ready()`-style hook to wait on. In that broken-web case the call
    can never succeed no matter how long we wait.

    The client's own internal wait is ~10s per call, so naively awaiting each
    call makes startup hang for ~10s x (retries) x (number of keys) in web
    mode. To keep startup responsive we wrap each attempt in a short
    `per_call_timeout` (via `asyncio.wait_for`) so a not-yet-ready client
    fails in ~2s instead of ~10s, and cap `retries` low so the whole thing
    degrades to defaults within a few seconds. Callers should
    `asyncio.gather` independent loads (see `Storage.load_persistent`) so the
    worst-case cost is one key's budget, not the sum of all keys. On native,
    where the first attempt succeeds in milliseconds, none of this backoff is
    exercised.

    #648 note: users testing with `flet run -r` (hot-reload, the default in
    `run.ps1`) have observed these calls succeed reliably once a module has
    already been navigated to/imported once, but fail on a session's first
    navigation to a not-yet-imported module. This is **not** import blocking
    the event loop racing this specific call - `Storage.load_persistent()`
    (in `main.py`) always fully completes before `ModuleLoader` is even
    constructed, let alone before any module import, so no import can run
    concurrently with these calls. The actual explanation is almost certainly
    that "module already cached" is a proxy for "this `main()` run reused an
    already-connected client from a prior hot-reload restart" (module cache
    is a class-level dict that survives `-r` restarts within the same
    process) - the client's SharedPreferences listener was already mounted
    from before, vs. a colder connection still inside the race window
    described above. See the `[#648]` diagnostic print in `main.py` for a
    way to confirm this correlation directly in the logs.

    Args:
        coro_func: Bound async method to call, e.g. `sp.get`.
        *args: Positional arguments to pass to `coro_func`.
        retries: Number of retry attempts after the first failed call.
        delay: Seconds to wait between attempts.
        per_call_timeout: Max seconds to wait for a single attempt before
            treating it as failed (bounds the client's ~10s internal wait).
        **kwargs: Keyword arguments to pass to `coro_func`.

    Returns:
        Whatever `coro_func` returns.

    Raises:
        The last exception encountered, if every attempt fails.
    """
    last_exc = None
    for attempt in range(retries + 1):
        try:
            return await asyncio.wait_for(
                coro_func(*args, **kwargs), timeout=per_call_timeout
            )
        except Exception as e:
            last_exc = e
            if attempt < retries:
                await asyncio.sleep(delay)
    raise last_exc


def unwrap_legacy_value(value):
    """
    Unwrap a value that may have been double-JSON-encoded by the old
    (pre-0.85) Flet client_storage.

    client_storage always ran values through json.dumps() before persisting
    and json.loads() on the way out, so a plain string like
    "https://example.com" was stored on disk as the JSON text
    '"https://example.com"'. The 0.85 SharedPreferences service reads that
    same on-disk value back verbatim (no implicit decoding), so installs
    upgrading from a pre-0.85 version see the literal quotes/escaping until
    unwrapped once here.

    Args:
        value: The raw value returned by SharedPreferences.get()

    Returns:
        The unwrapped value if it was a legacy JSON-encoded string,
        otherwise the original value unchanged.
    """
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except (ValueError, TypeError):
            return value
        if isinstance(decoded, str):
            return decoded
    return value
