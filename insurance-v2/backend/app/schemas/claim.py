import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ClaimSubmitRequest(BaseModel):
    policy_id: uuid.UUID
    claim_type: str
    claimed_amount: float
    description: str | None = None


class ClaimOut(BaseModel):
    id: uuid.UUID
    policy_id: uuid.UUID
    claim_type: str
    status: str
    claimed_amount: float
    description: str | None
    ai_analysis: dict
    final_action: str | None
    submitted_at: datetime
    resolved_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class ClaimDecisionRequest(BaseModel):
    final_action: str  # "approve" | "reject" | "escalate"


class CopilotQuestionRequest(BaseModel):
    question: str


class CopilotAnswerResponse(BaseModel):
    answer: str
    sources: list[str] = Field(default_factory=list)


class DashboardStatsOut(BaseModel):
    today_count: int
    pending_count: int
    high_risk_count: int
    recently_approved_count: int
    recently_rejected_count: int
    avg_processing_time_hours: float | None
