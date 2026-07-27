"""App-wide timezone handling (issue #47).

Every model's `created_at`/`updated_at` is stored as UTC (via `AwareDateTime`
below + a Python-side `utcnow()` default — see AGENTS.md's "Timestamps and
timezone handling" for why this replaced the old DB-clock-dependent
`server_default=func.now()`), so the app's behavior no longer depends on
whatever timezone the host machine or database container happens to be
running in. `APP_TIMEZONE` (core/config.py) is only the *boot-time default*
for a fresh install — the live, admin-editable setting is the `app_configs`
singleton row's own `timezone` column (see `master_config`), read here on
every call rather than cached, since it can change at runtime without a
restart.
"""

from datetime import datetime, timezone
from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, available_timezones

from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator

from core import config


def utcnow() -> datetime:
    """Python-side default/onupdate for every `AwareDateTime` column - always
    timezone-aware UTC, never the naive host-local `datetime.now()`."""
    return datetime.now(timezone.utc)


class AwareDateTime(TypeDecorator):
    """Stores a timezone-aware Python `datetime` as UTC, regardless of what
    zone it was constructed in - and always returns one back (never a naive
    `datetime`) on read.

    MariaDB/MySQL has no native `TIMESTAMP WITH TIME ZONE` the way Postgres
    does - SQLAlchemy's `DateTime(timezone=True)` is a silent no-op on this
    dialect, it does not make the column itself timezone-aware. So this type
    does the conversion itself at the Python/DB boundary: `process_bind_param`
    converts an aware value to UTC and strips its tzinfo before handing it to
    the driver (the underlying `DATETIME` column physically cannot store
    tzinfo); `process_result_value` re-attaches `UTC` on the way back out, so
    application code always deals in aware UTC datetimes, never naive ones
    that could be misread as local time.
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError(
                "AwareDateTime requires a timezone-aware datetime - got a "
                "naive one. Use core.timezone.utcnow() instead of a naive "
                "datetime.now()/datetime.utcnow()."
            )
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value


def get_app_timezone() -> ZoneInfo:
    """The currently-configured app timezone - reads the live `app_configs`
    row's `timezone` column (falling back to `config.APP_TIMEZONE`, the
    boot-time env default, if the row/column is unset or holds an
    unrecognized IANA name). Queried fresh each call rather than cached at
    import time, since an admin can change this at runtime via
    `master_config` with no restart needed.

    Imports `AppConfigRepository` lazily to avoid a import-time cycle
    (`repository` -> `models` -> `models.base` -> `core.config`; this module
    itself only needs `core.config`, but importing the repository at module
    scope would still work today - kept lazy anyway since this function is
    the only thing in this module that needs it)."""
    from repository.app_config_repository import AppConfigRepository

    app_config = AppConfigRepository().get_config()
    name = getattr(app_config, "timezone", None) if app_config else None
    if name:
        try:
            return ZoneInfo(name)
        except ZoneInfoNotFoundError:
            pass
    return config.APP_TIMEZONE


def to_app_timezone(value: datetime) -> datetime:
    """Convert an aware UTC `datetime` (as returned by `AwareDateTime`) into
    the currently-configured app timezone."""
    return value.astimezone(get_app_timezone())


def isoformat_app_timezone(value: datetime) -> str:
    """`to_app_timezone(value).isoformat()`, for a router serializing a
    `created_at`/`updated_at` field straight into a JSON response - the
    frontend's existing display formatting needs no changes since the value
    already arrives in the configured zone, not raw UTC."""
    return to_app_timezone(value).isoformat()


@lru_cache(maxsize=1)
def common_timezones() -> list[str]:
    """A curated subset of `zoneinfo.available_timezones()` for the
    `master_config` screen's timezone picker - the full set includes
    deprecated aliases and non-geographic buckets (`Etc/GMT+5`, `posix/...`,
    `right/...`, bare abbreviations with no `/`) that would make a very long
    dropdown mostly noise. Mirrors the same filtering approach `pytz.
    common_timezones` uses, without adding a `pytz` dependency just for this
    one list. Cached (per-process) since `available_timezones()` scans the
    whole tzdata directory on every call.
    """
    names = {
        name
        for name in available_timezones()
        if "/" in name
        and not name.startswith(("Etc/", "posix/", "right/", "SystemV/"))
    }
    names.add("UTC")
    return sorted(names)
