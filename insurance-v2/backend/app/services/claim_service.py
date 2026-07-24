"""
Claim service -- this is where a claim's whole lifecycle lives:
submission, document upload, running the AI pipeline (OCR/quality check ->
damage detection for motor claims -> fraud detection -> classification ->
a rule-based decision recommendation), and recording the human agent's
final call.

No LangGraph, no agent framework, no message queue: `run_ai_pipeline` is
one plain Python function that calls the other modules in sequence and
writes the combined result into `claim.ai_analysis`. That is the entire
"orchestration layer" for this project, by design.
"""
from datetime import date, datetime, timezone

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.claim import Claim, Notification
from app.models.document import Document
from app.models.policy import Policy, Product
from app.models.user import User
from app.services import fraud_service
from app.utils import classification, ocr
from app.utils.damage_detection import assess_vehicle_damage
from app.utils.file_storage import save_upload
from app.utils.report_writer import write_claim_report

FRAUD_ESCALATION_THRESHOLD = 0.75


# ---------------------------------------------------------------------
# Submission and documents
# ---------------------------------------------------------------------

def submit_claim(db: Session, user: User, policy_id, claim_type: str, claimed_amount: float, description: str | None) -> Claim:
    policy = db.get(Policy, policy_id)
    if policy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    if policy.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This policy does not belong to you")
    if policy.status != "active":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Policy is not active")

    claim = Claim(
        user_id=user.id,
        policy_id=policy.id,
        claim_type=claim_type,
        claimed_amount=claimed_amount,
        description=description,
        status="submitted",
    )
    db.add(claim)
    db.commit()
    db.refresh(claim)
    return claim


def get_claim(db: Session, claim_id) -> Claim:
    claim = db.get(Claim, claim_id)
    if claim is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
    return claim


