"""Authentication core — password hashing + JWT tokens.

Uses bcrypt directly (avoids passlib 1.7.4 / bcrypt 5.0 version-detection bug).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import JWTError, jwt

from app.config import settings


# ═══ Password hashing ═══

def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt."""
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# ═══ JWT tokens ═══

def create_access_token(subject: str, expires_minutes: Optional[int] = None) -> str:
    """Create a signed JWT access token with `sub` = user id."""
    expire_min = expires_minutes or settings.jwt_expire_minutes
    expire = datetime.now(timezone.utc) + timedelta(minutes=expire_min)
    payload = {"sub": subject, "exp": expire, "iat": datetime.now(timezone.utc)}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> Optional[str]:
    """Decode a JWT token and return the subject (user id), or None if invalid."""
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        return payload.get("sub")
    except JWTError:
        return None
