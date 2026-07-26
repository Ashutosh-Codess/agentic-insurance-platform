import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.claim import Claim
from app.models.customer import Customer
from app.models.policy import Policy
from app.models.user import User
from app.schemas.claim import ClaimCreate, ClaimDecisionRequest, ClaimResponse
from app.services.cv_service import assess_damage
from app.services.ocr_service import check_document_quality
from app.services.agent_service import process_claim_with_agents

router = APIRouter()

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "data/raw/claim_documents")


def _claim_with_customer_name(claim: Claim, db: Session) -> dict:
    data = ClaimResponse.model_validate(claim).model_dump()
    customer = db.get(Customer, claim.customer_id)
    data["customer_name"] = customer.name if customer else None
    return data


def _append_history(claim: Claim, event: str):
    history = list(claim.processing_history or [])
    history.append({"event": event, "timestamp": datetime.now(timezone.utc).isoformat()})
    claim.processing_history = history


@router.post("/claims", response_model=ClaimResponse)
def submit_claim(payload: ClaimCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.user_id == current_user.id).first()
    if not customer:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Complete your customer profile first")

    policy = db.get(Policy, payload.policy_id)
    if not policy or policy.customer_id != customer.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found for this customer")

    claim = Claim(
        customer_id=customer.id,
        policy_id=policy.id,
        type=payload.type,
        incident_date=payload.incident_date,
        incident_description=payload.incident_description,
        claimed_amount=payload.claimed_amount,
        status="submitted",
    )
    _append_history(claim, "claim submitted")

    db.add(claim)
    db.commit()
    db.refresh(claim)
    return claim


@router.get("/claims/mine", response_model=list[ClaimResponse])
def list_my_claims(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.user_id == current_user.id).first()
    if not customer:
        return []
    return db.query(Claim).filter(Claim.customer_id == customer.id).order_by(Claim.submitted_at.desc()).all()


@router.get("/claims/{claim_id}", response_model=ClaimResponse)
def get_claim(claim_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    claim = db.get(Claim, claim_id)
    if not claim:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")

    if current_user.role == "customer":
        customer = db.query(Customer).filter(Customer.user_id == current_user.id).first()
        if not customer or claim.customer_id != customer.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your claim")

    return claim


@router.get("/claims")
def list_claims(status_filter: str | None = None, _: User = Depends(require_role("agent", "admin")), db: Session = Depends(get_db)):
    query = db.query(Claim)
    if status_filter:
        query = query.filter(Claim.status == status_filter)
    claims = query.order_by(Claim.submitted_at.desc()).all()
    return [_claim_with_customer_name(c, db) for c in claims]


@router.post("/claims/{claim_id}/decision", response_model=ClaimResponse)
def decide_claim(claim_id: uuid.UUID, payload: ClaimDecisionRequest, current_user: User = Depends(require_role("agent", "admin")), db: Session = Depends(get_db)):
    claim = db.get(Claim, claim_id)
    if not claim:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")

    if payload.decision not in ("approved", "rejected"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="decision must be 'approved' or 'rejected'")

    claim.status = payload.decision
    claim.approved_amount = payload.approved_amount
    claim.final_decision = payload.notes
    _append_history(claim, f"claim {payload.decision} by agent {current_user.id}")

    db.commit()
    db.refresh(claim)
    return claim


@router.post("/claims/{claim_id}/documents")
def upload_claim_document(
    claim_id: uuid.UUID,
    doc_type: str = Form(...),  # "photo" runs damage detection, anything else runs a quality check
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    claim = db.get(Claim, claim_id)
    if not claim:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")

    if current_user.role == "customer":
        customer = db.query(Customer).filter(Customer.user_id == current_user.id).first()
        if not customer or claim.customer_id != customer.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your claim")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(file.filename or "")[1]
    saved_path = os.path.join(UPLOAD_DIR, f"{claim_id}_{uuid.uuid4().hex}{ext}")
    with open(saved_path, "wb") as f:
        f.write(file.file.read())

    if doc_type == "photo" and claim.type == "motor":
        result = assess_damage(saved_path)
    else:
        result = check_document_quality(saved_path)

    _append_history(claim, f"document uploaded ({doc_type}): {result}")
    db.commit()

    return {"doc_type": doc_type, "file_path": saved_path, "result": result}


@router.post("/claims/{claim_id}/run-analysis")
def run_claim_analysis(
    claim_id: uuid.UUID,
    _: User = Depends(require_role("agent", "admin")),
    db: Session = Depends(get_db),
):
    """
    Runs the claim adjudication crew and fraud investigation crew against
    this claim (see app/services/agent_service.py), and flags whether it
    needs human review. This doesn't change claim.status or approve
    anything - it's a recommendation an agent reads before calling
    POST /claims/{claim_id}/decision themselves.
    """
    claim = db.get(Claim, claim_id)
    if not claim:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")

    claim_context = (
        f"Claim type: {claim.type}. Claimed amount: {claim.claimed_amount}. "
        f"Incident: {claim.incident_description or 'not provided'}. "
        f"Processing history: {claim.processing_history}"
    )

    analysis = process_claim_with_agents(
        claim_context=claim_context,
        claimed_amount=float(claim.claimed_amount),
        fraud_score=float(claim.fraud_score) if claim.fraud_score is not None else None,
    )

    _append_history(claim, "AI analysis run by agent")
    db.commit()

    return analysis
