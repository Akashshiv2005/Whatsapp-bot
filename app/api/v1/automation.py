from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, verify_admin_key
from app.models import AutomationRule
from app.schemas.automation import AutomationRuleCreate, AutomationRuleRead, AutomationRuleUpdate

router = APIRouter(prefix="/automation-rules", tags=["Automation Rules"])


@router.get("", response_model=List[AutomationRuleRead])
async def list_automation_rules(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_admin_key),
):
    res = await db.execute(select(AutomationRule).order_by(AutomationRule.id.asc()))
    return res.scalars().all()


@router.post("", response_model=AutomationRuleRead, status_code=status.HTTP_201_CREATED)
async def create_automation_rule(
    data: AutomationRuleCreate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_admin_key),
):
    rule = AutomationRule(**data.model_dump())
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.patch("/{rule_id}", response_model=AutomationRuleRead)
async def update_automation_rule(
    rule_id: int,
    data: AutomationRuleUpdate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_admin_key),
):
    res = await db.execute(select(AutomationRule).where(AutomationRule.id == rule_id))
    rule = res.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")

    update_dict = data.model_dump(exclude_unset=True)
    for key, val in update_dict.items():
        setattr(rule, key, val)

    await db.commit()
    await db.refresh(rule)
    return rule


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_automation_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_admin_key),
):
    res = await db.execute(select(AutomationRule).where(AutomationRule.id == rule_id))
    rule = res.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")

    await db.delete(rule)
    await db.commit()
