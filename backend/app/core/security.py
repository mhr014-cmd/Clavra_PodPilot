from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt, JWTError
import bcrypt
import hashlib
from fastapi import HTTPException, status
from app.config import settings


# ── Password helpers ──────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


# ── Token storage helpers (SHA-256, no 72-byte limit) ─────────────────────

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def verify_token_hash(token: str, token_hash: str) -> bool:
    return hashlib.sha256(token.encode("utf-8")).hexdigest() == token_hash


# ── Token creation ────────────────────────────────────────────────────────

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a short-lived JWT access token.
    Payload must include: sub (user_id), org_id, role
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.get_secret_key(), algorithm=settings.ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    """
    Create a long-lived JWT refresh token.
    Contains only user_id — minimal payload for security.
    """
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "type": "refresh"
    }
    return jwt.encode(payload, settings.get_secret_key(), algorithm=settings.ALGORITHM)


# ── Token verification ────────────────────────────────────────────────────

def verify_token(token: str, token_type: str = "access") -> dict:
    """
    Decode and validate a JWT token.
    Raises HTTP 401 on any failure.
    Returns the full decoded payload dict.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            settings.get_secret_key(),
            algorithms=[settings.ALGORITHM]
        )
        if payload.get("type") != token_type:
            raise credentials_exception
        return payload
    except JWTError:
        raise credentials_exception


def decode_access_token(token: str) -> dict:
    """Convenience wrapper — decode access token."""
    return verify_token(token, "access")


def decode_refresh_token(token: str) -> dict:
    """Convenience wrapper — decode refresh token."""
    return verify_token(token, "refresh")
