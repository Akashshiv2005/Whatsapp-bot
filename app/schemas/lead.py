from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class LeadBase(BaseModel):
    name: str
    phone_number: str
    email: Optional[str] = None
    service_id: Optional[int] = None
    business_type: Optional[str] = None
    requirement: Optional[str] = None
    budget: Optional[str] = None
    timeline: Optional[str] = None
    preferred_contact_time: Optional[str] = None
    estimated_amount: Optional[str] = None
    status: str = "NEW"
    source: str = "WHATSAPP_BOT"


class LeadCreate(LeadBase):
    user_id: Optional[int] = None
    conversation_id: Optional[int] = None


class LeadUpdate(BaseModel):
    name: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    business_type: Optional[str] = None
    requirement: Optional[str] = None
    budget: Optional[str] = None
    timeline: Optional[str] = None
    preferred_contact_time: Optional[str] = None
    estimated_amount: Optional[str] = None
    status: Optional[str] = None  # NEW, CONTACTED, QUALIFIED, IN_PROGRESS, CONVERTED, LOST, CLOSED


class LeadRead(LeadBase):
    id: int
    user_id: Optional[int] = None
    conversation_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
