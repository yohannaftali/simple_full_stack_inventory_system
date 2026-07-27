"""Pre-auth session token: Python port of the legacy PHP `sha1(md5(...))` scheme.

Token = sha1(md5(ip_2 + username + "HHmm" + ip_1 + JWT_SECRET)), where "HHmm" is the
current hour+minute (zero-padded 24h). A token is valid if it matches the current
minute or either of the two preceding minutes, giving a short-lived (~2-3 min) window.
"""

import hashlib
from datetime import datetime, timedelta

from core.config import JWT_SECRET


def _minute_stamp(offset_minutes: int = 0) -> str:
    # Deliberately naive/local-clock (issue #47 explicitly excludes this
    # function): the client computes the same token from its own local
    # clock, so this must track whatever wall-clock the two sides already
    # agree on, not the app's configured display timezone - switching this
    # to UTC or core.timezone.utcnow() would break the token match unless
    # the client-side generator changed identically.
    return (datetime.now() - timedelta(minutes=offset_minutes)).strftime("%H%M")


def _hash_session(username: str, ip_1: str, ip_2: str, time_stamp: str) -> str:
    raw = f"{ip_2}{username}{time_stamp}{ip_1}{JWT_SECRET}"
    md5_hex = hashlib.md5(raw.encode("utf-8")).hexdigest()
    return hashlib.sha1(md5_hex.encode("utf-8")).hexdigest()


def get_session_token(username: str, ip_1: str, ip_2: str) -> str:
    """Generate the current-minute pre-auth token for a username/IP pair."""
    return _hash_session(username, ip_1, ip_2, _minute_stamp())


def is_valid_session_token(username: str, ip_1: str, ip_2: str, token: str) -> bool:
    """Accept the token if it matches this minute or either of the previous two."""
    return any(
        token == _hash_session(username, ip_1, ip_2, _minute_stamp(offset))
        for offset in range(3)
    )
