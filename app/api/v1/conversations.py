from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, verify_admin_key
from app.models import Conversation, Message
from app.schemas.conversation import ConversationRead
from app.schemas.message import MessageRead

router = APIRouter(prefix="/conversations", tags=["Conversations Management"])


@router.get("", response_model=List[ConversationRead])
async def list_conversations(
    user_id: Optional[int] = Query(None),
    state: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_admin_key),
):
    query = select(Conversation)
    if user_id:
        query = query.where(Conversation.user_id == user_id)
    if state:
        query = query.where(Conversation.state == state)
    if status_filter:
        query = query.where(Conversation.status == status_filter.upper())
    query = query.order_by(Conversation.updated_at.desc()).limit(limit).offset(offset)

    res = await db.execute(query)
    return res.scalars().all()


@router.get("/{conversation_id}", response_model=ConversationRead)
async def get_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_admin_key),
):
    res = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conv = res.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return conv


@router.get("/{conversation_id}/messages", response_model=List[MessageRead])
async def get_conversation_messages(
    conversation_id: int,
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_admin_key),
):
    res = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .limit(limit)
    )
    return res.scalars().all()
