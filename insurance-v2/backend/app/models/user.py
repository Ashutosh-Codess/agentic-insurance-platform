"""
User model.

Deliberate simplification vs. a "real" enterprise design: profile fields
(occupation, income, health/asset/lifestyle data, risk score) live directly
on User instead of a separate Customer/CustomerProfile table. For agent and
admin rows these columns just stay null/empty. This trades a small amount
of schema purity for a genuinely simpler codebase -- one model, one query,
no join required anywhere a customer's data is needed -- which is what
"keep the architecture simple" calls for here.
"""
import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

VALID_ROLES = ("customer", "agent", "admin")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        # Enforced at the DB level AND on the model itself (not just in a
        # migration file) so the constraint can never silently drift out
        # of sync with what the ORM thinks the schema looks like.
        CheckConstraint("role IN ('customer', 'agent', 'admin')", name="ck_users_role"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # --- profile fields (customer role only, in practice) ---
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)
    occupation: Mapped[str | None] = mapped_column(String(255), nullable=True)
    income: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    marital_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    address: Mapped[dict] = mapped_column(JSONB, default=dict)
    health_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    assets: Mapped[dict] = mapped_column(JSONB, default=dict)
    lifestyle_data: Mapped[dict] = mapped_column(JSONB, default=dict)

    # written by recommendation_service.py, never by the user directly
    risk_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    coverage_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)

    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def age(self) -> int | None:
        if not self.date_of_birth:
            return None
        today = date.today()
        dob = self.date_of_birth
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


class RefreshToken(Base):
    """
    Only the HASH of each issued refresh token is stored. Logout / token
    compromise response = flip `revoked`, never a raw-token comparison.
    """
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")
