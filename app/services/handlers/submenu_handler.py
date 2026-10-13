"""Handler for submenus (Website, Software, Mobile, Marketing, Communication, ERP)."""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, Conversation
from app.services.workflow_engine import workflow_engine, get_workflow_description
from app.services.faq_service import faq_service
from app.services.handlers.base_handler import BaseHandler


class SubmenuHandler:
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

        # Universal Back / Main Menu navigation from any submenu
        if (
            input_lower in [
                "back", "b", "nav_main_menu", "menu", "main menu", "home",
                "main menu 🏠", "🏠 main menu", "return to main menu"
            ]
            or sel in ["nav_main_menu", "menu", "main menu"]
        ):
            await BaseHandler.transition_to_main_menu(db, user, conv)
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
                await BaseHandler.send_and_log_submenu(
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
                for code, keyword in [
                    ("hms", "hospital"), ("lms", "learning"), ("tms", "transport"),
                    ("mms", "manufacturing"), ("fms", "financial"), ("pms", "project"),
                    ("ams", "asset"), ("oms", "order"), ("wms", "warehouse"),
                    ("sms", "school"), ("bms", "business")
                ]:
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

                await BaseHandler.log_message(
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
            await BaseHandler.send_and_log_text(db=db, conv=conv, to=phone, text=msg_text)
            return

        faq = await faq_service.match_faq(db, raw_input)
        if faq:
            await BaseHandler.send_and_log_text(
                db=db, conv=conv, to=phone,
                text=f"💡 *Information:*\n{faq.answer}\n\nType *back* for previous menu or *menu* for main menu."
            )
            return

        await BaseHandler.send_and_log_text(
            db=db, conv=conv, to=phone,
            text="⚠️ Invalid selection. Please choose one of the available options or type *menu*."
        )
        await BaseHandler.send_and_log_submenu(
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
        input_clean = raw_input.strip()
        if (
            input_clean.lower() in [
                "back", "b", "nav_main_menu", "menu", "main menu", "home",
                "main menu 🏠", "🏠 main menu"
            ]
            or selection_id in ["nav_main_menu", "menu"]
        ):
            await BaseHandler.transition_to_main_menu(db, user, conv)
            return

        conv.state = "COLLECT_NAME"
        await db.commit()
        await BaseHandler.send_and_log_text(
            db=db, conv=conv, to=user.phone_number,
            text="Let's collect your requirement details.\n\n*Step 1 of 8:* What is your full name?"
        )
