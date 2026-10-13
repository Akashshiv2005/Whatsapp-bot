from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict


class AutomationRuleBase(BaseModel):
    name: str
    trigger_type: str  # KEYWORD, STATUS_CHANGE, TIME_INACTIVITY
    trigger_value: str
    action_type: str  # SEND_MESSAGE, NOTIFY_ADMIN, CHANGE_STATE
    action_config: Dict[str, Any] = {}
    active: bool = True


class AutomationRuleCreate(AutomationRuleBase):
    pass


class AutomationRuleUpdate(BaseModel):
    name: Optional[str] = None
    trigger_type: Optional[str] = None
    trigger_value: Optional[str] = None
    action_type: Optional[str] = None
    action_config: Optional[Dict[str, Any]] = None
    active: Optional[bool] = None


class AutomationRuleRead(AutomationRuleBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MessageTemplateBase(BaseModel):
    name: str
    template_key: str
    content: str
    meta_template_name: Optional[str] = None
    language: str = "en"
    active: bool = True


class MessageTemplateCreate(MessageTemplateBase):
    pass


class MessageTemplateUpdate(BaseModel):
    name: Optional[str] = None
    template_key: Optional[str] = None
    content: Optional[str] = None
    meta_template_name: Optional[str] = None
    language: Optional[str] = None
    active: Optional[bool] = None


class MessageTemplateRead(MessageTemplateBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
