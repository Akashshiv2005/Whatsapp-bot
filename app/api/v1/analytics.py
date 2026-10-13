from typing import Any, Dict
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, verify_admin_key
from app.models import User, Conversation, Message, Lead, Service

router = APIRouter(prefix="/analytics", tags=["Analytics & KPIs"])


@router.get("/summary", summary="Bot Performance & Lead Metrics")
async def get_analytics_summary(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_admin_key),
) -> Dict[str, Any]:
    # 1. Total WhatsApp Users
    res_users = await db.execute(select(func.count(User.id)))
    total_users = res_users.scalar() or 0

    # 2. Total Conversations & Human Handoffs
    res_convs = await db.execute(select(func.count(Conversation.id)))
    total_convs = res_convs.scalar() or 0

    res_handoffs = await db.execute(
        select(func.count(Conversation.id)).where(Conversation.status == "HUMAN_HANDOFF")
    )
    total_handoffs = res_handoffs.scalar() or 0

    # 3. Total Messages (Inbound vs Outbound)
    res_msgs = await db.execute(select(func.count(Message.id)))
    total_msgs = res_msgs.scalar() or 0

    res_inbound = await db.execute(
        select(func.count(Message.id)).where(Message.direction == "INBOUND")
    )
    inbound_msgs = res_inbound.scalar() or 0

    res_outbound = await db.execute(
        select(func.count(Message.id)).where(Message.direction == "OUTBOUND")
    )
    outbound_msgs = res_outbound.scalar() or 0

    # 4. Total Leads & Breakdown by Status
    res_leads = await db.execute(select(func.count(Lead.id)))
    total_leads = res_leads.scalar() or 0

    res_lead_status = await db.execute(
        select(Lead.status, func.count(Lead.id)).group_by(Lead.status)
    )
    leads_by_status = {row[0]: row[1] for row in res_lead_status.all()}

    # 5. Leads by Service Category
    res_leads_by_service = await db.execute(
        select(Service.name, func.count(Lead.id))
        .join(Lead, Lead.service_id == Service.id)
        .group_by(Service.name)
    )
    leads_by_service = {row[0]: row[1] for row in res_leads_by_service.all()}

    return {
        "users": {
            "total_users": total_users,
        },
        "conversations": {
            "total_conversations": total_convs,
            "human_handoffs": total_handoffs,
        },
        "messages": {
            "total_messages": total_msgs,
            "inbound_messages": inbound_msgs,
            "outbound_messages": outbound_msgs,
        },
        "leads": {
            "total_leads": total_leads,
            "by_status": leads_by_status,
            "by_service": leads_by_service,
        }
    }
