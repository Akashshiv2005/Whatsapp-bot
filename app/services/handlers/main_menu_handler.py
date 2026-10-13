"""Handler for MAIN_MENU routing and top-level user inputs."""
from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, Conversation, Service, MenuOption
from app.services.workflow_engine import workflow_engine, get_workflow_description
from app.services.faq_service import faq_service
from app.services.handlers.base_handler import BaseHandler, settings


class MainMenuHandler:
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

            "6": ("ERP_MENU_1", "menu_erp"),
            "erp": ("ERP_MENU_1", "menu_erp"),
            "management systems": ("ERP_MENU_1", "menu_erp"),
            "more erp systems": ("ERP_MENU_1", "menu_erp"),
            "menu_erp": ("ERP_MENU_1", "menu_erp"),

            "7": ("CONTACT_MENU", "menu_contact"),
            "8": ("CONTACT_MENU", "menu_contact"),
            "help": ("CONTACT_MENU", "menu_contact"),
            "support": ("CONTACT_MENU", "menu_contact"),
            "help & support": ("CONTACT_MENU", "menu_contact"),
            "menu_help_support": ("CONTACT_MENU", "menu_contact"),
            "menu_contact": ("CONTACT_MENU", "menu_contact"),
            "contact": ("CONTACT_MENU", "menu_contact"),
            "contact info": ("CONTACT_MENU", "menu_contact"),
            "location": ("CONTACT_MENU", "menu_contact"),

            "other": ("COLLECT_NAME", "service_other"),
            "other / custom need": ("COLLECT_NAME", "service_other"),
            "service_other": ("COLLECT_NAME", "service_other"),
            "custom": ("COLLECT_NAME", "service_other"),
        }

        fallback_mapping = {
            "other": ("COLLECT_NAME", "service_other"),
            "service_other": ("COLLECT_NAME", "service_other"),
            "custom": ("COLLECT_NAME", "service_other"),
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
            res_opt = await db.execute(
                select(MenuOption).where(MenuOption.parent_state == "MAIN_MENU", MenuOption.sort_order == 7)
            )
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
                await BaseHandler.send_and_log_submenu(
                    db=db, conv=conv, to=phone, parent_state="CORE_SERVICES_MENU",
                    title="iZone Core Services",
                    description="Select a core service category:"
                )
            elif matched_state == "ERP_MENU_1":
                await BaseHandler.send_and_log_submenu(
                    db=db, conv=conv, to=phone, parent_state="ERP_MENU_1",
                    title="Management Systems",
                    description="Select an ERP system (Page 1):"
                )
            elif matched_state == "HELP_SUPPORT_MENU":
                await BaseHandler.send_and_log_submenu(
                    db=db, conv=conv, to=phone, parent_state="HELP_SUPPORT_MENU",
                    title="Help & Support",
                    description="How can we help you?"
                )
            elif matched_state == "WEBSITE_MENU":
                await BaseHandler.send_and_log_submenu(
                    db=db, conv=conv, to=phone, parent_state="WEBSITE_MENU",
                    title="Website Development",
                    description="Select a website service category to get started:"
                )
            elif matched_state == "SOFTWARE_MENU":
                await BaseHandler.send_and_log_submenu(
                    db=db, conv=conv, to=phone, parent_state="SOFTWARE_MENU",
                    title="Software Development",
                    description="Select a software solution category:"
                )
            elif matched_state == "MOBILE_MENU":
                await BaseHandler.send_and_log_submenu(
                    db=db, conv=conv, to=phone, parent_state="MOBILE_MENU",
                    title="Mobile App Development",
                    description="Select mobile app development service:"
                )
            elif matched_state == "MARKETING_MENU":
                await BaseHandler.send_and_log_submenu(
                    db=db, conv=conv, to=phone, parent_state="MARKETING_MENU",
                    title="SEO & Digital Marketing",
                    description="Choose your digital marketing growth channel:"
                )
            elif matched_state == "COMMUNICATION_MENU":
                await BaseHandler.send_and_log_submenu(
                    db=db, conv=conv, to=phone, parent_state="COMMUNICATION_MENU",
                    title="WhatsApp / SMS / Voice Services",
                    description="Select messaging or voice API solution:"
                )
            elif matched_state == "CONTACT_MENU":
                res = await workflow_engine.send_contact_info(to=phone)
                await BaseHandler.log_message(
                    db=db, conversation_id=conv.id, direction="OUTBOUND",
                    message_type="interactive_button",
                    text=f"Company Details for {settings.COMPANY_NAME}",
                    raw_payload=res
                )
            elif matched_state == "HUMAN_HANDOFF":
                await BaseHandler.transition_to_support(db, user, conv)
            elif matched_state == "COLLECT_NAME":
                session_data = dict(conv.session_data or {})
                session_data["service_name"] = "Other / Custom Need"
                session_data["parent_menu"] = "MAIN_MENU"
                conv.session_data = session_data
                await db.commit()

                msg_text = (
                    "Great! You selected *Other / Custom Need* 🚀\n\n"
                    "We'd love to learn about your unique requirements and build a customized solution for your business.\n\n"
                    "*Step 1 of 8:* What is your full name?"
                )
                await BaseHandler.send_and_log_text(db=db, conv=conv, to=phone, text=msg_text)
                return
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

                    await BaseHandler.log_message(
                        db=db, conversation_id=conv.id, direction="OUTBOUND",
                        message_type="interactive_button",
                        text=f"Product Overview for {service.name}",
                        raw_payload=res
                    )
            return

        # Check if the input/selection matches any service menu option directly
        search_val = target_val
        if search_val.lower() in ["hms", "lms", "tms", "mms", "fms", "pms", "ams", "oms", "wms", "sms", "bms"]:
            search_val = f"software_{search_val.lower()}"

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

                await BaseHandler.log_message(
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
            await BaseHandler.send_and_log_text(db=db, conv=conv, to=phone, text=msg_text)
            return

        faq = await faq_service.match_faq(db, raw_input)
        if faq:
            await BaseHandler.send_and_log_text(
                db=db, conv=conv, to=phone,
                text=f"💡 *Information:*\n{faq.answer}\n\nType *menu* to explore our services."
            )
            return

        await BaseHandler.send_and_log_text(
            db=db, conv=conv, to=phone,
            text="⚠️ Invalid selection. Please choose an option from the menu below."
        )
        await BaseHandler.send_and_log_main_menu(db=db, conv=conv, to=phone, user_name=user.name)