def upload_claim_document(db: Session, claim: Claim, doc_type: str, file: UploadFile) -> Document:
    file_path = save_upload(file, settings.UPLOAD_DIR, prefix=f"claim_{claim.id}")

    # Document quality check runs immediately on upload -- the customer
    # finds out right away if a photo is too blurry to use, rather than
    # waiting for the full pipeline run.
    quality = ocr.analyze_document(file_path)

    doc = Document(
        claim_id=claim.id,
        doc_type=doc_type,
        file_path=file_path,
        ocr_result=quality,
        status=quality["status"],
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


# ---------------------------------------------------------------------
# Policy eligibility + payable amount (inline, no separate agent files --
# this project intentionally keeps them as small functions here rather
# than their own service module)
# ---------------------------------------------------------------------

def _check_policy_eligibility(policy: Policy, product: Product, claim: Claim) -> dict:
    reasons = []
    eligible = True

    waiting_period = product.waiting_period_days or 0
    days_since_start = (claim.submitted_at.date() - policy.start_date).days
    if days_since_start < waiting_period:
        eligible = False
        reasons.append(f"Claim filed {days_since_start} days after policy start; waiting period is {waiting_period} days.")

    coverage_rules = product.coverage_rules or {}
    covered_types = coverage_rules.get("covered_claim_types")
    if covered_types and claim.claim_type not in covered_types:
        eligible = False
        reasons.append(f"Claim type '{claim.claim_type}' is not covered by this product.")

    if eligible:
        reasons.append("No waiting period or coverage issues found.")

    return {"eligible": eligible, "reasons": reasons}


def _compute_payable_amount(policy: Policy, product: Product, claim: Claim) -> dict:
    coverage_rules = product.coverage_rules or {}
    coverage_percentage = float(coverage_rules.get("coverage_percentage", 100))
    deductible = float(coverage_rules.get("deductible", 0))

    capped = min(float(claim.claimed_amount), float(policy.sum_insured))
    after_percentage = capped * (coverage_percentage / 100.0)
    payable = max(after_percentage - deductible, 0)

    return {
        "payable_amount": round(payable, 2),
        "coverage_percentage": coverage_percentage,
        "deductible": deductible,
        "breakdown": (
            f"Claimed {claim.claimed_amount}, capped at sum insured {policy.sum_insured}, "
            f"{coverage_percentage}% coverage applied, deductible {deductible} subtracted."
        ),
    }


# ---------------------------------------------------------------------
# AI pipeline
# ---------------------------------------------------------------------

def run_ai_pipeline(db: Session, claim: Claim) -> Claim:
    """Runs every AI module for this claim, in order, and writes the
    combined result into claim.ai_analysis. Called synchronously from the
    router (no task queue) -- simple, and fast enough at this project's
    scale."""
    policy = db.get(Policy, claim.policy_id)
    product = db.get(Product, policy.product_id)
    documents = db.query(Document).filter(Document.claim_id == claim.id).all()

    analysis: dict = {}

    # 1. Document quality (already computed per-document on upload; here
    #    we just summarize).
    analysis["document_quality"] = {
        "documents_checked": len(documents),
        "any_needs_review": any(d.status == "needs_manual_review" for d in documents),
    }
    if analysis["document_quality"]["any_needs_review"]:
        claim.status = "missing_documents"
        claim.ai_analysis = analysis
        db.commit()
        db.refresh(claim)
        return claim

    # 2. Damage detection (motor claims with a photo document only).
    if claim.claim_type == "motor":
        photo_docs = [d for d in documents if d.doc_type == "photo"]
        if photo_docs:
            analysis["damage_detection"] = assess_vehicle_damage(photo_docs[0].file_path)

    # 3. Policy eligibility.
    eligibility = _check_policy_eligibility(policy, product, claim)
    analysis["policy_eligibility"] = eligibility

    if not eligibility["eligible"]:
        claim.status = "pending_review"
        claim.final_action = None

        analysis["decision"] = {
            "recommended_action": "reject",
            "confidence": 0.95,
            "reasoning": " ".join(eligibility["reasons"]),
        }

        claim.ai_analysis = analysis
        db.commit()
        db.refresh(claim)
        return claim

    # 4. Coverage / payable amount.
    coverage = _compute_payable_amount(policy, product, claim)
    analysis["coverage"] = coverage

    # 5. Fraud detection.
    other_claims = (
        db.query(Claim)
        .filter(Claim.user_id == claim.user_id, Claim.id != claim.id)
        .all()
    )
    claim_history = [
        {"claimed_amount": float(c.claimed_amount), "submitted_at": c.submitted_at.isoformat()}
        for c in other_claims
    ]
    fraud = fraud_service.assess_fraud(
        {"claimed_amount": float(claim.claimed_amount), "submitted_at": claim.submitted_at.isoformat()},
        claim_history,
        policy.start_date,
    )
    analysis["fraud"] = fraud

    # 6. Classification (triage bucket).
    analysis["classification"] = classification.classify_claim(
        {"claimed_amount": float(claim.claimed_amount), "description": claim.description}, len(documents)
    )

    # 7. Decision recommendation -- rule-based, never auto-approves. A
    #    human agent always makes the actual call (see record_decision).
    if fraud["fraud_score"] >= FRAUD_ESCALATION_THRESHOLD:
        recommended_action = "escalate"
        confidence = 0.7
        reasoning = f"Fraud score {fraud['fraud_score']} exceeds the escalation threshold of {FRAUD_ESCALATION_THRESHOLD}."
    elif coverage["payable_amount"] <= 0:
        recommended_action = "reject"
        confidence = 0.85
        reasoning = "No payable amount after applying policy limits and deductions."
    else:
        recommended_action = "approve"
        confidence = round(max(0.6, 0.95 - fraud["fraud_score"]), 2)
        reasoning = (
            f"Claim is eligible, payable amount is {coverage['payable_amount']}, "
            f"fraud score ({fraud['fraud_score']}) is below the escalation threshold."
        )

    analysis["decision"] = {"recommended_action": recommended_action, "confidence": confidence, "reasoning": reasoning}

    claim.ai_analysis = analysis
    claim.status = "decision_ready"
    db.commit()

    write_claim_report(settings.REPORTS_DIR, str(claim.id), analysis)

    db.refresh(claim)
    return claim


# ---------------------------------------------------------------------
# Human decision
# ---------------------------------------------------------------------

def _notify(db: Session, user_id, notif_type: str, content: str) -> None:
    db.add(Notification(user_id=user_id, type=notif_type, content=content))
    db.commit()


def _rejection_message(claim: Claim, reasoning: str) -> str:
    return f"Your claim ({claim.id}) was not approved. Reason: {reasoning}"


def _approval_message(claim: Claim) -> str:
    payable = (claim.ai_analysis or {}).get("coverage", {}).get("payable_amount")
    return f"Your claim ({claim.id}) has been approved. Approved payout: {payable}."


def record_decision(db: Session, claim: Claim, final_action: str, decided_by_user_id) -> Claim:
    if not claim.ai_analysis or "decision" not in claim.ai_analysis:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Claim has no AI recommendation yet -- run the AI pipeline first",
        )

    claim.final_action = final_action
    claim.decided_by_user_id = decided_by_user_id
    claim.decided_at = datetime.now(timezone.utc)

    if final_action == "escalate":
        claim.status = "escalated"
    else:
        claim.status = "approved" if final_action == "approve" else "rejected"
        claim.resolved_at = datetime.now(timezone.utc)
        message = (
            _approval_message(claim)
            if final_action == "approve"
            else _rejection_message(claim, claim.ai_analysis["decision"]["reasoning"])
        )
        _notify(db, claim.user_id, "approval" if final_action == "approve" else "rejection", message)

    db.commit()
    db.refresh(claim)
    return claim


