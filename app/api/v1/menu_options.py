from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, verify_admin_key
from app.models import MenuOption
from app.schemas.service import MenuOptionCreate, MenuOptionRead, MenuOptionUpdate

router = APIRouter(prefix="/menu-options", tags=["Menu Options Management"])


@router.get("", response_model=List[MenuOptionRead])
async def list_menu_options(
    parent_state: Optional[str] = Query(None, description="Filter by parent state"),
    active: Optional[bool] = Query(None, description="Filter by active status"),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_admin_key),
):
    query = select(MenuOption)
    if parent_state:
        query = query.where(MenuOption.parent_state == parent_state)
    if active is not None:
        query = query.where(MenuOption.active == active)
    query = query.order_by(MenuOption.parent_state, MenuOption.sort_order)

    res = await db.execute(query)
    return res.scalars().all()


@router.post("", response_model=MenuOptionRead, status_code=status.HTTP_201_CREATED)
async def create_menu_option(
    data: MenuOptionCreate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_admin_key),
):
    option = MenuOption(**data.model_dump())
    db.add(option)
    await db.commit()
    await db.refresh(option)
    return option


@router.put("/{option_id}", response_model=MenuOptionRead)
async def update_menu_option(
    option_id: int,
    data: MenuOptionUpdate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_admin_key),
):
    res = await db.execute(select(MenuOption).where(MenuOption.id == option_id))
    option = res.scalar_one_or_none()
    if not option:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu option not found")

    update_dict = data.model_dump(exclude_unset=True)
    for key, val in update_dict.items():
        setattr(option, key, val)

    await db.commit()
    await db.refresh(option)
    return option


@router.delete("/{option_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_menu_option(
    option_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_admin_key),
):
    res = await db.execute(select(MenuOption).where(MenuOption.id == option_id))
    option = res.scalar_one_or_none()
    if not option:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu option not found")

    await db.delete(option)
    await db.commit()
