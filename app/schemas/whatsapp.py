from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ButtonReplyItem(BaseModel):
    id: str
    title: str


class InteractiveButton(BaseModel):
    type: str = "reply"
    reply: ButtonReplyItem


class ListRow(BaseModel):
    id: str
    title: str
    description: Optional[str] = None


class ListSection(BaseModel):
    title: str
    rows: List[ListRow]


class OutgoingInteractivePayload(BaseModel):
    type: str  # button, list
    header: Optional[Dict[str, Any]] = None
    body: Dict[str, str]
    footer: Optional[Dict[str, str]] = None
    action: Dict[str, Any]


class OutgoingLocationPayload(BaseModel):
    latitude: float
    longitude: float
    name: Optional[str] = None
    address: Optional[str] = None


class OutgoingTextPayload(BaseModel):
    preview_url: bool = False
    body: str


class OutgoingMessage(BaseModel):
    messaging_product: str = "whatsapp"
    recipient_type: str = "individual"
    to: str
    type: str  # text, interactive, location, template
    text: Optional[OutgoingTextPayload] = None
    interactive: Optional[OutgoingInteractivePayload] = None
    location: Optional[OutgoingLocationPayload] = None
    template: Optional[Dict[str, Any]] = None
