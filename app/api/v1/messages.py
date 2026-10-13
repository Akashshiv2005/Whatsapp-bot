from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, verify_admin_key
from app.models import Message
from app.schemas.message import MessageRead

router = APIRouter(prefix="/messages", tags=["Messages Query"])


@router.get("", response_model=List[MessageRead])
async def list_messages(
    direction: Optional[str] = Query(None, description="INBOUND or OUTBOUND"),
    search: Optional[str] = Query(None, description="Search message text"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_admin_key),
):
    query = select(Message)
    if direction:
        query = query.where(Message.direction == direction.upper())
    if search:
        query = query.where(Message.message_text.ilike(f"%{search}%"))
    query = query.order_by(Message.id.desc()).limit(limit).offset(offset)

    res = await db.execute(query)
    return res.scalars().all()
