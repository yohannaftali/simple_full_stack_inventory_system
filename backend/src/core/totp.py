"""TOTP (RFC 6238): Python port of the legacy PHP `L_totp` library.

SHA1 HMAC, 6 digits, 30s period, +/-1 step drift tolerance — same parameters as the
PHP original. QR-image rendering is intentionally not ported: the frontend builds the
`otpauth://` URI itself and renders the QR code client-side, so the backend only needs
to hand out the raw secret.
"""

import base64
import hashlib
import hmac
import os
import struct
import time
import urllib.parse


def generate_secret() -> str:
    """Generate a new random Base32 TOTP secret (160-bit, matching SHA1 HMAC entropy)."""
    return base64.b32encode(os.urandom(20)).decode("utf-8").rstrip("=")


def get_totp_uri(username: str, secret: str, issuer: str = "SFSIS") -> str:
    """Build the otpauth:// URI consumed by authenticator apps."""
    if not secret:
        return ""
    label = urllib.parse.quote(f"{issuer}:{username}", safe="")
    return (
        f"otpauth://totp/{label}"
        f"?secret={urllib.parse.quote(secret, safe='')}"
        f"&issuer={urllib.parse.quote(issuer, safe='')}"
        "&algorithm=SHA1&digits=6&period=30"
    )


def _decode_secret(secret: str) -> bytes:
    cleaned = secret.strip().upper().replace(" ", "")
    padding = "=" * ((8 - len(cleaned) % 8) % 8)
    return base64.b32decode(cleaned + padding, casefold=True)


def _compute_totp(secret: str, time_step: int) -> str:
    key = _decode_secret(secret)
    msg = struct.pack(">Q", time_step)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[19] & 0x0F
    code = (
        (digest[offset] & 0x7F) << 24
        | (digest[offset + 1] & 0xFF) << 16
        | (digest[offset + 2] & 0xFF) << 8
        | (digest[offset + 3] & 0xFF)
    ) % 1_000_000
    return str(code).zfill(6)


def verify(secret: str, totp: str) -> bool:
    """Verify a 6-digit TOTP code, allowing +/-1 step (~30s) of clock drift."""
    if not secret:
        return True  # No secret means 2FA is not set up, so we consider it valid.
    step = int(time.time() // 30)
    return any(
        hmac.compare_digest(_compute_totp(secret, step + drift), str(totp))
        for drift in (-1, 0, 1)
    )
