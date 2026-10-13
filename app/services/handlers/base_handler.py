"""Base helpers for WhatsApp bot messaging and state logging."""
import re
from typing import Any, Dict, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, Conversation, Message, Service, MenuOption, Lead
from app.services.whatsapp import whatsapp_service
from app.services.workflow_engine import (
    workflow_engine,
    calculate_dummy_estimate,
    get_workflow_description,
    BUSINESS_TYPE_OPTIONS,
    TIMELINE_OPTIONS,
    BUDGET_OPTIONS,
    PREFERRED_TIME_OPTIONS,
    SUPPORT_SERVICE_OPTIONS,
)
from app.core.config import get_settings
from app.core.logging import logger

settings = get_settings()


class BaseHandler:
    @staticmethod
    async def get_or_create_user_and_conv(
        db: AsyncSession,
        phone_number: str,
        sender_name: Optional[str] = None
    ) -> Tuple[User, Conversation]:
        """Resolve or initialize User and active Conversation."""
        res_user = await db.execute(select(User).where(User.phone_number == phone_number))
        user = res_user.scalar_one_or_none()

        if not user:
            user = User(
                phone_number=phone_number,
                whatsapp_user_id=phone_number,
                name=sender_name,
                is_active=True
            )
            db.add(user)
            await db.flush()
            logger.info(f"Created new user for phone {phone_number} (ID={user.id})")
        elif sender_name and user.name != sender_name:
            user.name = sender_name
            await db.flush()

        res_conv = await db.execute(
            select(Conversation)
            .where(Conversation.user_id == user.id)
            .order_by(Conversation.id.desc())
        )
        conversation = res_conv.scalars().first()

        if not conversation:
            conversation = Conversation(
                user_id=user.id,
                state="MAIN_MENU",
                status="ACTIVE",
                session_data={}
            )
            db.add(conversation)
            await db.flush()
            logger.info(f"Created initial conversation for user ID={user.id} (ID={conversation.id})")

        return user, conversation

    @staticmethod
    async def log_message(
        db: AsyncSession,
        conversation_id: int,
        direction: str,
        message_type: str,
        text: Optional[str] = None,
        whatsapp_message_id: Optional[str] = None,
        raw_payload: Optional[Dict[str, Any]] = None,
        status: str = "DELIVERED"
    ) -> Message:
        """Persist message in messages table for auditing and UI trace."""
        msg = Message(
            conversation_id=conversation_id,
            direction=direction,
            message_type=message_type,
            message_text=text,
            whatsapp_message_id=whatsapp_message_id,
            raw_payload=raw_payload,
            status=status
        )
        db.add(msg)
        await db.commit()
        await db.refresh(msg)
        return msg

    @staticmethod
    async def send_and_log_text(
        db: AsyncSession,
        conv: Conversation,
        to: str,
        text: str
    ) -> Dict[str, Any]:
        """Helper to send plain text and record in DB."""
        res = await whatsapp_service.send_text(to=to, text=text)
        await BaseHandler.log_message(
            db=db,
            conversation_id=conv.id,
            direction="OUTBOUND",
            message_type="text",
            text=text,
            whatsapp_message_id=res.get("messages", [{}])[0].get("id") if res.get("messages") else None,
            raw_payload=res.get("payload") or res
        )
        return res

    @staticmethod
    async def send_and_log_main_menu(
        db: AsyncSession,
        conv: Conversation,
        to: str,
        user_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Helper to send main menu and record in DB."""
        res = await workflow_engine.send_main_menu(to=to, user_name=user_name)
        payload = res.get("payload") or {}
        body_text = payload.get("interactive", {}).get("body", {}).get("text", "Welcome to iZone Technologies! (Main Menu)")
        await BaseHandler.log_message(
            db=db,
            conversation_id=conv.id,
            direction="OUTBOUND",
            message_type="interactive_list",
            text=body_text,
            raw_payload=payload or res
        )
        return res

    @staticmethod
    async def send_and_log_submenu(
        db: AsyncSession,
        conv: Conversation,
        to: str,
        parent_state: str,
        title: str,
        description: str
    ) -> Dict[str, Any]:
        """Helper to send submenu and record in DB."""
        res = await workflow_engine.send_submenu(
            to=to, db=db, parent_state=parent_state,
            title=title, description=description
        )
        payload = res.get("payload") or {}
        body_text = payload.get("interactive", {}).get("body", {}).get("text", f"{title}: {description}")
        await BaseHandler.log_message(
            db=db,
            conversation_id=conv.id,
            direction="OUTBOUND",
            message_type="interactive_list",
            text=body_text,
            raw_payload=payload or res
        )
        return res

    @staticmethod
    async def send_and_log_business_type_selection(
        db: AsyncSession,
        conv: Conversation,
        to: str,
        user_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Helper to send interactive business type options and record in DB."""
        res = await workflow_engine.send_business_type_selection(to=to, user_name=user_name)
        payload = res.get("payload") or {}
        body_text = payload.get("interactive", {}).get("body", {}).get(
            "text", "Step 2 of 8: What type of business or organization is this for?"
        )
        await BaseHandler.log_message(
            db=db,
            conversation_id=conv.id,
            direction="OUTBOUND",
            message_type="interactive_list",
            text=body_text,
            raw_payload=payload or res
        )
        return res

    @staticmethod
    async def send_and_log_requirement_selection(
        db: AsyncSession,
        conv: Conversation,
        to: str,
        session_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Helper to send service-based requirement options and record in DB."""
        service_name = session_data.get("service_name")
        parent_menu = session_data.get("parent_menu")
        res = await workflow_engine.send_requirement_selection(
            to=to,
            service_name=service_name,
            parent_menu=parent_menu
        )
        payload = res.get("payload") or {}
        body_text = payload.get("interactive", {}).get("body", {}).get(
            "text", f"Step 3 of 8: Requirements for {service_name or 'Service'}"
        )
        await BaseHandler.log_message(
            db=db,
            conversation_id=conv.id,
            direction="OUTBOUND",
            message_type="interactive_list",
            text=body_text,
            raw_payload=payload or res
        )
        return res

    @staticmethod
    async def send_and_log_timeline(
        db: AsyncSession,
        conv: Conversation,
        to: str
    ) -> Dict[str, Any]:
        """Helper to send timeline options and record in DB."""
        res = await workflow_engine.send_timeline_selection(to=to)
        payload = res.get("payload") or {}
        body_text = payload.get("interactive", {}).get("body", {}).get("text", "Step 4 of 8: Choose your project timeline")
        await BaseHandler.log_message(
            db=db,
            conversation_id=conv.id,
            direction="OUTBOUND",
            message_type="interactive_list",
            text=body_text,
            raw_payload=payload or res
        )
        return res

    @staticmethod
    async def send_and_log_budget(
        db: AsyncSession,
        conv: Conversation,
        to: str
    ) -> Dict[str, Any]:
        """Helper to send budget options and record in DB."""
        res = await workflow_engine.send_budget_selection(to=to)
        payload = res.get("payload") or {}
        body_text = payload.get("interactive", {}).get("body", {}).get("text", "Step 5 of 8: Select your approximate budget")
        await BaseHandler.log_message(
            db=db,
            conversation_id=conv.id,
            direction="OUTBOUND",
            message_type="interactive_list",
            text=body_text,
            raw_payload=payload or res
        )
        return res

    @staticmethod
    async def send_and_log_preferred_time(
        db: AsyncSession,
        conv: Conversation,
        to: str
    ) -> Dict[str, Any]:
        """Helper to send preferred consultation time options and record in DB."""
        res = await workflow_engine.send_preferred_time_selection(to=to)
        payload = res.get("payload") or {}
        body_text = payload.get("interactive", {}).get("body", {}).get("text", "Step 7 of 8: Preferred discussion time")
        await BaseHandler.log_message(
            db=db,
            conversation_id=conv.id,
            direction="OUTBOUND",
            message_type="interactive_list",
            text=body_text,
            raw_payload=payload or res
        )
        return res

    @staticmethod
    async def send_and_log_confirmation_card(
        db: AsyncSession,
        conv: Conversation,
        to: str,
        session_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Helper to present interactive requirement review summary card before final submit."""
        res = await workflow_engine.send_lead_confirmation_card(to=to, session_data=session_data)
        payload = res.get("payload") or {}
        body_text = payload.get("interactive", {}).get("body", {}).get("text", "Requirement Summary Review")
        await BaseHandler.log_message(
            db=db,
            conversation_id=conv.id,
            direction="OUTBOUND",
            message_type="interactive_button",
            text=body_text,
            raw_payload=payload or res
        )
        return res

    @staticmethod
    async def transition_to_main_menu(db: AsyncSession, user: User, conv: Conversation) -> None:
        """Reset conversation session and show main menu."""
        conv.previous_state = conv.state
        conv.state = "MAIN_MENU"
        conv.status = "ACTIVE"
        conv.session_data = {}
        await db.commit()
        await BaseHandler.send_and_log_main_menu(db=db, conv=conv, to=user.phone_number, user_name=user.name)

    @staticmethod
    async def transition_to_support(db: AsyncSession, user: User, conv: Conversation) -> None:
        """Handoff user to human support team."""
        conv.previous_state = conv.state
        conv.state = "HUMAN_HANDOFF"
        conv.status = "HUMAN_HANDOFF"
        await db.commit()

        text = (
            "👤 *iZone Support Team Connected*\n\n"
            "A member of our support team will attend to you shortly during our business hours:\n"
            f"🕒 {settings.COMPANY_WORKING_HOURS}\n\n"
            f"📞 For urgent inquiries, call us at {settings.COMPANY_PHONE}.\n\n"
            "Type *menu* whenever you wish to return to the automated service menu."
        )
        await BaseHandler.send_and_log_text(db=db, conv=conv, to=user.phone_number, text=text)
