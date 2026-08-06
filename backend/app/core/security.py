"""
JWT creation/validation and password hashing.
"""
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str, extra_claims: dict[str, Any] | None = None) -> str:
    """
    Create a signed JWT. `subject` is the user id (as string).
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode: dict[str, Any] = {"sub": subject, "iat": now, "exp": expire}
    if extra_claims:
        to_encode.update(extra_claims)
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


class TokenPayloadError(Exception):
    """Raised when a JWT is invalid, expired, or malformed."""


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise TokenPayloadError(str(exc)) from exc
    if "sub" not in payload:
        raise TokenPayloadError("Token missing 'sub' claim")
    return payload
