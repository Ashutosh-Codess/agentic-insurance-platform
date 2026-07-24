"""
Everything security-related lives in this one file on purpose, matching
the flat architecture you asked for: password hashing, JWT creation and
decoding, and the two FastAPI dependencies every protected route uses --
`get_current_user` and `require_role`. No hidden auth logic anywhere else
in the codebase; if a route is protected, it says so explicitly in its
own signature via one of these two dependencies.
"""
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=True)


# ---------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------

def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# ---------------------------------------------------------------------
# JWT access tokens
# ---------------------------------------------------------------------

def create_access_token(*, user_id: str, role: str) -> str:
    """Role is normalized to lowercase/stripped BEFORE it goes into the
    token, so the token itself can never carry a whitespace/case variant
    that would silently fail a role check later."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "role": role.strip().lower(),
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Raises jose.JWTError on invalid/expired/wrong-type token."""
    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    if payload.get("type") != "access":
        raise JWTError("Not an access token")
    return payload


# ---------------------------------------------------------------------
# Refresh tokens (opaque, stored hashed -- see models/user.py RefreshToken)
# ---------------------------------------------------------------------

def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(raw_token: str) -> str:
    return pwd_context.hash(raw_token)


def verify_refresh_token(raw_token: str, hashed_token: str) -> bool:
    return pwd_context.verify(raw_token, hashed_token)


def refresh_token_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)


# ---------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    """
    Decodes the bearer token, loads the matching User row fresh from a
    brand-new per-request session (see get_db — there is no session reuse
    or caching across requests, so a "stale user object" bug is not
    possible here), and returns it.
    """
    from app.models.user import User  # local import avoids a circular import with models -> db -> core

    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired access token")

    user_id = payload.get("sub")
    try:
        user_uuid = uuid.UUID(user_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")

    user = db.get(User, user_uuid)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    return user


def require_role(*allowed_roles: str):
    """
    Usage: Depends(require_role("agent", "admin"))

    Both sides of the comparison are normalized (stripped + lowercased)
    so a role value with incidental whitespace or casing -- from a manual
    DB edit, a different seeding path, anything -- can never cause a
    false-negative 403. This is a defensive fix for a real class of bug,
    not just a style choice.
    """
    normalized_allowed = {r.strip().lower() for r in allowed_roles}

    def _check(current_user=Depends(get_current_user)):
        actual_role = (current_user.role or "").strip().lower()
        if actual_role not in normalized_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Requires one of roles: {', '.join(sorted(normalized_allowed))} "
                    f"(user has role: '{current_user.role}')"
                ),
            )
        return current_user

    return _check
