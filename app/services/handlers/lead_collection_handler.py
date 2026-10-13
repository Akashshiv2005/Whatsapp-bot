"""Handler for 8-step lead collection wizard."""
import asyncio
import re
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, Conversation
from app.services.workflow_engine import (
    workflow_engine,
    calculate_dummy_estimate,
    BUSINESS_TYPE_OPTIONS,
    TIMELINE_OPTIONS,
    BUDGET_OPTIONS,
    PREFERRED_TIME_OPTIONS,
)
from app.services.lead_service import lead_service
from app.services.email_service import email_service
from app.services.handlers.base_handler import BaseHandler, settings
from app.core.logging import logger


class LeadCollectionHandler:
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
                    await BaseHandler.send_and_log_main_menu(db=db, conv=conv, to=phone, user_name=user.name)
                else:
                    await BaseHandler.send_and_log_submenu(db=db, conv=conv, to=phone, parent_state=parent_menu, title="Services", description="Select service:")
                return
            elif state in ["COLLECT_BUSINESS_TYPE", "COLLECT_CUSTOM_BUSINESS_TYPE"]:
                conv.state = "COLLECT_NAME"
                await db.commit()
                await BaseHandler.send_and_log_text(db=db, conv=conv, to=phone, text="*Step 1 of 8:* What is your full name?")
                return
            elif state == "COLLECT_REQUIREMENT":
                conv.state = "COLLECT_BUSINESS_TYPE"
                await db.commit()
                await BaseHandler.send_and_log_business_type_selection(db=db, conv=conv, to=phone, user_name=session_data.get("name"))
                return
            elif state in ["COLLECT_TIMELINE", "COLLECT_CUSTOM_REQUIREMENT"]:
                conv.state = "COLLECT_REQUIREMENT"
                await db.commit()
                await BaseHandler.send_and_log_requirement_selection(db=db, conv=conv, to=phone, session_data=session_data)
                return
            elif state in ["COLLECT_BUDGET", "COLLECT_CUSTOM_TIMELINE"]:
                conv.state = "COLLECT_TIMELINE"
                await db.commit()
                await BaseHandler.send_and_log_timeline(db=db, conv=conv, to=phone)
                return
            elif state in ["COLLECT_EMAIL", "COLLECT_CUSTOM_BUDGET"]:
                conv.state = "COLLECT_BUDGET"
                await db.commit()
                await BaseHandler.send_and_log_budget(db=db, conv=conv, to=phone)
                return
            elif state == "COLLECT_PREFERRED_TIME":
                conv.state = "COLLECT_EMAIL"
                await db.commit()
                await BaseHandler.send_and_log_text(db=db, conv=conv, to=phone, text="*Step 6 of 8:* What is your email address?\n_(Type 'skip' if you prefer phone only)_")
                return
            elif state in ["COLLECT_CONTACT", "COLLECT_CUSTOM_PREFERRED_TIME"]:
                conv.state = "COLLECT_PREFERRED_TIME"
                await db.commit()
                await BaseHandler.send_and_log_preferred_time(db=db, conv=conv, to=phone)
                return
            elif state == "LEAD_CONFIRMATION":
                conv.state = "COLLECT_CONTACT"
                await db.commit()
                await BaseHandler.send_and_log_text(db=db, conv=conv, to=phone, text=f"*Step 8 of 8:* Confirm contact phone number (Currently {session_data.get('phone', phone)}):")
                return

        # ----------------------------------------------------
        # Step 1: COLLECT_NAME
        # ----------------------------------------------------
        if state == "COLLECT_NAME":
            if not input_clean:
                await BaseHandler.send_and_log_text(db=db, conv=conv, to=phone, text="⚠️ Please enter your name:")
                return

            if any(char.isdigit() for char in input_clean):
                await BaseHandler.send_and_log_text(
                    db=db, conv=conv, to=phone,
                    text="⚠️ Name must not contain any numbers. Please enter your valid full name (letters only):"
                )
                return

            clean_name = re.sub(r"[\s\.\'\-]", "", input_clean)
            if not clean_name.isalpha() or len(clean_name) < 2:
                await BaseHandler.send_and_log_text(
                    db=db, conv=conv, to=phone,
                    text="⚠️ Please enter a valid name using letters only (minimum 2 letters):"
                )
                return

            session_data["name"] = input_clean
            conv.session_data = session_data
            conv.previous_state = "COLLECT_NAME"
            conv.state = "COLLECT_BUSINESS_TYPE"
            await db.commit()

            await BaseHandler.send_and_log_business_type_selection(
                db=db, conv=conv, to=phone, user_name=input_clean
            )
            return

        # ----------------------------------------------------
        # Step 2: COLLECT_BUSINESS_TYPE (Selection based + Other)
        # ----------------------------------------------------
        elif state == "COLLECT_BUSINESS_TYPE":
            sel = (selection_id or input_clean).strip()
            sel_lower = sel.lower()

            is_other = (
                sel_lower in ["biz_other", "other", "custom", "other / custom", "others"]
                or sel_lower.startswith("other")
            )
            if input_clean.isdigit():
                idx = int(input_clean)
                if 1 <= idx <= len(BUSINESS_TYPE_OPTIONS):
                    matched_opt = BUSINESS_TYPE_OPTIONS[idx - 1]
                    if matched_opt["id"] == "biz_other":
                        is_other = True
                    else:
                        sel = matched_opt["title"]
                        sel_lower = sel.lower()

            if is_other:
                conv.previous_state = "COLLECT_BUSINESS_TYPE"
                conv.state = "COLLECT_CUSTOM_BUSINESS_TYPE"
                await db.commit()

                await BaseHandler.send_and_log_text(
                    db=db, conv=conv, to=phone,
                    text=(
                        "💼 *Business / Organization Category*\n\n"
                        "🏢 *Custom Business Type:*\n"
                        "Please type your custom business or organization category manually below:"
                    )
                )
                return

            chosen_biz_type = None
            for opt in BUSINESS_TYPE_OPTIONS:
                if sel == opt["id"] or sel_lower == opt["title"].lower():
                    chosen_biz_type = opt["title"]
                    break

            if not chosen_biz_type and not input_clean.isdigit():
                for opt in BUSINESS_TYPE_OPTIONS:
                    if opt["title"].lower() in sel_lower or sel_lower in opt["title"].lower():
                        chosen_biz_type = opt["title"]
                        break

            # Fallback for direct free-form text input
            if not chosen_biz_type:
                chosen_biz_type = input_clean

            session_data["business_type"] = chosen_biz_type
            conv.session_data = session_data
            conv.previous_state = "COLLECT_BUSINESS_TYPE"
            conv.state = "COLLECT_REQUIREMENT"
            await db.commit()

            await BaseHandler.send_and_log_requirement_selection(
                db=db, conv=conv, to=phone, session_data=session_data
            )
            return

        # ----------------------------------------------------
        # Step 2b: COLLECT_CUSTOM_BUSINESS_TYPE (When "Other" was clicked)
        # ----------------------------------------------------
        elif state == "COLLECT_CUSTOM_BUSINESS_TYPE":
            if not input_clean:
                await BaseHandler.send_and_log_text(
                    db=db, conv=conv, to=phone,
                    text="💼 *Business / Organization Category:*\n\nPlease type your business or organization category manually below:"
                )
                return

            session_data["business_type"] = input_clean
            conv.session_data = session_data
            conv.previous_state = "COLLECT_CUSTOM_BUSINESS_TYPE"
            conv.state = "COLLECT_REQUIREMENT"
            await db.commit()

            await BaseHandler.send_and_log_requirement_selection(
                db=db, conv=conv, to=phone, session_data=session_data
            )
            return

        # ----------------------------------------------------
        # Step 3: COLLECT_REQUIREMENT (Service-based options + Other)
        # ----------------------------------------------------
        elif state == "COLLECT_REQUIREMENT":
            sel = (selection_id or input_clean).strip()
            sel_lower = sel.lower()

            req_options = workflow_engine.get_requirement_options(
                service_name=session_data.get("service_name"),
                parent_menu=session_data.get("parent_menu")
            )

            is_other = (
                sel_lower in ["req_other", "other", "custom", "other / custom", "other requirement", "others"]
                or sel_lower.startswith("other")
            )
            if input_clean.isdigit():
                idx = int(input_clean)
                if 1 <= idx <= len(req_options):
                    matched_opt = req_options[idx - 1]
                    if matched_opt["id"] == "req_other":
                        is_other = True
                    else:
                        sel = matched_opt["title"]
                        sel_lower = sel.lower()

            if is_other:
                conv.previous_state = "COLLECT_REQUIREMENT"
                conv.state = "COLLECT_CUSTOM_REQUIREMENT"
                await db.commit()

                await BaseHandler.send_and_log_text(
                    db=db, conv=conv, to=phone,
                    text=(
                        "📋 *Custom Requirement:*\n\n"
                        "Please describe your specific requirements or features needed below:"
                    )
                )
                return

            chosen_requirement = None
            for opt in req_options:
                if sel == opt["id"] or sel_lower == opt["title"].lower():
                    chosen_requirement = opt["title"]
                    break

            if not chosen_requirement and not input_clean.isdigit():
                for opt in req_options:
                    if opt["title"].lower() in sel_lower or sel_lower in opt["title"].lower():
                        chosen_requirement = opt["title"]
                        break

            # Fallback for free-form text input
            if not chosen_requirement:
                chosen_requirement = input_clean

            session_data["requirement"] = chosen_requirement
            conv.session_data = session_data
            conv.previous_state = "COLLECT_REQUIREMENT"
            conv.state = "COLLECT_TIMELINE"
            await db.commit()

            await BaseHandler.send_and_log_timeline(db=db, conv=conv, to=phone)
            return

        # ----------------------------------------------------
        # Step 3b: COLLECT_CUSTOM_REQUIREMENT (When "Other" was clicked)
        # ----------------------------------------------------
        elif state == "COLLECT_CUSTOM_REQUIREMENT":
            if not input_clean:
                await BaseHandler.send_and_log_text(
                    db=db, conv=conv, to=phone,
                    text="📋 *Custom Requirement:*\n\nPlease describe your specific requirements or features needed below:"
                )
                return

            session_data["requirement"] = input_clean
            conv.session_data = session_data
            conv.previous_state = "COLLECT_CUSTOM_REQUIREMENT"
            conv.state = "COLLECT_TIMELINE"
            await db.commit()

            await BaseHandler.send_and_log_timeline(db=db, conv=conv, to=phone)
            return

        # ----------------------------------------------------
        # Step 4: COLLECT_TIMELINE
        # ----------------------------------------------------
        elif state == "COLLECT_TIMELINE":
            sel = (selection_id or input_clean).strip()
            sel_lower = sel.lower()

            is_other = (
                sel_lower in ["time_other", "other", "custom", "other / custom", "others"]
                or sel_lower.startswith("other")
            )
            if input_clean.isdigit():
                idx = int(input_clean)
                if 1 <= idx <= len(TIMELINE_OPTIONS):
                    matched_opt = TIMELINE_OPTIONS[idx - 1]
                    if matched_opt["id"] == "time_other":
                        is_other = True
                    else:
                        sel = matched_opt["title"]
                        sel_lower = sel.lower()

            if is_other:
                conv.previous_state = "COLLECT_TIMELINE"
                conv.state = "COLLECT_CUSTOM_TIMELINE"
                await db.commit()

                await BaseHandler.send_and_log_text(
                    db=db, conv=conv, to=phone,
                    text=(
                        "⏱️ *Custom Project Timeline:*\n\n"
                        "Please describe your expected timeframe or target launch date below:"
                    )
                )
                return

            chosen_timeline = None
            for opt in TIMELINE_OPTIONS:
                if sel == opt["id"] or sel_lower == opt["title"].lower():
                    chosen_timeline = opt["title"]
                    break

            if not chosen_timeline and not input_clean.isdigit():
                for opt in TIMELINE_OPTIONS:
                    if opt["title"].lower() in sel_lower or sel_lower in opt["title"].lower():
                        chosen_timeline = opt["title"]
                        break

            if not chosen_timeline:
                chosen_timeline = input_clean

            session_data["timeline"] = chosen_timeline
            conv.session_data = session_data
            conv.previous_state = "COLLECT_TIMELINE"
            conv.state = "COLLECT_BUDGET"
            await db.commit()

            await BaseHandler.send_and_log_budget(db=db, conv=conv, to=phone)
            return

        # ----------------------------------------------------
        # Step 4b: COLLECT_CUSTOM_TIMELINE
        # ----------------------------------------------------
        elif state == "COLLECT_CUSTOM_TIMELINE":
            if not input_clean:
                await BaseHandler.send_and_log_text(
                    db=db, conv=conv, to=phone,
                    text="⏱️ *Custom Project Timeline:*\n\nPlease specify your expected launch timeframe below:"
                )
                return

            session_data["timeline"] = input_clean
            conv.session_data = session_data
            conv.previous_state = "COLLECT_CUSTOM_TIMELINE"
            conv.state = "COLLECT_BUDGET"
            await db.commit()

            await BaseHandler.send_and_log_budget(db=db, conv=conv, to=phone)
            return

        # ----------------------------------------------------
        # Step 5: COLLECT_BUDGET
        # ----------------------------------------------------
        elif state == "COLLECT_BUDGET":
            sel = (selection_id or input_clean).strip()
            sel_lower = sel.lower()

            is_other = (
                sel_lower in ["budget_other", "other", "custom", "other / custom", "others"]
                or sel_lower.startswith("other")
            )
            if input_clean.isdigit():
                idx = int(input_clean)
                if 1 <= idx <= len(BUDGET_OPTIONS):
                    matched_opt = BUDGET_OPTIONS[idx - 1]
                    if matched_opt["id"] == "budget_other":
                        is_other = True
                    else:
                        sel = matched_opt["title"]
                        sel_lower = sel.lower()

            if is_other:
                conv.previous_state = "COLLECT_BUDGET"
                conv.state = "COLLECT_CUSTOM_BUDGET"
                await db.commit()

                await BaseHandler.send_and_log_text(
                    db=db, conv=conv, to=phone,
                    text=(
                        "💰 *Custom Budget:*\n\n"
                        "Please specify your approximate planned budget range below:"
                    )
                )
                return

            chosen_budget = None
            for opt in BUDGET_OPTIONS:
                if sel == opt["id"] or sel_lower == opt["title"].lower():
                    chosen_budget = opt["title"]
                    break

            if not chosen_budget and not input_clean.isdigit():
                for opt in BUDGET_OPTIONS:
                    if opt["title"].lower() in sel_lower or sel_lower in opt["title"].lower():
                        chosen_budget = opt["title"]
                        break

            if not chosen_budget:
                chosen_budget = input_clean

            session_data["budget"] = chosen_budget
            conv.session_data = session_data
            conv.previous_state = "COLLECT_BUDGET"
            conv.state = "COLLECT_EMAIL"
            await db.commit()

            msg_text = (
                "📧 *Step 6 of 8: Email Address*\n\n"
                "Please enter your email address so we can forward you the formal quotation & technical scope.\n\n"
                "_(Type your email below, or type *skip* if you prefer phone communication only)_"
            )
            await BaseHandler.send_and_log_text(db=db, conv=conv, to=phone, text=msg_text)
            return

        # ----------------------------------------------------
        # Step 5b: COLLECT_CUSTOM_BUDGET
        # ----------------------------------------------------
        elif state == "COLLECT_CUSTOM_BUDGET":
            if not input_clean:
                await BaseHandler.send_and_log_text(
                    db=db, conv=conv, to=phone,
                    text="💰 *Custom Budget:*\n\nPlease specify your planned budget below:"
                )
                return

            session_data["budget"] = input_clean
            conv.session_data = session_data
            conv.previous_state = "COLLECT_CUSTOM_BUDGET"
            conv.state = "COLLECT_EMAIL"
            await db.commit()

            msg_text = (
                "📧 *Step 6 of 8: Email Address*\n\n"
                "Please enter your email address so we can forward you the formal quotation & technical scope.\n\n"
                "_(Type your email below, or type *skip* if you prefer phone communication only)_"
            )
            await BaseHandler.send_and_log_text(db=db, conv=conv, to=phone, text=msg_text)
            return

        # ----------------------------------------------------
        # Step 6: COLLECT_EMAIL
        # ----------------------------------------------------
        elif state == "COLLECT_EMAIL":
            if input_lower == "skip":
                session_data["email"] = "Not provided (Skipped)"
            else:
                email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", input_clean)
                if not email_match:
                    await BaseHandler.send_and_log_text(
                        db=db, conv=conv, to=phone,
                        text="⚠️ Please enter a valid email address (e.g., name@company.com) or type *skip*:"
                    )
                    return
                session_data["email"] = email_match.group(0).lower()

            conv.session_data = session_data
            conv.previous_state = "COLLECT_EMAIL"
            conv.state = "COLLECT_PREFERRED_TIME"
            await db.commit()

            await BaseHandler.send_and_log_preferred_time(db=db, conv=conv, to=phone)
            return

        # ----------------------------------------------------
        # Step 7: COLLECT_PREFERRED_TIME
        # ----------------------------------------------------
        elif state == "COLLECT_PREFERRED_TIME":
            sel = (selection_id or input_clean).strip()
            sel_lower = sel.lower()

            is_other = (
                sel_lower in ["slot_other", "other", "custom", "other / custom", "others"]
                or sel_lower.startswith("other")
            )
            if input_clean.isdigit():
                idx = int(input_clean)
                if 1 <= idx <= len(PREFERRED_TIME_OPTIONS):
                    matched_opt = PREFERRED_TIME_OPTIONS[idx - 1]
                    if matched_opt["id"] == "slot_other":
                        is_other = True
                    else:
                        sel = matched_opt["title"]
                        sel_lower = sel.lower()

            if is_other:
                conv.previous_state = "COLLECT_PREFERRED_TIME"
                conv.state = "COLLECT_CUSTOM_PREFERRED_TIME"
                await db.commit()

                await BaseHandler.send_and_log_text(
                    db=db, conv=conv, to=phone,
                    text=(
                        "🕒 *Custom Preferred Time:*\n\n"
                        "Please specify what day or time works best for you (e.g., 'Tomorrow at 11 AM'):"
                    )
                )
                return

            chosen_time = None
            for opt in PREFERRED_TIME_OPTIONS:
                if sel == opt["id"] or sel_lower == opt["title"].lower():
                    chosen_time = opt["title"]
                    break

            if not chosen_time and not input_clean.isdigit():
                for opt in PREFERRED_TIME_OPTIONS:
                    if opt["title"].lower() in sel_lower or sel_lower in opt["title"].lower():
                        chosen_time = opt["title"]
                        break

            if not chosen_time:
                chosen_time = input_clean

            session_data["preferred_contact_time"] = chosen_time
            conv.session_data = session_data
            conv.previous_state = "COLLECT_PREFERRED_TIME"
            conv.state = "COLLECT_CONTACT"
            await db.commit()

            msg_text = (
                f"📞 *Step 8 of 8: Contact Phone Number*\n\n"
                f"We currently have *{phone}* as your WhatsApp contact.\n\n"
                f"If you'd like our technical manager to call you on this same number, type *yes* or *ok*.\n"
                f"If you prefer a different phone number, type it below:"
            )
            await BaseHandler.send_and_log_text(db=db, conv=conv, to=phone, text=msg_text)
            return

        # ----------------------------------------------------
        # Step 7b: COLLECT_CUSTOM_PREFERRED_TIME
        # ----------------------------------------------------
        elif state == "COLLECT_CUSTOM_PREFERRED_TIME":
            if not input_clean:
                await BaseHandler.send_and_log_text(
                    db=db, conv=conv, to=phone,
                    text="🕒 *Custom Preferred Time:*\n\nPlease specify your preferred discussion time below:"
                )
                return

            session_data["preferred_contact_time"] = input_clean
            conv.session_data = session_data
            conv.previous_state = "COLLECT_CUSTOM_PREFERRED_TIME"
            conv.state = "COLLECT_CONTACT"
            await db.commit()

            msg_text = (
                f"📞 *Step 8 of 8: Contact Phone Number*\n\n"
                f"We currently have *{phone}* as your WhatsApp contact.\n\n"
                f"If you'd like our technical manager to call you on this same number, type *yes* or *ok*.\n"
                f"If you prefer a different phone number, type it below:"
            )
            await BaseHandler.send_and_log_text(db=db, conv=conv, to=phone, text=msg_text)
            return

        # ----------------------------------------------------
        # Step 8: COLLECT_CONTACT
        # ----------------------------------------------------
        elif state == "COLLECT_CONTACT":
            if input_lower in ["yes", "y", "ok", "same", "current", "this"]:
                session_data["phone"] = phone
            else:
                if any(char.isalpha() for char in input_clean):
                    await BaseHandler.send_and_log_text(
                        db=db, conv=conv, to=phone,
                        text="⚠️ Mobile number must not contain any words or letters. Please enter numbers only (e.g. 9876543210) or type *yes* to keep current number:"
                    )
                    return

                digits = re.sub(r"\D", "", input_clean)
                if len(digits) < 10:
                    await BaseHandler.send_and_log_text(
                        db=db, conv=conv, to=phone,
                        text="⚠️ Please enter a valid 10-digit mobile number (e.g. 9876543210) or type *yes* to keep current number:"
                    )
                    return
                session_data["phone"] = digits

            conv.session_data = session_data
            conv.previous_state = "COLLECT_CONTACT"
            conv.state = "LEAD_CONFIRMATION"
            await db.commit()

            # Present interactive requirement review card with instant quote estimate
            await BaseHandler.send_and_log_confirmation_card(db=db, conv=conv, to=phone, session_data=session_data)
            return

        # ----------------------------------------------------
        # Step 9: LEAD_CONFIRMATION
        # ----------------------------------------------------
        elif state == "LEAD_CONFIRMATION":
            sel = (selection_id or input_lower).strip()

            if sel in ["btn_confirm_lead", "confirm", "yes", "1", "submit", "confirm & submit ✅"]:
                lead = await lead_service.create_lead_from_conversation(db, conv, user)

                # Generate live dummy quotation estimate
                est = calculate_dummy_estimate(
                    service_name=session_data.get("service_name", "Software Solution"),
                    budget=session_data.get("budget"),
                    timeline=session_data.get("timeline")
                )

                # Send WhatsApp thanking reply to user immediately for instant response
                summary_msg = (
                    "🎉 *Requirement Successfully Submitted!* 🚀\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    f"Dear *{lead.name}*,\n\n"
                    f"Thank you for contacting *{settings.COMPANY_NAME}*! Our technical team has received your project requirements.\n\n"
                    f"👤 *Assigned Consultant:* Senior Technical Lead\n"
                    f"📞 *Consultant Phone:* {settings.COMPANY_PHONE}\n"
                    f"🕒 *Callback Scheduled:* {session_data.get('preferred_contact_time', 'Next business slot')}\n\n"
                    "🙏 *Thank you for choosing iZone Technologies! We will be in touch with you shortly.* 🚀\n\n"
                    "💡 _Type *menu* at any time to return to the main menu._"
                )
                await BaseHandler.send_and_log_text(db=db, conv=conv, to=phone, text=summary_msg)

                # Send internal notification email in the background without blocking the user reply
                asyncio.create_task(
                    email_service.send_lead_notification(
                        lead=lead,
                        to_email=settings.NOTIFICATION_EMAIL,
                        estimated_amount=est.get("estimated_range")
                    )
                )

                conv.session_data = {}
                conv.state = "MAIN_MENU"
                conv.status = "ACTIVE"
                await db.commit()
                return

            elif sel in ["btn_edit_lead", "edit", "2", "edit ✏️"]:
                conv.state = "COLLECT_NAME"
                await db.commit()
                await BaseHandler.send_and_log_text(
                    db=db, conv=conv, to=phone,
                    text="✏️ *Editing details:*\n\n*Step 1 of 8:* What is your full name?"
                )
                return

            elif sel in ["btn_cancel_lead", "cancel", "3", "cancel ❌"]:
                conv.session_data = {}
                conv.state = "MAIN_MENU"
                await db.commit()
                await BaseHandler.send_and_log_text(
                    db=db, conv=conv, to=phone,
                    text="❌ Requirement submission cancelled. Returning to main menu."
                )
                await BaseHandler.send_and_log_main_menu(db=db, conv=conv, to=phone, user_name=user.name)
                return

            else:
                await BaseHandler.send_and_log_confirmation_card(db=db, conv=conv, to=phone, session_data=session_data)
