import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import require_role
from app.db.database import get_db
from app.models.claim import Notification
from app.models.document import Document
from app.models.user import User
from app.schemas.policy import RecommendationOut
from app.schemas.user import DocumentOut, NotificationOut, ProfileUpdateRequest, UserOut
from app.services import recommendation_service
from app.utils import ocr
from app.utils.file_storage import save_upload

router = APIRouter(tags=["customers"])


@router.get("/customers/me", response_model=UserOut)
def read_my_profile(current_user: User = Depends(require_role("customer"))):
    return current_user


@router.put("/customers/me/profile", response_model=UserOut)
def update_my_profile(
    payload: ProfileUpdateRequest,
    current_user: User = Depends(require_role("customer")),
    db: Session = Depends(get_db),
):
    data = payload.model_dump(exclude_unset=True)
    for field in ("full_name", "date_of_birth", "gender", "occupation", "income", "marital_status"):
        if field in data and data[field] is not None:
            setattr(current_user, field, data[field])
    if data.get("address"):
        current_user.address = {**(current_user.address or {}), **data["address"]}
    if data.get("health_data"):
        current_user.health_data = {**(current_user.health_data or {}), **data["health_data"]}
    if data.get("assets"):
        current_user.assets = {**(current_user.assets or {}), **data["assets"]}
    if data.get("lifestyle_data"):
        current_user.lifestyle_data = {**(current_user.lifestyle_data or {}), **data["lifestyle_data"]}

    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/customers/me/documents", response_model=DocumentOut, status_code=201)
def upload_kyc_document(
    doc_type: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(require_role("customer")),
    db: Session = Depends(get_db),
):
    file_path = save_upload(file, settings.UPLOAD_DIR, prefix=f"kyc_{current_user.id}")
    quality = ocr.analyze_document(file_path)

    doc = Document(user_id=current_user.id, doc_type=doc_type, file_path=file_path, ocr_result=quality, status=quality["status"])
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@router.get("/customers/me/documents", response_model=list[DocumentOut])
def list_my_documents(
    current_user: User = Depends(require_role("customer")),
    db: Session = Depends(get_db),
):
    return db.query(Document).filter(Document.user_id == current_user.id).all()


@router.post("/customers/me/recommendations/refresh", response_model=list[RecommendationOut])
def refresh_recommendations(
    current_user: User = Depends(require_role("customer")),
    db: Session = Depends(get_db),
):
    return recommendation_service.refresh_recommendations(db, current_user)


@router.get("/customers/me/recommendations", response_model=list[RecommendationOut])
def get_recommendations(
    current_user: User = Depends(require_role("customer")),
    db: Session = Depends(get_db),
):
    return recommendation_service.get_latest_recommendations(db, current_user)


@router.get("/notifications", response_model=list[NotificationOut])
def list_notifications(
    unread_only: bool = Query(default=False),
    current_user: User = Depends(require_role("customer")),
    db: Session = Depends(get_db),
):
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    if unread_only:
        query = query.filter(Notification.is_read.is_(False))
    return query.order_by(Notification.created_at.desc()).all()


@router.post("/notifications/{notification_id}/read", response_model=NotificationOut)
def mark_notification_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(require_role("customer")),
    db: Session = Depends(get_db),
):
    notification = db.get(Notification, notification_id)
    if notification is None or notification.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return notification
