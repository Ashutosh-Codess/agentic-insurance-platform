"""
Product (catalog), Policy (a purchased product), and Recommendation.

Simplification vs. a "real" system: no separate premium-schedule table --
a policy just carries its own `premium_amount` and `next_due_date`. If you
later need a full payment history, that's a natural place to add a table,
but a single-family "final year project" scope doesn't need it yet.
"""
import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

PRODUCT_CATEGORIES = ("health", "life", "motor", "travel", "home", "business")


class Product(Base):
    """
    Config-driven catalog entry. `eligibility_rules` and `coverage_rules`
    are small JSON blobs (not a formula engine) -- documented shape:

        eligibility_rules: {"min_age": 18, "max_age": 65, "excluded_occupations": [...]}
        coverage_rules:    {"covered_claim_types": [...], "coverage_percentage": 80, "deductible": 5000}
    """
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_premium: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    waiting_period_days: Mapped[int] = mapped_column(Integer, default=0)
    eligibility_rules: Mapped[dict] = mapped_column(JSONB, default=dict)
    coverage_rules: Mapped[dict] = mapped_column(JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Policy(Base):
    __tablename__ = "policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active")
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    sum_insured: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    premium_amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    next_due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Recommendation(Base):
    """One row per (customer, recommended product) per run of the
    recommendation engine. Never overwritten -- old recommendations are
    just history."""
    __tablename__ = "recommendations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    estimated_premium: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
