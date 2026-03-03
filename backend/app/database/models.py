"""
Database Models for TaxIA

Pydantic models for database entities.
"""
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field


def generate_uuid() -> str:
    """Generate a new UUID string."""
    return str(uuid.uuid4())


class UserBase(BaseModel):
    """Base user model"""
    email: EmailStr
    name: Optional[str] = None


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
    title: Optional[str] = None


class ConversationCreate(ConversationBase):
    """Conversation creation model"""
    pass


class Conversation(ConversationBase):
    """Conversation model with all fields"""
    id: str = Field(default_factory=generate_uuid)
    user_id: Optional[str] = None
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
    metadata: Optional[Dict[str, Any]] = None


class Message(MessageBase):
    """Message model with all fields"""
    id: str = Field(default_factory=generate_uuid)
    conversation_id: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        from_attributes = True


class UsageMetric(BaseModel):
    """Usage metrics model"""
    id: str = Field(default_factory=generate_uuid)
    user_id: Optional[str] = None
    endpoint: str
    tokens_used: int = 0
    processing_time: Optional[float] = None
    cached: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        from_attributes = True


class PayslipBase(BaseModel):
    """Base payslip model"""
    filename: str
    file_path: str
    file_size: int
    period_month: Optional[int] = None
    period_year: Optional[int] = None
    company_name: Optional[str] = None
    company_cif: Optional[str] = None
    employee_name: Optional[str] = None
    employee_nif: Optional[str] = None
    employee_ss: Optional[str] = None
    gross_salary: Optional[float] = None
    net_salary: Optional[float] = None
    base_salary: Optional[float] = None
    irpf_withholding: Optional[float] = None
    irpf_percentage: Optional[float] = None
    ss_contribution: Optional[float] = None
    unemployment_contribution: Optional[float] = None
    extra_payments: Optional[float] = None
    overtime_pay: Optional[float] = None


class PayslipCreate(PayslipBase):
    """Payslip creation model"""
    user_id: str
    extraction_status: str = "pending"
    extracted_data: Optional[str] = None  # JSON string
    analysis_summary: Optional[str] = None
    error_message: Optional[str] = None


class Payslip(PayslipBase):
    """Payslip model with all fields"""
    id: str = Field(default_factory=generate_uuid)
    user_id: str
    upload_date: datetime = Field(default_factory=datetime.utcnow)
    extraction_status: str = "pending"
    extracted_data: Optional[str] = None
    analysis_summary: Optional[str] = None
    error_message: Optional[str] = None
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
    stripe_subscription_id: Optional[str] = None
    plan_type: str = "particular"
    status: str = "inactive"  # active, inactive, past_due, canceled, grace_period
    current_period_start: Optional[str] = None
    current_period_end: Optional[str] = None
    cancel_at_period_end: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class ContactRequest(BaseModel):
    """Contact form submission model"""
    id: str = Field(default_factory=generate_uuid)
    user_id: Optional[str] = None
    email: str
    name: Optional[str] = None
    message: Optional[str] = None
    request_type: str = "autonomo_interest"
    status: str = "pending"
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True
