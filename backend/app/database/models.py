"""
Database Models for TaxIA

Pydantic models for database entities.
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field


def generate_uuid() -> str:
    """Generate a new UUID string."""
    return str(uuid.uuid4())


class UserBase(BaseModel):
    """Base user model"""

    email: EmailStr
    name: str | None = None


class UserCreate(UserBase):
    """User creation model"""

    password: str = Field(..., min_length=8)


class User(UserBase):
    """User model with all fields"""

    id: str = Field(default_factory=generate_uuid)
    is_active: bool = True
    is_admin: bool = False
    is_owner: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class UserInDB(User):
    """User model as stored in database"""

    password_hash: str


class Session(BaseModel):
    """Session model for refresh tokens"""

    id: str = Field(default_factory=generate_uuid)
    user_id: str
    refresh_token_hash: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class ConversationBase(BaseModel):
    """Base conversation model"""

    title: str | None = None


class ConversationCreate(ConversationBase):
    """Conversation creation model"""

    pass


class Conversation(ConversationBase):
    """Conversation model with all fields"""

    id: str = Field(default_factory=generate_uuid)
    user_id: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class MessageBase(BaseModel):
    """Base message model"""

    role: str  # "user", "assistant", "system"
    content: str


class MessageCreate(MessageBase):
    """Message creation model"""

    conversation_id: str
    metadata: dict[str, Any] | None = None


class Message(MessageBase):
    """Message model with all fields"""

    id: str = Field(default_factory=generate_uuid)
    conversation_id: str
    metadata: dict[str, Any] | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class UsageMetric(BaseModel):
    """Usage metrics model"""

    id: str = Field(default_factory=generate_uuid)
    user_id: str | None = None
    endpoint: str
    tokens_used: int = 0
    processing_time: float | None = None
    cached: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class PayslipBase(BaseModel):
    """Base payslip model"""

    filename: str
    file_path: str
    file_size: int
    period_month: int | None = None
    period_year: int | None = None
    company_name: str | None = None
    company_cif: str | None = None
    employee_name: str | None = None
    employee_nif: str | None = None
    employee_ss: str | None = None
    gross_salary: float | None = None
    net_salary: float | None = None
    base_salary: float | None = None
    irpf_withholding: float | None = None
    irpf_percentage: float | None = None
    ss_contribution: float | None = None
    unemployment_contribution: float | None = None
    extra_payments: float | None = None
    overtime_pay: float | None = None


class PayslipCreate(PayslipBase):
    """Payslip creation model"""

    user_id: str
    extraction_status: str = "pending"
    extracted_data: str | None = None  # JSON string
    analysis_summary: str | None = None
    error_message: str | None = None


class Payslip(PayslipBase):
    """Payslip model with all fields"""

    id: str = Field(default_factory=generate_uuid)
    user_id: str
    upload_date: datetime = Field(default_factory=datetime.utcnow)
    extraction_status: str = "pending"
    extracted_data: str | None = None
    analysis_summary: str | None = None
    error_message: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class PayslipInDB(Payslip):
    """Payslip model as stored in database"""

    pass


# =============================================
# SUBSCRIPTION & PAYMENT MODELS
# =============================================


class Subscription(BaseModel):
    """Subscription model for Stripe integration"""

    id: str = Field(default_factory=generate_uuid)
    user_id: str
    stripe_customer_id: str
    stripe_subscription_id: str | None = None
    plan_type: str = "particular"
    status: str = "inactive"  # active, inactive, past_due, canceled, grace_period
    current_period_start: str | None = None
    current_period_end: str | None = None
    cancel_at_period_end: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class ContactRequest(BaseModel):
    """Contact form submission model"""

    id: str = Field(default_factory=generate_uuid)
    user_id: str | None = None
    email: str
    name: str | None = None
    message: str | None = None
    request_type: str = "autonomo_interest"
    status: str = "pending"
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True
