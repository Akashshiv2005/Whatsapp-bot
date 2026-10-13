"""State Machine Router and Dispatcher for WhatsApp Bot."""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, Conversation
from app.services.message_parser import ParsedMessage
from app.core.logging import logger

from app.services.handlers.base_handler import BaseHandler
from app.services.handlers.main_menu_handler import MainMenuHandler
from app.services.handlers.submenu_handler import SubmenuHandler
from app.services.handlers.contact_support_handler import ContactSupportHandler
from app.services.handlers.product_info_handler import ProductInfoHandler
from app.services.handlers.lead_collection_handler import LeadCollectionHandler


class MessageHandler(
    BaseHandler,
    MainMenuHandler,
    SubmenuHandler,
    ContactSupportHandler,
    ProductInfoHandler,
    LeadCollectionHandler
):
    """Unified WhatsApp Bot MessageHandler coordinating modular domain handlers."""

    @staticmethod
    async def process_incoming_message(
        db: AsyncSession,
        parsed_msg: ParsedMessage
    ) -> None:
        """Core state machine message processing pipeline."""
        phone = parsed_msg.sender_phone
        user, conv = await BaseHandler.get_or_create_user_and_conv(
            db, phone, parsed_msg.sender_name
        )

        # 1. Log inbound message
        await BaseHandler.log_message(
            db=db,
            conversation_id=conv.id,
            direction="INBOUND",
            message_type=parsed_msg.message_type,
            text=parsed_msg.raw_text or parsed_msg.text_content,
            whatsapp_message_id=parsed_msg.message_id,
            raw_payload=parsed_msg.raw_payload,
            status="RECEIVED"
        )

        raw_input = (parsed_msg.raw_text or parsed_msg.text_content or "").strip()
        selection_id = parsed_msg.selection_id
        input_lower = raw_input.lower()

        logger.info(
            f"Processing message from {phone} | Current State: {conv.state} | "
            f"Input: '{raw_input}' | Selection ID: '{selection_id}'"
        )

        # 2. Universal Navigation & Main Menu Commands
        # Matches: "menu", "main menu", "hi", "hello", "0", "start", "home", "main menu 🏠", "🏠 main menu", or selection ID 'nav_main_menu'
        is_menu_command = (
            input_lower in [
                "0", "menu", "/start", "start", "hi", "hello", "hey",
                "main menu", "home", "main menu 🏠", "🏠 main menu", "return to main menu"
            ]
            or selection_id in ["nav_main_menu", "menu", "main_menu"]
            or input_lower == "nav_main_menu"
        )

        if is_menu_command:
            await BaseHandler.transition_to_main_menu(db, user, conv)
            return

        if input_lower == "cancel":
            conv.session_data = {}
            conv.state = "MAIN_MENU"
            await db.commit()
            await BaseHandler.send_and_log_text(
                db=db, conv=conv, to=phone,
                text="❌ Action cancelled. Returning to the main menu."
            )
            await BaseHandler.send_and_log_main_menu(db=db, conv=conv, to=phone, user_name=user.name)
            return

        if selection_id == "menu_support" or input_lower in ["talk to support", "talk support", "request callback", "callback"]:
            await ContactSupportHandler.start_support_workflow(db, user, conv)
            return

        if input_lower in ["support", "agent", "human", "help"]:
            await BaseHandler.transition_to_support(db, user, conv)
            return

        # 3. Handle Special Human Handoff State
        if conv.status == "HUMAN_HANDOFF" or conv.state == "HUMAN_HANDOFF":
            is_menu_choice = bool(selection_id) or any(
                input_lower == k or input_lower.startswith(f"{k}.") or input_lower.startswith(f"{k} ")
                for k in [
                    "1", "2", "3", "4", "5", "6", "7", "8",
                    "website", "software", "mobile", "marketing", "seo",
                    "communication", "whatsapp", "contact", "location", "address",
                    "menu_website", "menu_software", "menu_mobile", "menu_marketing",
                    "menu_communication", "menu_contact", "nav_main_menu"
                ]
            )
            if is_menu_choice:
                conv.status = "ACTIVE"
                conv.state = "MAIN_MENU"
                await db.commit()
            else:
                await BaseHandler.send_and_log_text(
                    db=db, conv=conv, to=phone,
                    text=(
                        "👤 You are currently connected to human support.\n"
                        "Our team has received your message and will respond shortly.\n\n"
                        "💡 Type *menu* at any time to return to automated options."
                    )
                )
                return

        # 4. State Dispatcher
        state = conv.state

        if state == "MAIN_MENU":
            await MainMenuHandler.handle_main_menu_input(db, user, conv, raw_input, selection_id)
        elif state == "PRODUCT_INFO":
            await ProductInfoHandler.handle_product_info_input(db, user, conv, raw_input, selection_id)
        elif state == "CONTACT_MENU":
            await ContactSupportHandler.handle_contact_menu_input(db, user, conv, raw_input, selection_id)
        elif state.endswith("_MENU") or state.startswith("ERP_MENU"):
            await SubmenuHandler.handle_submenu_input(db, user, conv, raw_input, selection_id)
        elif state.startswith("COLLECT_") or state == "LEAD_CONFIRMATION":
            await LeadCollectionHandler.handle_lead_collection_input(db, user, conv, raw_input, selection_id)
        elif state.startswith("SUPPORT_"):
            await ContactSupportHandler.handle_support_workflow_input(db, user, conv, raw_input, selection_id)
        else:
            await SubmenuHandler.handle_direct_service_state(db, user, conv, raw_input, selection_id)


message_handler = MessageHandler()
