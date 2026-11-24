"""Password hashing with scrypt (salted, memory-hard, part of the standard library)."""

import hashlib
import hmac
import os

_PARAMETERS = {"n": 2**14, "r": 8, "p": 1}


def hash_password(password: str) -> str:
    """Return 'salt$hash' in hexadecimal."""
    salt = os.urandom(16)
    return f"{salt.hex()}${hashlib.scrypt(password.encode(), salt=salt, **_PARAMETERS).hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Compare in constant time."""
    salt, expected = (bytes.fromhex(part) for part in stored.split("$"))
    return hmac.compare_digest(hashlib.scrypt(password.encode(), salt=salt, **_PARAMETERS), expected)
