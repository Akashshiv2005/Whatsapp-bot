"""Handler for product feature overview tours (HMS, LMS, etc.)."""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, Conversation
from app.services.workflow_engine import workflow_engine
from app.services.handlers.base_handler import BaseHandler


class ProductInfoHandler:
    @staticmethod
    async def handle_product_info_input(
        db: AsyncSession,
        user: User,
        conv: Conversation,
        raw_input: str,
        selection_id: Optional[str]
    ) -> None:
        """Process user input when viewing product info overview (HMS/LMS/ERP tours)."""
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

        sequences = {
            "hms": ["mod_hms_opd", "mod_hms_ipd", "mod_hms_pharmacy", "mod_hms_lab", "mod_hms_billing"],
            "lms": ["mod_lms_courses", "mod_lms_live", "mod_lms_exams", "mod_lms_portal", "mod_lms_analytics"],
            "tms": ["mod_tms_fleet", "mod_tms_dispatch", "mod_tms_gps", "mod_tms_fuel", "mod_tms_billing"],
            "mms": ["mod_mms_bom", "mod_mms_mrp", "mod_mms_workorder", "mod_mms_qc", "mod_mms_inventory"],
            "fms": ["mod_fms_ledger", "mod_fms_invoicing", "mod_fms_tax", "mod_fms_banking", "mod_fms_reports"],
            "pms": ["mod_pms_kanban", "mod_pms_gantt", "mod_pms_timesheets", "mod_pms_budget", "mod_pms_collaboration"],
            "ams": ["mod_ams_register", "mod_ams_tracking", "mod_ams_depreciation", "mod_ams_maintenance", "mod_ams_audit"],
            "oms": ["mod_oms_capture", "mod_oms_inventory", "mod_oms_fulfillment", "mod_oms_shipping", "mod_oms_returns"],
            "wms": ["mod_wms_receiving", "mod_wms_binning", "mod_wms_picking", "mod_wms_audit", "mod_wms_transfers"],
            "sms": ["mod_sms_admissions", "mod_sms_attendance", "mod_sms_fees", "mod_sms_exams", "mod_sms_parentportal"],
            "bms": ["mod_bms_crm", "mod_bms_finance", "mod_bms_operations", "mod_bms_hr", "mod_bms_bi"],
        }

        # 1. Check if user selected to proceed to Demo/Lead collection
        if sel in ["btn_start_demo", "demo", "request", "yes", "confirm", "start", "request quote & demo ✅"]:
            conv.previous_state = "PRODUCT_INFO"
            conv.state = "COLLECT_NAME"
            await db.commit()

            msg_text = (
                f"Great! Let's collect a few details so our technical team can prepare an accurate proposal and estimate for *{service_name}*.\n\n"
                "*Step 1 of 8:* What is your full name?"
            )
            await BaseHandler.send_and_log_text(db=db, conv=conv, to=phone, text=msg_text)
            return

        # 2. Check if user wants to go back to the Main Menu
        elif (
            sel in ["nav_main_menu", "menu", "back", "cancel", "no", "🏠 main menu", "🏠 return to main menu", "main menu 🏠"]
            or input_lower in ["nav_main_menu", "menu", "back", "cancel", "main menu", "home", "main menu 🏠", "🏠 main menu"]
        ):
            await BaseHandler.transition_to_main_menu(db, user, conv)
            return

        # 3. Check if user wants to view the modules list menu again
        elif sel in ["btn_explore_modules", "explore", "tour", "explore modules 📋", "modules"]:
            method = getattr(workflow_engine, f"send_{product_code}_tour_menu", None)
            if method:
                res = await method(to=phone)
            else:
                res = await workflow_engine.send_hms_tour_menu(to=phone)

            await BaseHandler.log_message(
                db=db, conversation_id=conv.id, direction="OUTBOUND",
                message_type="interactive_list",
                text=f"Explore Modules for {service_name}",
                raw_payload=res
            )
            return

        # 4. Check if user selected a specific module to describe
        elif product_code and product_code in sequences and sel in sequences[product_code]:
            res = await workflow_engine.send_module_description(phone, sel)
            await BaseHandler.log_message(
                db=db, conversation_id=conv.id, direction="OUTBOUND",
                message_type="interactive_button",
                text=f"Module details: {sel}",
                raw_payload=res
            )
            return

        # 5. Fallback
        else:
            method = getattr(workflow_engine, f"send_{product_code}_tour_menu", None)
            if method:
                res = await method(to=phone)
            else:
                res = await workflow_engine.send_hms_tour_menu(to=phone)

            await BaseHandler.log_message(
                db=db, conversation_id=conv.id, direction="OUTBOUND",
                message_type="interactive_list",
                text=f"Explore Modules for {service_name}",
                raw_payload=res
            )
