"""Handler for contact info and support request workflows."""
import re
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, Conversation, Lead
from app.services.workflow_engine import (
    workflow_engine,
    SUPPORT_SERVICE_OPTIONS,
    PREFERRED_TIME_OPTIONS,
)
from app.services.handlers.base_handler import BaseHandler, settings


class ContactSupportHandler:
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

        if any(k in sel for k in ["location", "map", "pin", "address"]) or sel in ["btn_send_location", "1"]:
            res = await workflow_engine.send_location_pin(to=phone)
            await BaseHandler.log_message(
                db=db, conversation_id=conv.id, direction="OUTBOUND",
                message_type="location",
                text=f"Location Pin: {settings.COMPANY_NAME}",
                raw_payload=res
            )
            await BaseHandler.send_and_log_text(
                db=db, conv=conv, to=phone,
                text="📍 Here is our office location on Google Maps! We look forward to meeting you.\n\nType *menu* to explore our services."
            )
            return
        elif any(k in sel for k in ["support", "talk", "agent", "human", "callback"]) or sel in ["menu_support", "2"]:
            await ContactSupportHandler.start_support_workflow(db, user, conv)
            return
        elif any(k in sel for k in ["menu", "home", "main"]) or sel in ["nav_main_menu", "3"]:
            await BaseHandler.transition_to_main_menu(db, user, conv)
            return
        else:
            res = await workflow_engine.send_contact_info(to=phone)
            await BaseHandler.log_message(
                db=db, conversation_id=conv.id, direction="OUTBOUND",
                message_type="interactive_button",
                text=f"Contact Info for {settings.COMPANY_NAME}",
                raw_payload=res
            )

    @staticmethod
    async def start_support_workflow(db: AsyncSession, user: User, conv: Conversation) -> None:
        """Initiate the 3-step support callback workflow."""
        phone = user.phone_number
        conv.previous_state = conv.state
        session_data = dict(conv.session_data or {})
        session_data["in_support_workflow"] = True
        conv.session_data = session_data

        conv.state = "SUPPORT_NAME"
        await db.commit()

        text = (
            "👤 *iZone Support — Step 1 of 3: Your Name*\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Please enter your full name so our technical consultant knows who they will be speaking with:\n\n"
            "_(Type your name below or type *cancel* to return to menu)_"
        )
        await BaseHandler.send_and_log_text(db=db, conv=conv, to=phone, text=text)

    @staticmethod
    async def handle_support_workflow_input(
        db: AsyncSession,
        user: User,
        conv: Conversation,
        raw_input: str,
        selection_id: Optional[str]
    ) -> None:
        """Handle steps for 3-step support callback request."""
        phone = user.phone_number
        state = conv.state
        input_clean = raw_input.strip()
        input_lower = input_clean.lower()
        session_data = dict(conv.session_data or {})

        # Step 1: SUPPORT_NAME
        if state == "SUPPORT_NAME":
            if not input_clean or len(input_clean) < 2 or not re.search(r"[a-zA-Z\u0B80-\u0BFF]", input_clean):
                await BaseHandler.send_and_log_text(
                    db=db, conv=conv, to=phone,
                    text="⚠️ Please enter a valid name (at least 2 letters):"
                )
                return

            name = input_clean.title()
            session_data["support_name"] = name
            conv.session_data = session_data
            conv.previous_state = "SUPPORT_NAME"
            conv.state = "SUPPORT_SERVICE"
            await db.commit()

            res = await workflow_engine.send_support_service_selection(to=phone, user_name=name)
            await BaseHandler.log_message(
                db=db, conversation_id=conv.id, direction="OUTBOUND",
                message_type="interactive_list",
                text="Support Service Selection Menu",
                raw_payload=res
            )
            return

        # Step 2: SUPPORT_SERVICE
        elif state == "SUPPORT_SERVICE":
            sel = (selection_id or input_clean).strip()
            sel_lower = sel.lower()

            is_other = (
                sel_lower in ["sup_other", "other", "custom", "other / custom", "other / custom need", "other need", "9"]
                or sel_lower.startswith("other")
            )

            if input_clean.isdigit():
                idx = int(input_clean)
                if 1 <= idx <= len(SUPPORT_SERVICE_OPTIONS):
                    opt = SUPPORT_SERVICE_OPTIONS[idx - 1]
                    if opt["id"] == "sup_other":
                        is_other = True
                    else:
                        sel = opt["title"]
                        sel_lower = sel.lower()

            if is_other:
                conv.previous_state = "SUPPORT_SERVICE"
                conv.state = "SUPPORT_CUSTOM_SERVICE"
                await db.commit()

                await BaseHandler.send_and_log_text(
                    db=db, conv=conv, to=phone,
                    text=(
                        "✏️ *Step 2: Custom Service / Need*\n"
                        "━━━━━━━━━━━━━━━━━━━━\n"
                        "Please describe the service, project, or technical issue you need assistance with:\n\n"
                        "_(Type your details below)_"
                    )
                )
                return

            chosen_service = None
            for opt in SUPPORT_SERVICE_OPTIONS:
                if sel == opt["id"] or sel_lower == opt["title"].lower():
                    chosen_service = opt["title"]
                    break

            if not chosen_service:
                for opt in SUPPORT_SERVICE_OPTIONS:
                    if opt["title"].lower() in sel_lower or sel_lower in opt["title"].lower():
                        chosen_service = opt["title"]
                        break

            if not chosen_service:
                chosen_service = input_clean

            session_data["support_service"] = chosen_service
            conv.session_data = session_data
            conv.previous_state = "SUPPORT_SERVICE"
            conv.state = "SUPPORT_TIME"
            await db.commit()

            res = await workflow_engine.send_support_time_selection(to=phone, user_name=session_data.get("support_name"))
            await BaseHandler.log_message(
                db=db, conversation_id=conv.id, direction="OUTBOUND",
                message_type="interactive_list",
                text="Support Preferred Time Selection",
                raw_payload=res
            )
            return

        # Step 2b: SUPPORT_CUSTOM_SERVICE
        elif state == "SUPPORT_CUSTOM_SERVICE":
            if not input_clean:
                await BaseHandler.send_and_log_text(
                    db=db, conv=conv, to=phone,
                    text="⚠️ Please type a brief description of what you need help with:"
                )
                return

            session_data["support_service"] = input_clean
            conv.session_data = session_data
            conv.previous_state = "SUPPORT_CUSTOM_SERVICE"
            conv.state = "SUPPORT_TIME"
            await db.commit()

            res = await workflow_engine.send_support_time_selection(to=phone, user_name=session_data.get("support_name"))
            await BaseHandler.log_message(
                db=db, conversation_id=conv.id, direction="OUTBOUND",
                message_type="interactive_list",
                text="Support Preferred Time Selection",
                raw_payload=res
            )
            return

        # Step 3: SUPPORT_TIME
        elif state == "SUPPORT_TIME":
            sel = (selection_id or input_clean).strip()
            sel_lower = sel.lower()

            is_other = (
                sel_lower in ["slot_other", "other", "custom", "other / custom", "5"]
                or sel_lower.startswith("other")
            )

            if input_clean.isdigit():
                idx = int(input_clean)
                if 1 <= idx <= len(PREFERRED_TIME_OPTIONS):
                    opt = PREFERRED_TIME_OPTIONS[idx - 1]
                    if opt["id"] == "slot_other":
                        is_other = True
                    else:
                        sel = opt["title"]
                        sel_lower = sel.lower()

            if is_other:
                conv.previous_state = "SUPPORT_TIME"
                conv.state = "SUPPORT_CUSTOM_TIME"
                await db.commit()

                await BaseHandler.send_and_log_text(
                    db=db, conv=conv, to=phone,
                    text=(
                        "🕒 *Custom Preferred Time*\n"
                        "━━━━━━━━━━━━━━━━━━━━\n"
                        "Please specify what day or time works best for you (e.g., 'Tomorrow at 11 AM'):\n\n"
                        "_(Type your preferred time below)_"
                    )
                )
                return

            chosen_slot = None
            for opt in PREFERRED_TIME_OPTIONS:
                if sel == opt["id"] or sel_lower == opt["title"].lower():
                    chosen_slot = opt["title"]
                    break

            if not chosen_slot:
                for opt in PREFERRED_TIME_OPTIONS:
                    if opt["title"].lower() in sel_lower or sel_lower in opt["title"].lower():
                        chosen_slot = opt["title"]
                        break

            if not chosen_slot:
                chosen_slot = input_clean

            session_data["support_time"] = chosen_slot
            conv.session_data = session_data

            await ContactSupportHandler.complete_support_request(db, user, conv, session_data)
            return

        # Step 3b: SUPPORT_CUSTOM_TIME
        elif state == "SUPPORT_CUSTOM_TIME":
            if not input_clean:
                await BaseHandler.send_and_log_text(
                    db=db, conv=conv, to=phone,
                    text="⚠️ Please type your preferred day or time to speak with our team:"
                )
                return

            session_data["support_time"] = input_clean
            conv.session_data = session_data

            await ContactSupportHandler.complete_support_request(db, user, conv, session_data)
            return

    @staticmethod
    async def complete_support_request(
        db: AsyncSession,
        user: User,
        conv: Conversation,
        session_data: Dict[str, Any]
    ) -> None:
        """Register the support lead and transition user into human support handoff."""
        phone = user.phone_number
        name = session_data.get("support_name") or user.name or "Valued Client"
        service = session_data.get("support_service") or "General Technical Inquiry"
        time_slot = session_data.get("support_time") or "Earliest Available Slot"

        lead = Lead(
            user_id=user.id,
            conversation_id=conv.id,
            name=name,
            phone_number=phone,
            business_type="Support Callback Request",
            requirement=f"[Support Callback] {service}",
            budget="Support Request",
            timeline=time_slot,
            preferred_contact_time=time_slot,
            status="NEW",
            source="WHATSAPP_SUPPORT",
        )
        db.add(lead)
        await db.flush()

        ticket_ref = f"#SUP-{lead.id:04d}"

        conv.previous_state = conv.state
        conv.state = "HUMAN_HANDOFF"
        conv.status = "HUMAN_HANDOFF"
        conv.session_data = {}
        await db.commit()

        receipt_text = (
            "✅ *Support Callback Request Registered!*\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"🎫 *Ticket Ref:* {ticket_ref}\n"
            f"👤 *Name:* {name}\n"
            f"📞 *Contact:* {phone}\n"
            f"🛠️ *Service Needed:* {service}\n"
            f"🕒 *Preferred Time to Talk:* {time_slot}\n\n"
            f"Our technical specialist will call/message you during your preferred slot (*{time_slot}*).\n\n"
            f"🏢 *Office Hours:* {settings.COMPANY_WORKING_HOURS}\n"
            f"📞 *Direct Phone:* {settings.COMPANY_PHONE}\n\n"
            "👤 *Live Support Chat:* You are now connected to our support desk. Any message you type here will be reviewed by our team.\n\n"
            "💡 Type *menu* at any time to return to the automated service menu."
        )
        await BaseHandler.send_and_log_text(db=db, conv=conv, to=phone, text=receipt_text)
