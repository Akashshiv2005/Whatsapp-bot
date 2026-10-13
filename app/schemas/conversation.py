from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict


class ConversationBase(BaseModel):
    user_id: int
    state: str = "MAIN_MENU"
    previous_state: Optional[str] = None
    status: str = "ACTIVE"
    session_data: Dict[str, Any] = {}


class ConversationCreate(ConversationBase):
    pass


class ConversationUpdate(BaseModel):
    state: Optional[str] = None
    previous_state: Optional[str] = None
    status: Optional[str] = None
    session_data: Optional[Dict[str, Any]] = None


class ConversationRead(ConversationBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
