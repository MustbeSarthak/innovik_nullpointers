"""Password hashing and JWT access-token helpers.

Only the standard ``bcrypt`` library and ``PyJWT`` are used, which keeps the
security surface small and easy to audit.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from backend.core.config import settings

# bcrypt silently truncates inputs longer than 72 bytes, so requests are
# rejected up-front instead of producing surprising hashes.
MAX_PASSWORD_BYTES = 72


class SecurityError(ValueError):
    """Raised when a password or token cannot be processed."""


def hash_password(password: str) -> str:
    """Hash ``password`` with bcrypt and return the encoded digest."""
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > MAX_PASSWORD_BYTES:
        raise SecurityError(
            f"password must not exceed {MAX_PASSWORD_BYTES} bytes when UTF-8 encoded"
        )
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return ``True`` when ``plain_password`` matches ``hashed_password``."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), hashed_password.encode("utf-8")
        )
    except (ValueError, TypeError):
        # Malformed hash in the database - treat as a failed login.
        return False


def create_access_token(
    subject: str | int, expires_delta: timedelta | None = None
) -> str:
    """Create a signed JWT whose ``sub`` claim is ``subject``."""
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode ``token`` and return its claims.

    Raises:
        SecurityError: when the token is expired, tampered with or malformed.
    """
    try:
        return jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
    except jwt.ExpiredSignatureError as exc:  # pragma: no cover - trivial branch
        raise SecurityError("access token has expired") from exc
    except jwt.PyJWTError as exc:
        raise SecurityError("invalid access token") from exc
