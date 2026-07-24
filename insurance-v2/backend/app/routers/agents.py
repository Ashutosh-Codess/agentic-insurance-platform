import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import require_role
from app.db.database import get_db
from app.models.user import User
from app.schemas.claim import ClaimDecisionRequest, ClaimOut, DashboardStatsOut
from app.services import claim_service

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/dashboard", response_model=DashboardStatsOut)
def agent_dashboard(
    _agent: User = Depends(require_role("agent", "admin")),
    db: Session = Depends(get_db),
):
    return claim_service.dashboard_stats(db)


@router.get("/claims", response_model=list[ClaimOut])
def agent_claim_queue(
    high_risk_only: bool = Query(default=False),
    pending_only: bool = Query(default=False),
    _agent: User = Depends(require_role("agent", "admin")),
    db: Session = Depends(get_db),
):
    return claim_service.list_agent_queue(db, high_risk_only=high_risk_only, pending_only=pending_only)


@router.get("/claims/{claim_id}", response_model=ClaimOut)
def agent_claim_detail(
    claim_id: uuid.UUID,
    _agent: User = Depends(require_role("agent", "admin")),
    db: Session = Depends(get_db),
):
    return claim_service.get_claim(db, claim_id)


@router.post("/claims/{claim_id}/decision", response_model=ClaimOut)
def record_decision(
    claim_id: uuid.UUID,
    payload: ClaimDecisionRequest,
    current_user: User = Depends(require_role("agent", "admin")),
    db: Session = Depends(get_db),
):
    claim = claim_service.get_claim(db, claim_id)
    return claim_service.record_decision(db, claim, payload.final_action, current_user.id)
