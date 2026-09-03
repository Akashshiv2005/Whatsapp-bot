import asyncio
from typing import Any, Dict, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Lead, Service, User, Conversation
from app.services.workflow_engine import calculate_dummy_estimate
from app.core.logging import logger


class LeadService:
    @staticmethod
    async def create_lead_from_session(
        db: AsyncSession,
        user: User,
        conversation: Conversation,
        session_data: Dict[str, Any]
    ) -> Lead:
        """Create a new lead from completed session data with timeline, preferred time, and dummy estimate."""
        service_id = session_data.get("service_id")
        service_name = session_data.get("service_name")

        if not service_id and service_name:
            res = await db.execute(select(Service).where(Service.name == service_name))
            srv = res.scalar_one_or_none()
            if srv:
                service_id = srv.id

        est_amount = session_data.get("estimated_amount")
        if not est_amount:
            est_info = calculate_dummy_estimate(
                service_name=service_name or "General Solution",
                budget=session_data.get("budget"),
                timeline=session_data.get("timeline")
            )
            est_amount = est_info["estimated_range"]

        lead = Lead(
            user_id=user.id,
            service_id=service_id,
            conversation_id=conversation.id,
            name=session_data.get("name", user.name or "WhatsApp User"),
            email=session_data.get("email", user.email),
            phone_number=session_data.get("phone", user.phone_number),
            business_type=session_data.get("business_type"),
            requirement=session_data.get("requirement"),
            budget=session_data.get("budget"),
            timeline=session_data.get("timeline"),
            preferred_contact_time=session_data.get("preferred_contact_time"),
            estimated_amount=est_amount,
            status="NEW",
            source="WHATSAPP_BOT"
        )
        db.add(lead)
        await db.commit()
        await db.refresh(lead)

        if session_data.get("name") and not user.name:
            user.name = session_data.get("name")
        if session_data.get("email") and not user.email:
            user.email = session_data.get("email")
        await db.commit()

        logger.info(f"Created new Lead ID={lead.id} for {lead.name} ({lead.phone_number}) - Service ID={service_id} - Est: {est_amount}")

        # Trigger email notification safely with primitive parameters
        try:
            from app.services.email_service import email_service
            asyncio.create_task(
                email_service.send_lead_notification(
                    lead_id=lead.id,
                    name=lead.name,
                    phone_number=lead.phone_number,
                    email=lead.email,
                    business_type=lead.business_type,
                    service_name=service_name,
                    requirement=lead.requirement,
                    timeline=lead.timeline,
                    budget=lead.budget,
                    estimated_amount=lead.estimated_amount,
                    preferred_contact_time=lead.preferred_contact_time,
                    status=lead.status,
                    source=lead.source
                )
            )
        except Exception as err:
            logger.error(f"Failed to schedule email notification for lead {lead.id}: {err}")

        return lead

    @staticmethod
    async def update_lead_status(
        db: AsyncSession,
        lead_id: int,
        new_status: str
    ) -> Optional[Lead]:
        """Update lead status (NEW, CONTACTED, QUALIFIED, IN_PROGRESS, CONVERTED, LOST, CLOSED)."""
        res = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = res.scalar_one_or_none()
        if not lead:
            return None

        lead.status = new_status.upper()
        await db.commit()
        await db.refresh(lead)
        logger.info(f"Updated Lead ID={lead.id} status to {lead.status}")
        return lead


lead_service = LeadService()
