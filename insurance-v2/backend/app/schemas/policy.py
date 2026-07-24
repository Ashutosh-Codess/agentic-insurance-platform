import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class ProductCreateRequest(BaseModel):
    name: str
    category: str
    description: str | None = None
    base_premium: float
    waiting_period_days: int = 0
    eligibility_rules: dict = Field(default_factory=dict)
    coverage_rules: dict = Field(default_factory=dict)
    is_active: bool = True


class ProductOut(BaseModel):
    id: uuid.UUID
    name: str
    category: str
    description: str | None
    base_premium: float
    waiting_period_days: int
    eligibility_rules: dict
    coverage_rules: dict
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class PolicyPurchaseRequest(BaseModel):
    sum_insured: float


class PolicyOut(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    status: str
    start_date: date
    end_date: date
    sum_insured: float
    premium_amount: float
    next_due_date: date | None

    model_config = ConfigDict(from_attributes=True)


class RecommendationOut(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    score: float
    reasoning: str
    estimated_premium: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