# ---------------------------------------------------------------------
# Queries used by routers
# ---------------------------------------------------------------------

def list_user_claims(db: Session, user: User) -> list[Claim]:
    return db.query(Claim).filter(Claim.user_id == user.id).all()


def list_agent_queue(db: Session, high_risk_only: bool = False, pending_only: bool = False) -> list[Claim]:
    query = db.query(Claim)
    if pending_only:
        query = query.filter(Claim.status.in_(["submitted", "under_review", "missing_documents", "decision_ready"]))
    claims = query.order_by(Claim.submitted_at.desc()).all()
    if high_risk_only:
        claims = [
            c for c in claims
            if (c.ai_analysis or {}).get("fraud", {}).get("fraud_score", 0) >= FRAUD_ESCALATION_THRESHOLD
        ]
    return claims


def dashboard_stats(db: Session) -> dict:
    today = date.today()
    all_claims = db.query(Claim).all()
    today_claims = [c for c in all_claims if c.submitted_at.date() == today]
    pending = [c for c in all_claims if c.status in ("submitted", "under_review", "missing_documents", "decision_ready")]
    high_risk = [
        c for c in all_claims
        if (c.ai_analysis or {}).get("fraud", {}).get("fraud_score", 0) >= FRAUD_ESCALATION_THRESHOLD
    ]
    approved = [c for c in all_claims if c.status == "approved"]
    rejected = [c for c in all_claims if c.status == "rejected"]

    resolved = [c for c in all_claims if c.resolved_at]
    if resolved:
        avg_seconds = sum((c.resolved_at - c.submitted_at).total_seconds() for c in resolved) / len(resolved)
        avg_hours = round(avg_seconds / 3600, 1)
    else:
        avg_hours = None

    return {
        "today_count": len(today_claims),
        "pending_count": len(pending),
        "high_risk_count": len(high_risk),
        "recently_approved_count": len(approved),
        "recently_rejected_count": len(rejected),
        "avg_processing_time_hours": avg_hours,
    }
