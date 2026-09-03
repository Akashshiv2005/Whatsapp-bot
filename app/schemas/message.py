from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict


class MessageBase(BaseModel):
    conversation_id: int
    whatsapp_message_id: Optional[str] = None
    direction: str  # INBOUND, OUTBOUND
    message_type: str = "text"
    message_text: Optional[str] = None
    media_url: Optional[str] = None
    status: str = "SENT"
    raw_payload: Optional[Dict[str, Any]] = None


class MessageCreate(MessageBase):
    pass


class MessageRead(MessageBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
