from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, verify_admin_key
from app.models import Lead
from app.schemas.lead import LeadCreate, LeadRead, LeadUpdate

router = APIRouter(prefix="/leads", tags=["Leads Management"])


@router.get("", response_model=List[LeadRead])
async def list_leads(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by lead status (NEW, CONTACTED, QUALIFIED, IN_PROGRESS, CONVERTED, LOST, CLOSED)"),
    service_id: Optional[int] = Query(None, description="Filter by service ID"),
    search: Optional[str] = Query(None, description="Search by name, phone, or email"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_admin_key),
):
    query = select(Lead)
    if status_filter:
        query = query.where(Lead.status == status_filter.upper())
    if service_id:
        query = query.where(Lead.service_id == service_id)
    if search:
        search_fmt = f"%{search}%"
        query = query.where(
            (Lead.name.ilike(search_fmt)) |
            (Lead.phone_number.ilike(search_fmt)) |
            (Lead.email.ilike(search_fmt))
        )
    query = query.order_by(Lead.id.desc()).limit(limit).offset(offset)

    res = await db.execute(query)
    return res.scalars().all()


@router.get("/{lead_id}", response_model=LeadRead)
async def get_lead(
    lead_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_admin_key),
):
    res = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = res.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    return lead


@router.post("", response_model=LeadRead, status_code=status.HTTP_201_CREATED)
async def create_lead(
    data: LeadCreate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_admin_key),
):
    lead = Lead(**data.model_dump())
    db.add(lead)
    await db.commit()
    await db.refresh(lead)
    return lead


@router.patch("/{lead_id}", response_model=LeadRead)
async def update_lead(
    lead_id: int,
    data: LeadUpdate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_admin_key),
):
    res = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = res.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

    update_dict = data.model_dump(exclude_unset=True)
    if "status" in update_dict and update_dict["status"]:
        update_dict["status"] = update_dict["status"].upper()

    for key, val in update_dict.items():
        setattr(lead, key, val)

    await db.commit()
    await db.refresh(lead)
    return lead


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lead(
    lead_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_admin_key),
):
    res = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = res.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

    await db.delete(lead)
    await db.commit()


from pydantic import BaseModel

class ForwardLeadEmailRequest(BaseModel):
    target_email: Optional[str] = None

@router.post("/{lead_id}/forward-email", summary="Forward Completed Lead Form to Any Email")
async def forward_lead_email(
    lead_id: int,
    req: ForwardLeadEmailRequest,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_admin_key),
):
    """Forward a completed lead form summary to any target email address."""
    from app.services.email_service import email_service
    res = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = res.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

    result = await email_service.send_lead_notification(lead, target_email=req.target_email)
    return result
