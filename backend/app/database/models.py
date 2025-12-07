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
