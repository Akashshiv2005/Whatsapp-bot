from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, verify_admin_key
from app.models import Service, MenuOption
from app.schemas.service import ServiceCreate, ServiceRead, ServiceUpdate

router = APIRouter(prefix="/services", tags=["Services Management"])


@router.get("", response_model=List[ServiceRead])
async def list_services(
    category: Optional[str] = Query(None, description="Filter by service category"),
    active: Optional[bool] = Query(None, description="Filter by active status"),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_admin_key),
):
    query = select(Service).options(selectinload(Service.menu_options))
    if category:
        query = query.where(Service.category == category)
    if active is not None:
        query = query.where(Service.active == active)
    query = query.order_by(Service.sort_order, Service.id)

    res = await db.execute(query)
    return res.scalars().all()


@router.get("/{service_id}", response_model=ServiceRead)
async def get_service(
    service_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_admin_key),
):
    res = await db.execute(
        select(Service).where(Service.id == service_id).options(selectinload(Service.menu_options))
    )
    service = res.scalar_one_or_none()
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    return service


@router.post("", response_model=ServiceRead, status_code=status.HTTP_201_CREATED)
async def create_service(
    data: ServiceCreate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_admin_key),
):
    res = await db.execute(select(Service).where(Service.slug == data.slug))
    if res.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Service slug already exists")

    service = Service(**data.model_dump())
    db.add(service)
    await db.commit()
    
    # Reload with menu_options
    res = await db.execute(
        select(Service).where(Service.id == service.id).options(selectinload(Service.menu_options))
    )
    return res.scalar_one()


@router.put("/{service_id}", response_model=ServiceRead)
async def update_service(
    service_id: int,
    data: ServiceUpdate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_admin_key),
):
    res = await db.execute(select(Service).where(Service.id == service_id))
    service = res.scalar_one_or_none()
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")

    update_dict = data.model_dump(exclude_unset=True)
    for key, val in update_dict.items():
        setattr(service, key, val)

    await db.commit()
    
    # Reload with menu_options
    res = await db.execute(
        select(Service).where(Service.id == service.id).options(selectinload(Service.menu_options))
    )
    return res.scalar_one()


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_service(
    service_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_admin_key),
):
    res = await db.execute(select(Service).where(Service.id == service_id))
    service = res.scalar_one_or_none()
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")

    await db.delete(service)
    await db.commit()
