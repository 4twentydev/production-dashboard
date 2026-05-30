from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from collections.abc import MutableMapping

from .config import DEFAULT_SETTINGS
from .db import get_security_state, update_security_state

PBKDF2_ITERATIONS = 210_000


def hash_pin(pin: str, *, salt: bytes | None = None) -> tuple[str, str]:
    salt_bytes = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        pin.encode("utf-8"),
        salt_bytes,
        PBKDF2_ITERATIONS,
    )
    return salt_bytes.hex(), digest.hex()


def is_pin_configured() -> bool:
    state = get_security_state()
    return bool(state.get("pin_hash") and state.get("pin_salt"))


def set_pin(pin: str) -> None:
    salt_hex, hash_hex = hash_pin(pin)
    update_security_state(
        pin_salt=salt_hex,
        pin_hash=hash_hex,
        failed_attempts=0,
        lockout_until=None,
        last_unlocked_at=None,
    )


def _lockout_until_seconds() -> float | None:
    state = get_security_state()
    value = state.get("lockout_until")
    if not value:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def pin_is_locked() -> bool:
    lockout = _lockout_until_seconds()
    return lockout is not None and time.time() < lockout


def verify_pin(pin: str) -> bool:
    state = get_security_state()
    if pin_is_locked():
        return False
    salt_hex = state.get("pin_salt")
    hash_hex = state.get("pin_hash")
    if not salt_hex or not hash_hex:
        return False
    salt = bytes.fromhex(str(salt_hex))
    _, candidate = hash_pin(pin, salt=salt)
    matched = hmac.compare_digest(candidate, str(hash_hex))
    if matched:
        update_security_state(failed_attempts=0, lockout_until=None, last_unlocked_at=str(time.time()))
        return True
    failed_attempts = int(state.get("failed_attempts") or 0) + 1
    lockout_until = state.get("lockout_until")
    if failed_attempts >= 5:
        try:
            minutes = int(DEFAULT_SETTINGS.get("pin_lockout_minutes", "10"))
        except ValueError:
            minutes = 10
        lockout_until = time.time() + (minutes * 60)
    update_security_state(failed_attempts=failed_attempts, lockout_until=lockout_until)
    return False


def register_unlock(storage: MutableMapping[str, object], *, minutes: int) -> None:
    storage["pin_unlocked_until"] = time.time() + (minutes * 60)
    storage["pin_unlocked_at"] = time.time()


def lock_session(storage: MutableMapping[str, object]) -> None:
    storage.pop("pin_unlocked_until", None)
    storage.pop("pin_unlocked_at", None)


def is_unlocked(storage: MutableMapping[str, object]) -> bool:
    expires = storage.get("pin_unlocked_until")
    if not expires:
        return False
    try:
        return time.time() < float(expires)
    except (TypeError, ValueError):
        return False


def pin_required_message() -> str:
    if pin_is_locked():
        return "PIN temporarily locked due to failed attempts."
    return "PIN required."
