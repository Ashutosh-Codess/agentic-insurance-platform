import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user, require_role
from app.db.database import get_db
from app.models.user import User
from app.schemas.claim import (
    ClaimOut,
    ClaimSubmitRequest,
    CopilotAnswerResponse,
    CopilotQuestionRequest,
)
from app.services import claim_service
from app.utils.copilot import ask_copilot

router = APIRouter(tags=["claims"])


@router.post("/claims", response_model=ClaimOut, status_code=201)
def submit_claim(
    payload: ClaimSubmitRequest,
    current_user: User = Depends(require_role("customer")),
    db: Session = Depends(get_db),
):
    return claim_service.submit_claim(
        db, current_user, payload.policy_id, payload.claim_type, payload.claimed_amount, payload.description
    )


@router.post("/claims/{claim_id}/documents", status_code=201)
def upload_claim_document(
    claim_id: uuid.UUID,
    doc_type: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(require_role("customer")),
    db: Session = Depends(get_db),
):
    claim = claim_service.get_claim(db, claim_id)
    doc = claim_service.upload_claim_document(db, claim, doc_type, file)
    return {"id": doc.id, "doc_type": doc.doc_type, "status": doc.status, "ocr_result": doc.ocr_result}


@router.post("/claims/{claim_id}/process", response_model=ClaimOut)
def process_claim(
    claim_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Runs the AI pipeline (document quality -> damage detection ->
    eligibility -> coverage -> fraud -> classification -> decision) for
    this claim. Called synchronously -- no task queue in this project."""
    claim = claim_service.get_claim(db, claim_id)
    return claim_service.run_ai_pipeline(db, claim)


@router.get("/customers/me/claims", response_model=list[ClaimOut])
def list_my_claims(
    current_user: User = Depends(require_role("customer")),
    db: Session = Depends(get_db),
):
    return claim_service.list_user_claims(db, current_user)


@router.get("/claims/{claim_id}", response_model=ClaimOut)
def read_claim(
    claim_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    claim = claim_service.get_claim(db, claim_id)
    if current_user.role == "customer" and claim.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This claim does not belong to you")
    return claim


@router.post("/claims/{claim_id}/copilot", response_model=CopilotAnswerResponse)
def copilot_question(
    claim_id: uuid.UUID,
    payload: CopilotQuestionRequest,
    _agent: User = Depends(require_role("agent", "admin")),
    db: Session = Depends(get_db),
):
    claim = claim_service.get_claim(db, claim_id)
    result = ask_copilot(payload.question, claim.ai_analysis or {})
    return CopilotAnswerResponse(**result)
