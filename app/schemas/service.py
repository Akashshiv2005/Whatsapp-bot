from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class MenuOptionBase(BaseModel):
    parent_state: str
    label: str
    value: str
    next_state: str
    service_id: Optional[int] = None
    sort_order: int = 0
    active: bool = True


class MenuOptionCreate(MenuOptionBase):
    pass


class MenuOptionUpdate(BaseModel):
    parent_state: Optional[str] = None
    label: Optional[str] = None
    value: Optional[str] = None
    next_state: Optional[str] = None
    service_id: Optional[int] = None
    sort_order: Optional[int] = None
    active: Optional[bool] = None


class MenuOptionRead(MenuOptionBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class ServiceBase(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    category: str
    active: bool = True
    sort_order: int = 0


class ServiceCreate(ServiceBase):
    pass


class ServiceUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    active: Optional[bool] = None
    sort_order: Optional[int] = None


class ServiceRead(ServiceBase):
    id: int
    created_at: datetime
    updated_at: datetime
    menu_options: List[MenuOptionRead] = []

    model_config = ConfigDict(from_attributes=True)
