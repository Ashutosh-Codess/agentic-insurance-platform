"""
Claim model.

Simplification vs. a "real" system: there is no separate AgentRun /
FraudFlag / Decision table set. Every AI module's output (OCR, damage
detection, fraud score, classification, the resulting recommendation) is
written into ONE jsonb column, `ai_analysis`, on the claim itself. That is
enough to show your work and to explain a decision to an agent, without
five extra tables and joins for a project at this scope. See
services/claim_service.py for the exact shape written into this column.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base

CLAIM_STATUSES = (
    "submitted",
    "under_review",
    "missing_documents",
    "decision_ready",
    "approved",
    "rejected",
    "escalated",
)


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    policy_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("policies.id"), nullable=False)
    claim_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="submitted")
    claimed_amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Everything the AI pipeline produced for this claim -- OCR results,
    # damage detection score, fraud score + signals, classification,
    # recommended action + reasoning. See claim_service.run_ai_pipeline().
    ai_analysis: Mapped[dict] = mapped_column(JSONB, default=dict)

    final_action: Mapped[str | None] = mapped_column(String(20), nullable=True)  # approve/reject/escalate
    decided_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
