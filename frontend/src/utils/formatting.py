"""Shared display-formatting helpers for numbers/dates/times.

House style (unless a screen has an explicit reason to deviate): numbers are
shown with 2 decimal places and a thousand separator, right-aligned; dates
as "dd Mon yyyy" (e.g. "07 Aug 2026"); times as "HH:MM" (e.g. "15:10").
Used by `components/table/rows.py` (driven by a field's `"format"` key) and
available for any screen that needs to format a value by hand.
"""

from datetime import date, datetime, time


def format_number(value, decimals: int = 2) -> str:
    """Format a number with a thousand separator and fixed decimal places.
    Returns the original value as a string if it isn't numeric (or blank)."""
    if value is None or value == "":
        return ""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    return f"{number:,.{decimals}f}"


def _parse_datetime(value):
    if isinstance(value, (date, datetime)):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def format_date(value) -> str:
    """Format an ISO "YYYY-MM-DD" (or datetime) value as "dd Mon yyyy"."""
    if not value:
        return ""
    parsed = _parse_datetime(value)
    if parsed is None:
        return str(value)
    return parsed.strftime("%d %b %Y")


def format_time(value) -> str:
    """Format an ISO datetime/time value as "HH:MM"."""
    if not value:
        return ""
    if isinstance(value, time):
        return value.strftime("%H:%M")
    parsed = _parse_datetime(value)
    if parsed is None:
        try:
            parsed = time.fromisoformat(str(value))
        except ValueError:
            return str(value)
    return parsed.strftime("%H:%M")
