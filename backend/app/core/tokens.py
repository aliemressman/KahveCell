import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import jwt

_SECRET_PATH = Path(__file__).resolve().parents[2] / "data" / "jwt_secret.key"
_ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 15
REFRESH_TOKEN_DAYS = 30


def _load_secret_key() -> str:
    environment_key = os.getenv("KAHVECELL_JWT_SECRET")
    if environment_key:
        if len(environment_key) < 32:
            raise RuntimeError("KAHVECELL_JWT_SECRET must be at least 32 characters.")
        return environment_key

    _SECRET_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        with _SECRET_PATH.open("x", encoding="ascii") as secret_file:
            secret_file.write(secrets.token_urlsafe(48))
    except FileExistsError:
        pass

    secret_key = _SECRET_PATH.read_text(encoding="ascii").strip()
    if len(secret_key) < 32:
        raise RuntimeError(f"JWT secret file is invalid: {_SECRET_PATH}")
    return secret_key


JWT_SECRET_KEY = _load_secret_key()


def create_token(
    subject: str,
    token_type: str,
    lifetime: timedelta,
    token_id: str | None = None,
) -> tuple[str, datetime]:
    now = datetime.now(timezone.utc)
    expires_at = now + lifetime
    claims: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": expires_at,
    }
    if token_id is not None:
        claims["jti"] = token_id
    return jwt.encode(claims, JWT_SECRET_KEY, algorithm=_ALGORITHM), expires_at


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, JWT_SECRET_KEY, algorithms=[_ALGORITHM])
