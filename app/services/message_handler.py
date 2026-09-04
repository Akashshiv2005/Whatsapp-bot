import re
from typing import Any, Dict, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import User, Conversation, Message, Service, MenuOption
from app.services.message_parser import ParsedMessage
from app.services.whatsapp import whatsapp_service
from app.services.workflow_engine import workflow_engine, calculate_dummy_estimate, get_workflow_description
from app.services.lead_service import lead_service
from app.services.faq_service import faq_service
from app.core.config import get_settings
from app.core.logging import logger

settings = get_settings()


class MessageHandler:
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
        status: str = "SENT"
    ) -> Message:
        """Persist inbound or outbound message record."""
        cleaned_payload = raw_payload
        if isinstance(raw_payload, dict) and "payload" in raw_payload and isinstance(raw_payload["payload"], dict):
            cleaned_payload = raw_payload["payload"]

        msg = Message(
            conversation_id=conversation_id,
            whatsapp_message_id=whatsapp_message_id,
            direction=direction,
            message_type=message_type,
            message_text=text,
            status=status,
            raw_payload=cleaned_payload
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
        """Helper to send text and record outbound message in DB."""
        res = await whatsapp_service.send_text(to=to, text=text)
        await MessageHandler.log_message(
            db=db,
            conversation_id=conv.id,
            direction="OUTBOUND",
            message_type="text",
            text=text,
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
        await MessageHandler.log_message(
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
        await MessageHandler.log_message(
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
        await MessageHandler.log_message(
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
        await MessageHandler.log_message(
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
        """Helper to send preferred time options and record in DB."""
        res = await workflow_engine.send_preferred_time_selection(to=to)
        payload = res.get("payload") or {}
        body_text = payload.get("interactive", {}).get("body", {}).get("text", "Step 7 of 8: Select best time to connect")
        await MessageHandler.log_message(
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
        """Helper to send lead confirmation card with dummy estimate and record in DB."""
        res = await workflow_engine.send_lead_confirmation_card(to=to, session_data=session_data)
        payload = res.get("payload") or {}
        body_text = payload.get("interactive", {}).get("body", {}).get("text", f"Requirement Summary for {session_data.get('service_name')}")
        await MessageHandler.log_message(
            db=db,
            conversation_id=conv.id,
            direction="OUTBOUND",
            message_type="interactive_button",
            text=body_text,
            raw_payload=payload or res
        )
        return res


    @staticmethod
    async def process_incoming_message(
        db: AsyncSession,
        parsed_msg: ParsedMessage
    ) -> None:
        """Core state machine message processing pipeline."""
        phone = parsed_msg.sender_phone
        user, conv = await MessageHandler.get_or_create_user_and_conv(
            db, phone, parsed_msg.sender_name
        )

        # 1. Log inbound message
        await MessageHandler.log_message(
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

        # 2. Check Universal Navigation & Reset Commands
        if input_lower in ["0", "menu", "/start", "start", "hi", "hello", "hey", "main menu", "home"]:
            await MessageHandler.transition_to_main_menu(db, user, conv)
            return

        if input_lower == "cancel":
            conv.session_data = {}
            conv.state = "MAIN_MENU"
            await db.commit()
            await MessageHandler.send_and_log_text(
                db=db, conv=conv, to=phone,
                text="❌ Action cancelled. Returning to the main menu."
            )
            await MessageHandler.send_and_log_main_menu(db=db, conv=conv, to=phone, user_name=user.name)
            return

        if input_lower in ["support", "talk to support", "agent", "human", "help"]:
            await MessageHandler.transition_to_support(db, user, conv)
            return

        # 3. Handle Special Human Handoff State
        if conv.status == "HUMAN_HANDOFF" or conv.state == "HUMAN_HANDOFF":
            is_menu_choice = bool(selection_id) or any(
                input_lower == k or input_lower.startswith(f"{k}.") or input_lower.startswith(f"{k} ")
                for k in [
                    "1", "2", "3", "4", "5", "6", "7", "8",
                    "website", "software", "mobile", "marketing", "seo",
                    "communication", "whatsapp", "student", "contact", "location", "address",
                    "menu_website", "menu_software", "menu_mobile", "menu_marketing",
                    "menu_communication", "menu_student", "menu_contact", "menu_support", "nav_main_menu"
                ]
            )
            if is_menu_choice:
                conv.status = "ACTIVE"
                conv.state = "MAIN_MENU"
                await db.commit()
            else:
                await MessageHandler.send_and_log_text(
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
            await MessageHandler.handle_main_menu_input(db, user, conv, raw_input, selection_id)
        elif state == "PRODUCT_INFO":
            await MessageHandler.handle_product_info_input(db, user, conv, raw_input, selection_id)
        elif state.endswith("_MENU") or state.startswith("ERP_MENU"):
            await MessageHandler.handle_submenu_input(db, user, conv, raw_input, selection_id)
        elif state == "CONTACT_MENU":
            await MessageHandler.handle_contact_menu_input(db, user, conv, raw_input, selection_id)
        elif state.startswith("COLLECT_") or state == "LEAD_CONFIRMATION":
            await MessageHandler.handle_lead_collection_input(db, user, conv, raw_input, selection_id)
        else:
            await MessageHandler.handle_direct_service_state(db, user, conv, raw_input, selection_id)

    @staticmethod
    async def transition_to_main_menu(db: AsyncSession, user: User, conv: Conversation) -> None:
        """Reset conversation session and show main menu."""
        conv.previous_state = conv.state
        conv.state = "MAIN_MENU"
        conv.status = "ACTIVE"
        conv.session_data = {}
        await db.commit()
        await MessageHandler.send_and_log_main_menu(db=db, conv=conv, to=user.phone_number, user_name=user.name)

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
        await MessageHandler.send_and_log_text(db=db, conv=conv, to=user.phone_number, text=text)

    @staticmethod
    async def handle_main_menu_input(
        db: AsyncSession,
        user: User,
        conv: Conversation,
        raw_input: str,
        selection_id: Optional[str]
    ) -> None:
        """Process input when user is at MAIN_MENU."""
        phone = user.phone_number
        target_val = selection_id or raw_input.strip()
        target_lower = target_val.lower()

        menu_mapping = {
            "1": ("WEBSITE_MENU", "menu_website"),
            "website": ("WEBSITE_MENU", "menu_website"),
            "website dev": ("WEBSITE_MENU", "menu_website"),
            "website development": ("WEBSITE_MENU", "menu_website"),
            "menu_website": ("WEBSITE_MENU", "menu_website"),

            "2": ("SOFTWARE_MENU", "menu_software"),
            "software": ("SOFTWARE_MENU", "menu_software"),
            "software dev": ("SOFTWARE_MENU", "menu_software"),
            "software development": ("SOFTWARE_MENU", "menu_software"),
            "menu_software": ("SOFTWARE_MENU", "menu_software"),

            "3": ("MOBILE_MENU", "menu_mobile"),
            "mobile": ("MOBILE_MENU", "menu_mobile"),
            "mobile apps": ("MOBILE_MENU", "menu_mobile"),
            "mobile app development": ("MOBILE_MENU", "menu_mobile"),
            "app": ("MOBILE_MENU", "menu_mobile"),
            "menu_mobile": ("MOBILE_MENU", "menu_mobile"),

            "4": ("MARKETING_MENU", "menu_marketing"),
            "seo": ("MARKETING_MENU", "menu_marketing"),
            "marketing": ("MARKETING_MENU", "menu_marketing"),
            "seo & digital marketing": ("MARKETING_MENU", "menu_marketing"),
            "digital marketing": ("MARKETING_MENU", "menu_marketing"),
            "menu_marketing": ("MARKETING_MENU", "menu_marketing"),

            "5": ("COMMUNICATION_MENU", "menu_communication"),
            "whatsapp": ("COMMUNICATION_MENU", "menu_communication"),
            "sms": ("COMMUNICATION_MENU", "menu_communication"),
            "voice": ("COMMUNICATION_MENU", "menu_communication"),
            "communication": ("COMMUNICATION_MENU", "menu_communication"),
            "whatsapp / sms / voice": ("COMMUNICATION_MENU", "menu_communication"),
            "menu_communication": ("COMMUNICATION_MENU", "menu_communication"),

            "6": ("STUDENT_MENU", "menu_student"),
            "student": ("STUDENT_MENU", "menu_student"),
            "student services": ("STUDENT_MENU", "menu_student"),
            "project": ("STUDENT_MENU", "menu_student"),
            "internship": ("STUDENT_MENU", "menu_student"),
            "menu_student": ("STUDENT_MENU", "menu_student"),

            "7": ("ERP_MENU_1", "menu_erp"),
            "erp": ("ERP_MENU_1", "menu_erp"),
            "management systems": ("ERP_MENU_1", "menu_erp"),
            "more erp systems": ("ERP_MENU_1", "menu_erp"),
            "menu_erp": ("ERP_MENU_1", "menu_erp"),

            "8": ("CONTACT_MENU", "menu_contact"),
            "help": ("CONTACT_MENU", "menu_contact"),
            "support": ("CONTACT_MENU", "menu_contact"),
            "help & support": ("CONTACT_MENU", "menu_contact"),
            "menu_help_support": ("CONTACT_MENU", "menu_contact"),
            "menu_contact": ("CONTACT_MENU", "menu_contact"),
            "contact": ("CONTACT_MENU", "menu_contact"),
        }
        
        # Keep backward compatibility for the direct keywords
        fallback_mapping = {
            "website": ("WEBSITE_MENU", "menu_website"),
            "website dev": ("WEBSITE_MENU", "menu_website"),
            "website development": ("WEBSITE_MENU", "menu_website"),
            "menu_website": ("WEBSITE_MENU", "menu_website"),

            "software": ("SOFTWARE_MENU", "menu_software"),
            "software dev": ("SOFTWARE_MENU", "menu_software"),
            "software development": ("SOFTWARE_MENU", "menu_software"),
            "menu_software": ("SOFTWARE_MENU", "menu_software"),

            "mobile": ("MOBILE_MENU", "menu_mobile"),
            "mobile apps": ("MOBILE_MENU", "menu_mobile"),
            "mobile app development": ("MOBILE_MENU", "menu_mobile"),
            "app": ("MOBILE_MENU", "menu_mobile"),
            "menu_mobile": ("MOBILE_MENU", "menu_mobile"),

            "seo": ("MARKETING_MENU", "menu_marketing"),
            "marketing": ("MARKETING_MENU", "menu_marketing"),
            "seo & digital marketing": ("MARKETING_MENU", "menu_marketing"),
            "digital marketing": ("MARKETING_MENU", "menu_marketing"),
            "menu_marketing": ("MARKETING_MENU", "menu_marketing"),

            "whatsapp": ("COMMUNICATION_MENU", "menu_communication"),
            "sms": ("COMMUNICATION_MENU", "menu_communication"),
            "voice": ("COMMUNICATION_MENU", "menu_communication"),
            "communication": ("COMMUNICATION_MENU", "menu_communication"),
            "whatsapp / sms / voice": ("COMMUNICATION_MENU", "menu_communication"),
            "menu_communication": ("COMMUNICATION_MENU", "menu_communication"),

            "student": ("STUDENT_MENU", "menu_student"),
            "student services": ("STUDENT_MENU", "menu_student"),
            "project": ("STUDENT_MENU", "menu_student"),
            "internship": ("STUDENT_MENU", "menu_student"),
            "menu_student": ("STUDENT_MENU", "menu_student"),

            "7": ("COLLECT_HMS", "menu_hms"),
            "hms": ("COLLECT_HMS", "menu_hms"),
            "hospital": ("COLLECT_HMS", "menu_hms"),
            "menu_hms": ("COLLECT_HMS", "menu_hms"),
            "software_hms": ("COLLECT_HMS", "menu_hms"),

            "8": ("COLLECT_LMS", "menu_lms"),
            "lms": ("COLLECT_LMS", "menu_lms"),
            "learning": ("COLLECT_LMS", "menu_lms"),
            "menu_lms": ("COLLECT_LMS", "menu_lms"),
            "software_lms": ("COLLECT_LMS", "menu_lms"),

            "9": ("COLLECT_TMS", "menu_tms"),
            "tms": ("COLLECT_TMS", "menu_tms"),
            "transport": ("COLLECT_TMS", "menu_tms"),
            "menu_tms": ("COLLECT_TMS", "menu_tms"),
            "software_tms": ("COLLECT_TMS", "menu_tms"),

            "10": ("COLLECT_MMS", "menu_mms"),
            "mms": ("COLLECT_MMS", "menu_mms"),
            "manufacturing": ("COLLECT_MMS", "menu_mms"),
            "menu_mms": ("COLLECT_MMS", "menu_mms"),
            "software_mms": ("COLLECT_MMS", "menu_mms"),

            "11": ("COLLECT_FMS", "menu_fms"),
            "fms": ("COLLECT_FMS", "menu_fms"),
            "finance": ("COLLECT_FMS", "menu_fms"),
            "financial": ("COLLECT_FMS", "menu_fms"),
            "menu_fms": ("COLLECT_FMS", "menu_fms"),
            "software_fms": ("COLLECT_FMS", "menu_fms"),

            "12": ("COLLECT_PMS", "menu_pms"),
            "pms": ("COLLECT_PMS", "menu_pms"),
            "menu_pms": ("COLLECT_PMS", "menu_pms"),
            "software_pms": ("COLLECT_PMS", "menu_pms"),

            "13": ("COLLECT_AMS", "menu_ams"),
            "ams": ("COLLECT_AMS", "menu_ams"),
            "asset": ("COLLECT_AMS", "menu_ams"),
            "menu_ams": ("COLLECT_AMS", "menu_ams"),
            "software_ams": ("COLLECT_AMS", "menu_ams"),

            "14": ("COLLECT_OMS", "menu_oms"),
            "oms": ("COLLECT_OMS", "menu_oms"),
            "order": ("COLLECT_OMS", "menu_oms"),
            "menu_oms": ("COLLECT_OMS", "menu_oms"),
            "software_oms": ("COLLECT_OMS", "menu_oms"),

            "15": ("COLLECT_WMS", "menu_wms"),
            "wms": ("COLLECT_WMS", "menu_wms"),
            "warehouse": ("COLLECT_WMS", "menu_wms"),
            "menu_wms": ("COLLECT_WMS", "menu_wms"),
            "software_wms": ("COLLECT_WMS", "menu_wms"),

            "16": ("COLLECT_SMS", "menu_sms"),
            "sms": ("COLLECT_SMS", "menu_sms"),
            "school": ("COLLECT_SMS", "menu_sms"),
            "menu_sms": ("COLLECT_SMS", "menu_sms"),
            "software_sms": ("COLLECT_SMS", "menu_sms"),

            "17": ("COLLECT_BMS", "menu_bms"),
            "bms": ("COLLECT_BMS", "menu_bms"),
            "business": ("COLLECT_BMS", "menu_bms"),
            "menu_bms": ("COLLECT_BMS", "menu_bms"),
            "software_bms": ("COLLECT_BMS", "menu_bms"),

            "contact": ("CONTACT_MENU", "menu_contact"),
            "menu_contact": ("CONTACT_MENU", "menu_contact"),
        }

        matched_state = None
        if target_lower == "7":
            res_opt = await db.execute(select(MenuOption).where(MenuOption.parent_state == "MAIN_MENU", MenuOption.sort_order == 7))
            opt_7 = res_opt.scalar_one_or_none()
            if opt_7 and "hms" in (opt_7.value or ""):
                matched_state = "COLLECT_HMS"

        if not matched_state:
            for key, (n_state, _) in menu_mapping.items():
                if target_lower == key:
                    matched_state = n_state
                    break
                elif key.isdigit():
                    if target_lower.startswith(key + ".") or target_lower.startswith(key + " "):
                        matched_state = n_state
                        break
                elif target_lower.startswith(key):
                    matched_state = n_state
                    break
        
        if not matched_state:
            for key, (n_state, _) in fallback_mapping.items():
                if target_lower == key or target_lower.startswith(key):
                    matched_state = n_state
                    break

        if matched_state:
            conv.previous_state = "MAIN_MENU"
            conv.state = matched_state
            await db.commit()

            if matched_state == "CORE_SERVICES_MENU":
                await MessageHandler.send_and_log_submenu(
                    db=db, conv=conv, to=phone, parent_state="CORE_SERVICES_MENU",
                    title="iZone Core Services",
                    description="Select a core service category:"
                )
            elif matched_state == "ERP_MENU_1":
                await MessageHandler.send_and_log_submenu(
                    db=db, conv=conv, to=phone, parent_state="ERP_MENU_1",
                    title="Management Systems",
                    description="Select an ERP system (Page 1):"
                )
            elif matched_state == "HELP_SUPPORT_MENU":
                await MessageHandler.send_and_log_submenu(
                    db=db, conv=conv, to=phone, parent_state="HELP_SUPPORT_MENU",
                    title="Help & Support",
                    description="How can we help you?"
                )
            elif matched_state == "WEBSITE_MENU":
                await MessageHandler.send_and_log_submenu(
                    db=db, conv=conv, to=phone, parent_state="WEBSITE_MENU",
                    title="Website Development",
                    description="Select a website service category to get started:"
                )
            elif matched_state == "SOFTWARE_MENU":
                await MessageHandler.send_and_log_submenu(
                    db=db, conv=conv, to=phone, parent_state="SOFTWARE_MENU",
                    title="Software Development",
                    description="Select a software solution category:"
                )
            elif matched_state == "MOBILE_MENU":
                await MessageHandler.send_and_log_submenu(
                    db=db, conv=conv, to=phone, parent_state="MOBILE_MENU",
                    title="Mobile App Development",
                    description="Select mobile app development service:"
                )
            elif matched_state == "MARKETING_MENU":
                await MessageHandler.send_and_log_submenu(
                    db=db, conv=conv, to=phone, parent_state="MARKETING_MENU",
                    title="SEO & Digital Marketing",
                    description="Choose your digital marketing growth channel:"
                )
            elif matched_state == "COMMUNICATION_MENU":
                await MessageHandler.send_and_log_submenu(
                    db=db, conv=conv, to=phone, parent_state="COMMUNICATION_MENU",
                    title="WhatsApp / SMS / Voice Services",
                    description="Select messaging or voice API solution:"
                )
            elif matched_state == "STUDENT_MENU":
                await MessageHandler.send_and_log_submenu(
                    db=db, conv=conv, to=phone, parent_state="STUDENT_MENU",
                    title="Student Services & Projects",
                    description="Select student training or project assistance:"
                )
            elif matched_state == "CONTACT_MENU":
                res = await workflow_engine.send_contact_info(to=phone)
                await MessageHandler.log_message(
                    db=db, conv_id=conv.id, direction="OUTBOUND",
                    message_type="interactive_button",
                    text=f"Company Details for {settings.COMPANY_NAME}",
                    raw_payload=res
                )
            elif matched_state == "HUMAN_HANDOFF":
                await MessageHandler.transition_to_support(db, user, conv)
            elif matched_state.startswith("COLLECT_") and matched_state[8:] in ["HMS", "LMS", "TMS", "MMS", "FMS", "PMS", "AMS", "OMS", "WMS", "SMS", "BMS"]:
                product_code = matched_state[8:].lower()
                service_slug = f"software-{product_code}"
                res_service = await db.execute(select(Service).where(Service.slug == service_slug))
                service = res_service.scalar_one_or_none()
                if service:
                    session_data = dict(conv.session_data or {})
                    session_data["service_id"] = service.id
                    session_data["service_name"] = service.name
                    session_data["parent_menu"] = "MAIN_MENU"

                    conv.session_data = session_data
                    conv.previous_state = "MAIN_MENU"
                    conv.state = "PRODUCT_INFO"
                    await db.commit()

                    method = getattr(workflow_engine, f"send_{product_code}_info", None)
                    if method:
                        res = await method(to=phone)
                    else:
                        res = await workflow_engine.send_hms_info(to=phone)

                    await MessageHandler.log_message(
                        db=db, conversation_id=conv.id, direction="OUTBOUND",
                        message_type="interactive_button",
                        text=f"Product Overview for {service.name}",
                        raw_payload=res
                    )
            return

        # Check if the input/selection matches any service menu option value directly (e.g. software_hms, software_lms)
        search_val = target_val
        if search_val.lower() in ["hms", "lms", "tms", "mms", "fms", "pms", "ams", "oms", "wms", "sms", "bms"]:
            search_val = f"software_{search_val.lower()}"
            
        from sqlalchemy.orm import selectinload
        res_opt = await db.execute(
            select(MenuOption)
            .where(MenuOption.value == search_val, MenuOption.active == True)
            .options(selectinload(MenuOption.service))
        )
        opt = res_opt.scalar_one_or_none()
        if opt:
            service_name = opt.service.name if opt.service else opt.label
            service_id = opt.service_id

            session_data = dict(conv.session_data or {})
            session_data["service_id"] = service_id
            session_data["service_name"] = service_name
            session_data["parent_menu"] = opt.parent_state

            conv.session_data = session_data
            conv.previous_state = conv.state

            # If HMS or LMS, show the feature overview first
            s_lower = service_name.lower()
            product_code = None
            for code in ["hms", "lms", "tms", "mms", "fms", "pms", "ams", "oms", "wms", "sms", "bms"]:
                if code in s_lower:
                    product_code = code
                    break
                    
            if product_code:
                conv.state = "PRODUCT_INFO"
                await db.commit()
                
                method = getattr(workflow_engine, f"send_{product_code}_info", None)
                if method:
                    res = await method(to=phone)
                else:
                    res = await workflow_engine.send_hms_info(to=phone)
                    
                await MessageHandler.log_message(
                    db=db, conversation_id=conv.id, direction="OUTBOUND",
                    message_type="interactive_button",
                    text=f"Product Overview for {service_name}",
                    raw_payload=res
                )
                return

            conv.state = "COLLECT_NAME"
            await db.commit()

            msg_text = f"Great! You selected *{service_name}* 🚀\n\n"
            wf_desc = get_workflow_description(service_name)
            if wf_desc:
                msg_text += f"{wf_desc}\n\n"
            msg_text += (
                "Let's collect a few details so our technical team can prepare an accurate proposal and estimate.\n\n"
                "*Step 1 of 8:* What is your full name?"
            )
            await MessageHandler.send_and_log_text(db=db, conv=conv, to=phone, text=msg_text)
            return


        faq = await faq_service.match_faq(db, raw_input)
        if faq:
            await MessageHandler.send_and_log_text(
                db=db, conv=conv, to=phone,
                text=f"💡 *Information:*\n{faq.answer}\n\nType *menu* to explore our services."
            )
            return

        await MessageHandler.send_and_log_text(
            db=db, conv=conv, to=phone,
            text="⚠️ Invalid selection. Please choose an option from the menu below."
        )
        await MessageHandler.send_and_log_main_menu(db=db, conv=conv, to=phone, user_name=user.name)

    @staticmethod
    async def handle_product_info_input(
        db: AsyncSession,
        user: User,
        conv: Conversation,
        raw_input: str,
        selection_id: Optional[str]
    ) -> None:
        """Process user input when viewing product info overview (HMS/LMS)."""
        phone = user.phone_number
        input_clean = raw_input.strip()
        input_lower = input_clean.lower()
        sel = selection_id or input_lower

        session_data = dict(conv.session_data or {})
        service_name = session_data.get("service_name", "")
        service_name_lower = service_name.lower()
        
        # Identify active product code
        product_code = None
        for code in ["hms", "lms", "tms", "mms", "fms", "pms", "ams", "oms", "wms", "sms", "bms"]:
            if code in service_name_lower:
                product_code = code
                break
        if not product_code:
            for code, keyword in [("hms", "hospital"), ("lms", "learning"), ("tms", "transport"), ("mms", "manufacturing"), ("fms", "financial"), ("pms", "project"), ("ams", "asset"), ("oms", "order"), ("wms", "warehouse"), ("sms", "school"), ("bms", "business")]:
                if keyword in service_name_lower:
                    product_code = code
                    break

        # Strip next_ prefix if present from Next Module CTA clicks
        if sel.startswith("next_"):
            sel = sel[5:]

        # Define module sequences for each product tour
        sequences = {
            "hms": ["hms_admin", "hms_opd", "hms_clinical", "hms_lab_pharmacy", "hms_store", "hms_er", "hms_billing"],
            "lms": ["lms_access", "lms_admin", "lms_teacher", "lms_student"],
            "tms": ["tms_fleet", "tms_dispatch", "tms_driver", "tms_fuel", "tms_gps", "tms_billing"],
            "mms": ["mms_bom", "mms_planning", "mms_orders", "mms_qa", "mms_maintenance", "mms_costing"],
            "fms": ["fms_gl", "fms_ap", "fms_ar", "fms_cash", "fms_tax", "fms_audit"],
            "pms": ["pms_planning", "pms_tasks", "pms_resources", "pms_budget", "pms_client", "pms_billing"],
            "ams": ["ams_registry", "ams_intake", "ams_custody", "ams_maintenance", "ams_valuation", "ams_audit"],
            "oms": ["oms_capture", "oms_allocation", "oms_fraud", "oms_fulfillment", "oms_shipping", "oms_returns"],
            "wms": ["wms_receiving", "wms_location", "wms_picking", "wms_replenishment", "wms_shipping", "wms_reports"],
            "sms": ["sms_directory", "sms_academics", "sms_attendance", "sms_exams", "sms_fees", "sms_auxiliary"],
            "bms": ["bms_crm", "bms_sales", "bms_purchasing", "bms_hr", "bms_inventory", "bms_bi"],
        }

        # Resolve numerical text inputs
        if sel.isdigit() and product_code in sequences:
            idx = int(sel) - 1
            seq = sequences[product_code]
            if 0 <= idx < len(seq):
                sel = seq[idx]

        # Resolve keyword replies
        elif product_code and product_code in sequences:
            for seq_id in sequences[product_code]:
                base_name = seq_id.split("_", 1)[1] if "_" in seq_id else seq_id
                words = base_name.replace("_", " ").split()
                if any(w in input_lower for w in words):
                    sel = seq_id
                    break

        # 1. Check if user selected to proceed to Demo/Lead collection
        if sel in ["btn_start_demo", "demo", "request", "yes", "confirm", "start", "request quote & demo ✅"]:
            conv.previous_state = "PRODUCT_INFO"
            conv.state = "COLLECT_NAME"
            await db.commit()

            msg_text = (
                f"Great! Let's collect a few details so our technical team can prepare an accurate proposal and estimate for *{service_name}*.\n\n"
                "*Step 1 of 8:* What is your full name?"
            )
            await MessageHandler.send_and_log_text(db=db, conv=conv, to=phone, text=msg_text)
            return

        # 2. Check if user wants to go back to the Main Menu
        elif sel in ["nav_main_menu", "menu", "back", "cancel", "no", "🏠 main menu", "🏠 return to main menu"]:
            await MessageHandler.transition_to_main_menu(db, user, conv)
            return

        # 3. Check if user wants to view the modules list menu again
        elif sel in ["btn_explore_modules", "explore", "tour", "explore modules 📋", "modules"]:
            method = getattr(workflow_engine, f"send_{product_code}_tour_menu", None)
            if method:
                res = await method(to=phone)
            else:
                res = await workflow_engine.send_hms_tour_menu(to=phone)

            await MessageHandler.log_message(
                db=db, conversation_id=conv.id, direction="OUTBOUND",
                message_type="interactive_list",
                text=f"Explore Modules for {service_name}",
                raw_payload=res
            )
            return

        # 4. Check if user selected a specific module to describe
        elif product_code and product_code in sequences and sel in sequences[product_code]:
            res = await workflow_engine.send_module_description(phone, sel)
            await MessageHandler.log_message(
                db=db, conversation_id=conv.id, direction="OUTBOUND",
                message_type="interactive_button",
                text=f"Module details: {sel}",
                raw_payload=res
            )
            return

        # 5. Invalid selection fallback (re-send tour menu)
        else:
            method = getattr(workflow_engine, f"send_{product_code}_tour_menu", None)
            if method:
                res = await method(to=phone)
            else:
                res = await workflow_engine.send_hms_tour_menu(to=phone)

            await MessageHandler.log_message(
                db=db, conversation_id=conv.id, direction="OUTBOUND",
                message_type="interactive_list",
                text=f"Explore Modules for {service_name}",
                raw_payload=res
            )

    @staticmethod
    async def handle_submenu_input(
        db: AsyncSession,
        user: User,
        conv: Conversation,
        raw_input: str,
        selection_id: Optional[str]
    ) -> None:
        """Process selection inside any of the service submenus."""
        phone = user.phone_number
        input_clean = raw_input.strip()
        input_lower = input_clean.lower()
        sel = selection_id or input_clean

        if input_lower in ["back", "b", "nav_main_menu", "menu", "main menu"]:
            await MessageHandler.transition_to_main_menu(db, user, conv)
            return

        options = await workflow_engine.get_menu_options(db, conv.state)
        selected_option = None

        for opt in options:
            if sel == opt.value or sel == opt.id:
                selected_option = opt
                break

        if not selected_option and input_clean.isdigit():
            idx = int(input_clean)
            if 1 <= idx <= len(options):
                selected_option = options[idx - 1]

        if not selected_option:
            for opt in options:
                if input_lower in opt.label.lower() or opt.label.lower() in input_lower:
                    selected_option = opt
                    break

        if selected_option:
            if selected_option.next_state in ["ERP_MENU_1", "ERP_MENU_2"]:
                conv.previous_state = conv.state
                conv.state = selected_option.next_state
                await db.commit()
                page_num = "1" if selected_option.next_state == "ERP_MENU_1" else "2"
                await MessageHandler.send_and_log_submenu(
                    db=db, conv=conv, to=phone, parent_state=selected_option.next_state,
                    title="Management Systems",
                    description=f"Select an ERP system (Page {page_num}):"
                )
                return

            service_name = selected_option.service.name if selected_option.service else selected_option.label
            service_id = selected_option.service_id

            session_data = dict(conv.session_data or {})
            session_data["service_id"] = service_id
            session_data["service_name"] = service_name
            session_data["parent_menu"] = conv.state

            conv.session_data = session_data
            conv.previous_state = conv.state

            # If ERP product, show the sub-modules overview tour first
            s_lower = service_name.lower()
            val_lower = (selected_option.value or "").lower()
            product_code = None
            for code in ["hms", "lms", "tms", "mms", "fms", "pms", "ams", "oms", "wms", "sms", "bms"]:
                if code in s_lower or f"_{code}" in val_lower or val_lower == code:
                    product_code = code
                    break
            if not product_code:
                for code, keyword in [("hms", "hospital"), ("lms", "learning"), ("tms", "transport"), ("mms", "manufacturing"), ("fms", "financial"), ("pms", "project"), ("ams", "asset"), ("oms", "order"), ("wms", "warehouse"), ("sms", "school"), ("bms", "business")]:
                    if keyword in s_lower or keyword in val_lower:
                        product_code = code
                        break

            if product_code:
                conv.state = "PRODUCT_INFO"
                await db.commit()
                
                method = getattr(workflow_engine, f"send_{product_code}_tour_menu", None)
                if not method:
                    method = getattr(workflow_engine, f"send_{product_code}_info", None)
                if method:
                    res = await method(to=phone)
                else:
                    res = await workflow_engine.send_hms_tour_menu(to=phone)
                    
                await MessageHandler.log_message(
                    db=db, conversation_id=conv.id, direction="OUTBOUND",
                    message_type="interactive_list",
                    text=f"Product Overview for {service_name}",
                    raw_payload=res
                )
                return

            conv.state = "COLLECT_NAME"
            await db.commit()

            msg_text = f"Great! You selected *{service_name}* 🚀\n\n"
            wf_desc = get_workflow_description(service_name)
            if wf_desc:
                msg_text += f"{wf_desc}\n\n"
            msg_text += (
                "Let's collect a few details so our technical team can prepare an accurate proposal and estimate.\n\n"
                "*Step 1 of 8:* What is your full name?"
            )
            await MessageHandler.send_and_log_text(db=db, conv=conv, to=phone, text=msg_text)
            return

        faq = await faq_service.match_faq(db, raw_input)
        if faq:
            await MessageHandler.send_and_log_text(
                db=db, conv=conv, to=phone,
                text=f"💡 *Information:*\n{faq.answer}\n\nType *back* for previous menu or *menu* for main menu."
            )
            return

        await MessageHandler.send_and_log_text(
            db=db, conv=conv, to=phone,
            text="⚠️ Invalid selection. Please choose one of the available options or type *menu*."
        )
        await MessageHandler.send_and_log_submenu(
            db=db, conv=conv, to=phone, parent_state=conv.state,
            title="Service Options",
            description="Please choose an option from the list below:"
        )

    @staticmethod
    async def handle_direct_service_state(
        db: AsyncSession,
        user: User,
        conv: Conversation,
        raw_input: str,
        selection_id: Optional[str]
    ) -> None:
        """Handle when state is set directly to a sub-service state."""
        conv.state = "COLLECT_NAME"
        await db.commit()
        await MessageHandler.send_and_log_text(
            db=db, conv=conv, to=user.phone_number,
            text="Let's collect your requirement details.\n\n*Step 1 of 8:* What is your full name?"
        )

    @staticmethod
    async def handle_contact_menu_input(
        db: AsyncSession,
        user: User,
        conv: Conversation,
        raw_input: str,
        selection_id: Optional[str]
    ) -> None:
        """Process actions in CONTACT_MENU."""
        phone = user.phone_number
        sel = selection_id or raw_input.strip().lower()

        if sel in ["btn_send_location", "map", "location", "pin", "1", "send map pin"]:
            res = await workflow_engine.send_location_pin(to=phone)
            await MessageHandler.log_message(
                db=db, conv_id=conv.id, direction="OUTBOUND",
                message_type="location",
                text=f"Location Pin: {settings.COMPANY_NAME}",
                raw_payload=res
            )
            await MessageHandler.send_and_log_text(
                db=db, conv=conv, to=phone,
                text="📍 Here is our office location on Google Maps! We look forward to meeting you.\n\nType *menu* to explore our services."
            )
            return
        elif sel in ["menu_support", "support", "talk to support", "2"]:
            await MessageHandler.transition_to_support(db, user, conv)
            return
        elif sel in ["nav_main_menu", "menu", "3"]:
            await MessageHandler.transition_to_main_menu(db, user, conv)
            return
        else:
            res = await workflow_engine.send_contact_info(to=phone)
            await MessageHandler.log_message(
                db=db, conv_id=conv.id, direction="OUTBOUND",
                message_type="interactive_button",
                text=f"Contact Info for {settings.COMPANY_NAME}",
                raw_payload=res
            )

    @staticmethod
    async def handle_lead_collection_input(
        db: AsyncSession,
        user: User,
        conv: Conversation,
        raw_input: str,
        selection_id: Optional[str]
    ) -> None:
        """8-step lead collection wizard with dynamic dummy estimate calculation."""
        phone = user.phone_number
        state = conv.state
        session_data = dict(conv.session_data or {})
        input_clean = raw_input.strip()
        input_lower = input_clean.lower()

        # Handle 'back' navigation at each step
        if input_lower in ["back", "b"]:
            if state == "COLLECT_NAME":
                parent_menu = session_data.get("parent_menu", "MAIN_MENU")
                conv.state = parent_menu
                await db.commit()
                if parent_menu == "MAIN_MENU":
                    await MessageHandler.send_and_log_main_menu(db=db, conv=conv, to=phone, user_name=user.name)
                else:
                    await MessageHandler.send_and_log_submenu(db=db, conv=conv, to=phone, parent_state=parent_menu, title="Services", description="Select service:")
                return
            elif state == "COLLECT_BUSINESS_TYPE":
                conv.state = "COLLECT_NAME"
                await db.commit()
                await MessageHandler.send_and_log_text(db=db, conv=conv, to=phone, text="*Step 1 of 8:* What is your full name?")
                return
            elif state == "COLLECT_REQUIREMENT":
                conv.state = "COLLECT_BUSINESS_TYPE"
                await db.commit()
                await MessageHandler.send_and_log_text(db=db, conv=conv, to=phone, text="*Step 2 of 8:* What type of business is this for?")
                return
            elif state == "COLLECT_TIMELINE":
                conv.state = "COLLECT_REQUIREMENT"
                await db.commit()
                await MessageHandler.send_and_log_text(db=db, conv=conv, to=phone, text="*Step 3 of 8:* Please describe your specific requirements.")
                return
            elif state == "COLLECT_BUDGET":
                conv.state = "COLLECT_TIMELINE"
                await db.commit()
                await MessageHandler.send_and_log_timeline(db=db, conv=conv, to=phone)
                return
            elif state == "COLLECT_EMAIL":
                conv.state = "COLLECT_BUDGET"
                await db.commit()
                await MessageHandler.send_and_log_budget(db=db, conv=conv, to=phone)
                return
            elif state == "COLLECT_PREFERRED_TIME":
                conv.state = "COLLECT_EMAIL"
                await db.commit()
                await MessageHandler.send_and_log_text(db=db, conv=conv, to=phone, text="*Step 6 of 8:* What is your email address?")
                return
            elif state == "COLLECT_CONTACT":
                conv.state = "COLLECT_PREFERRED_TIME"
                await db.commit()
                await MessageHandler.send_and_log_preferred_time(db=db, conv=conv, to=phone)
                return
            elif state == "LEAD_CONFIRMATION":
                conv.state = "COLLECT_CONTACT"
                await db.commit()
                await MessageHandler.send_and_log_text(db=db, conv=conv, to=phone, text=f"*Step 8 of 8:* Confirm contact phone number (Currently {session_data.get('phone', phone)}):")
                return

        # ----------------------------------------------------
        # Step 1: COLLECT_NAME
        # ----------------------------------------------------
        if state == "COLLECT_NAME":
            if not input_clean:
                await MessageHandler.send_and_log_text(db=db, conv=conv, to=phone, text="Please enter your name:")
                return
            session_data["name"] = input_clean
            conv.session_data = session_data
            conv.previous_state = "COLLECT_NAME"
            conv.state = "COLLECT_BUSINESS_TYPE"
            await db.commit()

            await MessageHandler.send_and_log_text(
                db=db, conv=conv, to=phone,
                text=(
                    f"Thanks {input_clean}! 👍\n\n"
                    "*Step 2 of 8:* What type of business or organization is this for?\n"
                    "_(e.g. Retail Shop, Clinic/Hospital, Education, Real Estate, Tech Startup, College Project)_"
                )
            )
            return

        # ----------------------------------------------------
        # Step 2: COLLECT_BUSINESS_TYPE
        # ----------------------------------------------------
        elif state == "COLLECT_BUSINESS_TYPE":
            if not input_clean:
                await MessageHandler.send_and_log_text(db=db, conv=conv, to=phone, text="Please enter your business or project type:")
                return
            session_data["business_type"] = input_clean
            conv.session_data = session_data
            conv.previous_state = "COLLECT_BUSINESS_TYPE"
            conv.state = "COLLECT_REQUIREMENT"
            await db.commit()

            await MessageHandler.send_and_log_text(
                db=db, conv=conv, to=phone,
                text=(
                    "*Step 3 of 8:* Please describe your specific requirements or features needed.\n"
                    "_(e.g. Online payment, customer login, Android & iOS app, SEO ranking, final year project guidance)_"
                )
            )
            return

        # ----------------------------------------------------
        # Step 3: COLLECT_REQUIREMENT
        # ----------------------------------------------------
        elif state == "COLLECT_REQUIREMENT":
            if not input_clean:
                await MessageHandler.send_and_log_text(db=db, conv=conv, to=phone, text="Please describe your requirements:")
                return
            session_data["requirement"] = input_clean
            conv.session_data = session_data
            conv.previous_state = "COLLECT_REQUIREMENT"
            conv.state = "COLLECT_TIMELINE"
            await db.commit()

            await MessageHandler.send_and_log_timeline(db=db, conv=conv, to=phone)
            return

        # ----------------------------------------------------
        # Step 4: COLLECT_TIMELINE (New)
        # ----------------------------------------------------
        elif state == "COLLECT_TIMELINE":
            sel = selection_id or input_clean
            timeline_map = {
                "time_urgent": "Urgent (< 2 Weeks)",
                "1": "Urgent (< 2 Weeks)",
                "urgent": "Urgent (< 2 Weeks)",
                "urgent (< 2 weeks)": "Urgent (< 2 Weeks)",

                "time_standard": "Standard (1 Month)",
                "2": "Standard (1 Month)",
                "1 month": "Standard (1 Month)",
                "standard": "Standard (1 Month)",

                "time_extended": "2–3 Months",
                "3": "2–3 Months",
                "2-3 months": "2–3 Months",
                "extended": "2–3 Months",

                "time_flexible": "Flexible / Exploring",
                "4": "Flexible / Exploring",
                "flexible": "Flexible / Exploring",
            }
            chosen_timeline = timeline_map.get(sel.lower()) or input_clean
            session_data["timeline"] = chosen_timeline
            conv.session_data = session_data
            conv.previous_state = "COLLECT_TIMELINE"
            conv.state = "COLLECT_BUDGET"
            await db.commit()

            await MessageHandler.send_and_log_budget(db=db, conv=conv, to=phone)
            return

        # ----------------------------------------------------
        # Step 5: COLLECT_BUDGET
        # ----------------------------------------------------
        elif state == "COLLECT_BUDGET":
            sel = selection_id or input_clean
            budget_map = {
                "budget_1": "Below ₹25,000",
                "1": "Below ₹25,000",
                "below 25000": "Below ₹25,000",
                "below ₹25,000": "Below ₹25,000",

                "budget_2": "₹25,000 – ₹50,000",
                "2": "₹25,000 – ₹50,000",
                "25000 - 50000": "₹25,000 – ₹50,000",
                "₹25,000 – ₹50,000": "₹25,000 – ₹50,000",

                "budget_3": "₹50,000 – ₹1,00,000",
                "3": "₹50,000 – ₹1,00,000",
                "50000 - 100000": "₹50,000 – ₹1,00,000",
                "₹50,000 – ₹1,00,000": "₹50,000 – ₹1,00,000",

                "budget_4": "Above ₹1,00,000",
                "4": "Above ₹1,00,000",
                "above 100000": "Above ₹1,00,000",
                "above ₹1,00,000": "Above ₹1,00,000",

                "budget_5": "Flexible / Not Decided",
                "5": "Flexible / Not Decided",
                "flexible": "Flexible / Not Decided",
                "not decided": "Flexible / Not Decided",
            }

            chosen_budget = budget_map.get(sel.lower()) or input_clean
            session_data["budget"] = chosen_budget
            conv.session_data = session_data
            conv.previous_state = "COLLECT_BUDGET"
            conv.state = "COLLECT_EMAIL"
            await db.commit()

            await MessageHandler.send_and_log_text(
                db=db, conv=conv, to=phone,
                text="*Step 6 of 8:* What is your email address?\n_(e.g. name@company.com or type 'skip' if you prefer phone only)_"
            )
            return

        # ----------------------------------------------------
        # Step 6: COLLECT_EMAIL
        # ----------------------------------------------------
        elif state == "COLLECT_EMAIL":
            email_val = input_clean
            if input_lower == "skip":
                email_val = None
            elif "@" not in email_val or "." not in email_val:
                if len(email_val) > 3 and not email_val.isdigit():
                    pass
                else:
                    await MessageHandler.send_and_log_text(
                        db=db, conv=conv, to=phone,
                        text="⚠️ Please enter a valid email address (e.g. name@example.com) or type *skip*:"
                    )
                    return

            session_data["email"] = email_val
            conv.session_data = session_data
            conv.previous_state = "COLLECT_EMAIL"
            conv.state = "COLLECT_PREFERRED_TIME"
            await db.commit()

            await MessageHandler.send_and_log_preferred_time(db=db, conv=conv, to=phone)
            return

        # ----------------------------------------------------
        # Step 7: COLLECT_PREFERRED_TIME (New)
        # ----------------------------------------------------
        elif state == "COLLECT_PREFERRED_TIME":
            sel = selection_id or input_clean
            slot_map = {
                "slot_morning": "Morning (10:00 AM – 1:00 PM)",
                "1": "Morning (10:00 AM – 1:00 PM)",
                "morning": "Morning (10:00 AM – 1:00 PM)",

                "slot_afternoon": "Afternoon (2:00 PM – 5:00 PM)",
                "2": "Afternoon (2:00 PM – 5:00 PM)",
                "afternoon": "Afternoon (2:00 PM – 5:00 PM)",

                "slot_evening": "Evening (5:00 PM – 7:00 PM)",
                "3": "Evening (5:00 PM – 7:00 PM)",
                "evening": "Evening (5:00 PM – 7:00 PM)",

                "slot_chat_only": "WhatsApp Chat Only",
                "4": "WhatsApp Chat Only",
                "chat only": "WhatsApp Chat Only",
                "whatsapp only": "WhatsApp Chat Only",
            }
            chosen_slot = slot_map.get(sel.lower()) or input_clean
            session_data["preferred_contact_time"] = chosen_slot
            conv.session_data = session_data
            conv.previous_state = "COLLECT_PREFERRED_TIME"
            conv.state = "COLLECT_CONTACT"
            await db.commit()

            await MessageHandler.send_and_log_text(
                db=db, conv=conv, to=phone,
                text=(
                    f"*Step 8 of 8: Contact Phone Number*\n\n"
                    f"We currently have your WhatsApp number: *{phone}*.\n\n"
                    f"Reply with a different number if desired, or type *OK* to use this number."
                )
            )
            return

        # ----------------------------------------------------
        # Step 8: COLLECT_CONTACT
        # ----------------------------------------------------
        elif state == "COLLECT_CONTACT":
            final_phone = phone
            if input_lower not in ["ok", "yes", "confirm", "y", "same"]:
                clean_phone = re.sub(r"[^\d+]", "", input_clean)
                if len(clean_phone) >= 10:
                    final_phone = clean_phone

            session_data["phone"] = final_phone

            # Compute dummy quote estimate
            estimate_info = calculate_dummy_estimate(
                service_name=session_data.get("service_name", "Service"),
                budget=session_data.get("budget"),
                timeline=session_data.get("timeline")
            )
            session_data["estimated_amount"] = estimate_info["estimated_range"]

            conv.session_data = session_data
            conv.previous_state = "COLLECT_CONTACT"
            conv.state = "LEAD_CONFIRMATION"
            await db.commit()

            await MessageHandler.send_and_log_confirmation_card(db=db, conv=conv, to=phone, session_data=session_data)
            return


        # ----------------------------------------------------
        # Step 9: LEAD_CONFIRMATION
        # ----------------------------------------------------
        elif state == "LEAD_CONFIRMATION":
            sel = selection_id or input_lower

            if sel in ["btn_confirm_lead", "confirm", "1", "yes", "confirm ✅", "confirm"]:
                lead = await lead_service.create_lead_from_session(db, user, conv, session_data)

                service_name = session_data.get("service_name", "Service")
                lead_name = session_data.get("name", user.name or "Valued Client")
                confirm_phone = session_data.get("phone", phone)
                est_amount = session_data.get("estimated_amount", "Custom Quote")
                preferred_time = session_data.get("preferred_contact_time", "business hours")

                receipt_text = (
                    f"🎉 *Thank you, {lead_name}!* ✅\n\n"
                    f"Your requirement for *{service_name}* (Ref: #LEAD-{lead.id:04d}) has been submitted successfully.\n\n"
                    f"💰 *Estimated Budget Scope:* {est_amount}\n"
                    f"🕒 *Preferred Discussion Time:* {preferred_time}\n"
                    f"📞 *Contact Number:* {confirm_phone}\n\n"
                    f"Our technical consultant will connect with you during your preferred slot.\n\n"
                    f"Type *menu* to explore more services or *support* to chat with an agent."
                )
                await MessageHandler.send_and_log_text(db=db, conv=conv, to=phone, text=receipt_text)

                conv.session_data = {}
                conv.state = "MAIN_MENU"
                conv.status = "ACTIVE"
                await db.commit()
                return

            elif sel in ["btn_edit_lead", "edit", "2", "edit ✏️"]:
                conv.state = "COLLECT_NAME"
                await db.commit()
                await MessageHandler.send_and_log_text(
                    db=db, conv=conv, to=phone,
                    text="✏️ *Editing details:*\n\n*Step 1 of 8:* What is your full name?"
                )
                return

            elif sel in ["btn_cancel_lead", "cancel", "3", "cancel ❌"]:
                conv.session_data = {}
                conv.state = "MAIN_MENU"
                await db.commit()
                await MessageHandler.send_and_log_text(
                    db=db, conv=conv, to=phone,
                    text="❌ Requirement submission cancelled. Returning to main menu."
                )
                await MessageHandler.send_and_log_main_menu(db=db, conv=conv, to=phone, user_name=user.name)
                return

            else:
                await MessageHandler.send_and_log_confirmation_card(db=db, conv=conv, to=phone, session_data=session_data)


message_handler = MessageHandler()
