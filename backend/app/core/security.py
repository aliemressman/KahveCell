import hashlib
import hmac
import secrets

_HASH_ALGORITHM = "pbkdf2_sha256"
_HASH_ITERATIONS = 600_000
_SALT_BYTES = 16


def hash_password(password: str) -> str:
    if not password:
        raise ValueError("Password cannot be empty.")

    salt = secrets.token_bytes(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        _HASH_ITERATIONS,
    )
    return f"{_HASH_ALGORITHM}${_HASH_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations_text, salt_hex, digest_hex = stored_hash.split("$", 3)
        iterations = int(iterations_text)
        salt = bytes.fromhex(salt_hex)
        expected_digest = bytes.fromhex(digest_hex)
    except (AttributeError, ValueError):
        return False

    if algorithm != _HASH_ALGORITHM or not 100_000 <= iterations <= 1_000_000:
        return False

    actual_digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(actual_digest, expected_digest)
