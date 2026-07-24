import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# --- Auth ---

class RegisterRequest(BaseModel):
    """Public self-registration -- always creates role='customer'. Agent
    and admin accounts only ever come from the seed script."""
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=1, max_length=255)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- User / profile ---

class ProfileUpdateRequest(BaseModel):
    """All fields optional so the customer can save the profile form
    section by section."""
    full_name: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    occupation: str | None = None
    income: float | None = None
    marital_status: str | None = None
    address: dict = Field(default_factory=dict)
    health_data: dict = Field(default_factory=dict)
    assets: dict = Field(default_factory=dict)
    lifestyle_data: dict = Field(default_factory=dict)


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    role: str
    is_active: bool
    full_name: str | None
    date_of_birth: date | None
    gender: str | None
    occupation: str | None
    income: float | None
    marital_status: str | None
    address: dict
    health_data: dict
    assets: dict
    lifestyle_data: dict
    risk_score: float | None
    coverage_score: float | None

    model_config = ConfigDict(from_attributes=True)


class DocumentOut(BaseModel):
    id: uuid.UUID
    doc_type: str
    file_path: str
    status: str
    ocr_result: dict
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationOut(BaseModel):
    id: uuid.UUID
    type: str
    content: str
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
