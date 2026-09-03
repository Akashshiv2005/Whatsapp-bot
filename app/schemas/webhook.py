from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class Profile(BaseModel):
    name: Optional[str] = None


class Contact(BaseModel):
    profile: Optional[Profile] = None
    wa_id: str


class TextMessage(BaseModel):
    body: str


class ButtonReply(BaseModel):
    id: str
    title: str


class ListReply(BaseModel):
    id: str
    title: str
    description: Optional[str] = None


class InteractiveMessage(BaseModel):
    type: str  # button_reply, list_reply
    button_reply: Optional[ButtonReply] = None
    list_reply: Optional[ListReply] = None


class LocationMessage(BaseModel):
    latitude: float
    longitude: float
    name: Optional[str] = None
    address: Optional[str] = None


class IncomingMessage(BaseModel):
    from_: str = Field(alias="from")
    id: str
    timestamp: str
    type: str  # text, interactive, location, image, document, etc.
    text: Optional[TextMessage] = None
    interactive: Optional[InteractiveMessage] = None
    location: Optional[LocationMessage] = None

    model_config = ConfigDict(populate_by_name=True)


class Metadata(BaseModel):
    display_phone_number: Optional[str] = None
    phone_number_id: Optional[str] = None


class ChangeValue(BaseModel):
    messaging_product: str
    metadata: Metadata
    contacts: Optional[List[Contact]] = None
    messages: Optional[List[IncomingMessage]] = None
    statuses: Optional[List[Dict[str, Any]]] = None


class Change(BaseModel):
    value: ChangeValue
    field: str


class Entry(BaseModel):
    id: str
    changes: List[Change]


class WebhookPayload(BaseModel):
    object: str
    entry: List[Entry]
