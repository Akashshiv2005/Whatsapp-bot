from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, verify_admin_key
from app.models import FAQ
from app.schemas.faq import FAQCreate, FAQRead, FAQUpdate

router = APIRouter(prefix="/faqs", tags=["FAQ Management"])


@router.get("", response_model=List[FAQRead])
async def list_faqs(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_admin_key),
):
    res = await db.execute(select(FAQ).order_by(FAQ.id.asc()))
    return res.scalars().all()


@router.get("/{faq_id}", response_model=FAQRead)
async def get_faq(
    faq_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_admin_key),
):
    res = await db.execute(select(FAQ).where(FAQ.id == faq_id))
    faq = res.scalar_one_or_none()
    if not faq:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="FAQ not found")
    return faq


@router.post("", response_model=FAQRead, status_code=status.HTTP_201_CREATED)
async def create_faq(
    data: FAQCreate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_admin_key),
):
    faq = FAQ(**data.model_dump())
    db.add(faq)
    await db.commit()
    await db.refresh(faq)
    return faq


@router.put("/{faq_id}", response_model=FAQRead)
async def update_faq(
    faq_id: int,
    data: FAQUpdate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_admin_key),
):
    res = await db.execute(select(FAQ).where(FAQ.id == faq_id))
    faq = res.scalar_one_or_none()
    if not faq:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="FAQ not found")

    update_dict = data.model_dump(exclude_unset=True)
    for key, val in update_dict.items():
        setattr(faq, key, val)

    await db.commit()
    await db.refresh(faq)
    return faq


@router.delete("/{faq_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_faq(
    faq_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_admin_key),
):
    res = await db.execute(select(FAQ).where(FAQ.id == faq_id))
    faq = res.scalar_one_or_none()
    if not faq:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="FAQ not found")

    await db.delete(faq)
    await db.commit()
