"""
Auth business logic. Routers stay thin (parse request -> call a service
function -> return it) -- every rule about what's allowed to happen lives
here, in one readable place.
"""
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    refresh_token_expiry,
    verify_password,
    verify_refresh_token,
)
from app.models.user import RefreshToken, User
from app.schemas.user import LoginRequest, RegisterRequest, TokenResponse


def register_customer(db: Session, payload: RegisterRequest) -> User:
    """Public self-registration. ALWAYS creates role='customer' -- this is
    the only way a customer account is ever created. Agent/admin accounts
    only come from the seed script (see backend/seed.py)."""
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role="customer",
        full_name=payload.full_name,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _issue_tokens(db: Session, user: User) -> TokenResponse:
    access_token = create_access_token(user_id=str(user.id), role=user.role)

    raw_refresh = generate_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(raw_refresh),
            expires_at=refresh_token_expiry(),
        )
    )
    db.commit()

    return TokenResponse(access_token=access_token, refresh_token=raw_refresh)


def login(db: Session, payload: LoginRequest) -> TokenResponse:
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

    return _issue_tokens(db, user)


def refresh_access_token(db: Session, raw_refresh_token: str) -> str:
    candidates = (
        db.query(RefreshToken)
        .filter(RefreshToken.revoked.is_(False))
        .filter(RefreshToken.expires_at > datetime.now(timezone.utc))
        .all()
    )

    matched = None
    for candidate in candidates:
        if verify_refresh_token(raw_refresh_token, candidate.token_hash):
            matched = candidate
            break

    if matched is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")

    user = db.get(User, matched.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    return create_access_token(user_id=str(user.id), role=user.role)


def logout(db: Session, raw_refresh_token: str) -> None:
    candidates = db.query(RefreshToken).filter(RefreshToken.revoked.is_(False)).all()
    for candidate in candidates:
        if verify_refresh_token(raw_refresh_token, candidate.token_hash):
            candidate.revoked = True
    db.commit()
