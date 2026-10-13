from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, verify_admin_key
from app.models import MessageTemplate
from app.schemas.automation import MessageTemplateCreate, MessageTemplateRead, MessageTemplateUpdate

router = APIRouter(prefix="/templates", tags=["Message Templates"])


@router.get("", response_model=List[MessageTemplateRead])
async def list_templates(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_admin_key),
):
    res = await db.execute(select(MessageTemplate).order_by(MessageTemplate.id.asc()))
    return res.scalars().all()


@router.post("", response_model=MessageTemplateRead, status_code=status.HTTP_201_CREATED)
async def create_template(
    data: MessageTemplateCreate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_admin_key),
):
    res = await db.execute(select(MessageTemplate).where(MessageTemplate.template_key == data.template_key))
    if res.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Template key already exists")

    template = MessageTemplate(**data.model_dump())
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template


@router.put("/{template_id}", response_model=MessageTemplateRead)
async def update_template(
    template_id: int,
    data: MessageTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_admin_key),
):
    res = await db.execute(select(MessageTemplate).where(MessageTemplate.id == template_id))
    template = res.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    update_dict = data.model_dump(exclude_unset=True)
    for key, val in update_dict.items():
        setattr(template, key, val)

    await db.commit()
    await db.refresh(template)
    return template


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_admin_key),
):
    res = await db.execute(select(MessageTemplate).where(MessageTemplate.id == template_id))
    template = res.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    await db.delete(template)
    await db.commit()
