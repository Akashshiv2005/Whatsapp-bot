import asyncio
from sqlalchemy import delete
from app.core.database import AsyncSessionLocal
from app.models import MenuOption

async def seed_menus():
    async with AsyncSessionLocal() as db:
        # We will delete all existing MenuOptions and re-create them properly
        await db.execute(delete(MenuOption))
        
        menus = [
            # 1. CORE_SERVICES_MENU (6 items)
            MenuOption(parent_state="CORE_SERVICES_MENU", value="menu_website", label="Web Development", sort_order=1, active=True, next_state="COLLECT_NAME"),
            MenuOption(parent_state="CORE_SERVICES_MENU", value="menu_software", label="Software Development", sort_order=2, active=True, next_state="COLLECT_NAME"),
            MenuOption(parent_state="CORE_SERVICES_MENU", value="menu_mobile", label="Mobile App Development", sort_order=3, active=True, next_state="COLLECT_NAME"),
            MenuOption(parent_state="CORE_SERVICES_MENU", value="menu_marketing", label="SEO & Digital Marketing", sort_order=4, active=True, next_state="COLLECT_NAME"),
            MenuOption(parent_state="CORE_SERVICES_MENU", value="menu_communication", label="WhatsApp & SMS APIs", sort_order=5, active=True, next_state="COLLECT_NAME"),
            MenuOption(parent_state="CORE_SERVICES_MENU", value="menu_student", label="Student Services", sort_order=6, active=True, next_state="COLLECT_NAME"),

            # 2. ERP_MENU_1 (Page 1) (9 items)
            MenuOption(parent_state="ERP_MENU_1", value="software_hms", label="Hospital Management HMS", sort_order=1, active=True, next_state="COLLECT_NAME"),
            MenuOption(parent_state="ERP_MENU_1", value="software_lms", label="Learning Management LMS", sort_order=2, active=True, next_state="COLLECT_NAME"),
            MenuOption(parent_state="ERP_MENU_1", value="software_tms", label="Transport Management TMS", sort_order=3, active=True, next_state="COLLECT_NAME"),
            MenuOption(parent_state="ERP_MENU_1", value="software_mms", label="Manufacturing MMS", sort_order=4, active=True, next_state="COLLECT_NAME"),
            MenuOption(parent_state="ERP_MENU_1", value="software_fms", label="Financial Management FMS", sort_order=5, active=True, next_state="COLLECT_NAME"),
            MenuOption(parent_state="ERP_MENU_1", value="software_pms", label="Project Management PMS", sort_order=6, active=True, next_state="COLLECT_NAME"),
            MenuOption(parent_state="ERP_MENU_1", value="software_ams", label="Asset Management AMS", sort_order=7, active=True, next_state="COLLECT_NAME"),
            MenuOption(parent_state="ERP_MENU_1", value="software_oms", label="Order Management OMS", sort_order=8, active=True, next_state="COLLECT_NAME"),
            MenuOption(parent_state="ERP_MENU_1", value="nav_erp_page_2", label="Next Page ➡️", sort_order=9, active=True, next_state="ERP_MENU_2"),

            # 3. ERP_MENU_2 (Page 2) (4 items)
            MenuOption(parent_state="ERP_MENU_2", value="software_wms", label="Warehouse Management WMS", sort_order=1, active=True, next_state="COLLECT_NAME"),
            MenuOption(parent_state="ERP_MENU_2", value="software_sms", label="School Management SMS", sort_order=2, active=True, next_state="COLLECT_NAME"),
            MenuOption(parent_state="ERP_MENU_2", value="software_bms", label="Business Management BMS", sort_order=3, active=True, next_state="COLLECT_NAME"),
            MenuOption(parent_state="ERP_MENU_2", value="nav_erp_page_1", label="⬅️ Previous Page", sort_order=4, active=True, next_state="ERP_MENU_1"),

            # 4. SOFTWARE_MENU (7 items)
            MenuOption(parent_state="SOFTWARE_MENU", value="software_billing", label="Billing Software", sort_order=1, active=True, next_state="COLLECT_NAME"),
            MenuOption(parent_state="SOFTWARE_MENU", value="software_crm", label="CRM Software", sort_order=2, active=True, next_state="COLLECT_NAME"),
            MenuOption(parent_state="SOFTWARE_MENU", value="software_erp", label="ERP Software", sort_order=3, active=True, next_state="COLLECT_NAME"),
            MenuOption(parent_state="SOFTWARE_MENU", value="software_payroll", label="Payroll Software", sort_order=4, active=True, next_state="COLLECT_NAME"),
            MenuOption(parent_state="SOFTWARE_MENU", value="software_custom", label="Custom Software", sort_order=5, active=True, next_state="COLLECT_NAME"),
            MenuOption(parent_state="SOFTWARE_MENU", value="software_student", label="Student Projects", sort_order=6, active=True, next_state="COLLECT_NAME"),
            MenuOption(parent_state="SOFTWARE_MENU", value="software_chitfund", label="Chit Fund Management", sort_order=7, active=True, next_state="COLLECT_NAME"),

            # 5. WEBSITE_MENU (5 items)
            MenuOption(parent_state="WEBSITE_MENU", value="website_business", label="Business Website", sort_order=1, active=True, next_state="COLLECT_NAME"),
            MenuOption(parent_state="WEBSITE_MENU", value="website_ecommerce", label="E-Commerce Website", sort_order=2, active=True, next_state="COLLECT_NAME"),
            MenuOption(parent_state="WEBSITE_MENU", value="website_cms", label="CMS Website", sort_order=3, active=True, next_state="COLLECT_NAME"),
            MenuOption(parent_state="WEBSITE_MENU", value="website_custom", label="Custom Web Application", sort_order=4, active=True, next_state="COLLECT_NAME"),
            MenuOption(parent_state="WEBSITE_MENU", value="website_redesign", label="Website Redesign", sort_order=5, active=True, next_state="COLLECT_NAME"),

            # 6. MOBILE_MENU (6 items)
            MenuOption(parent_state="MOBILE_MENU", value="mobile_android", label="Android App", sort_order=1, active=True, next_state="COLLECT_NAME"),
            MenuOption(parent_state="MOBILE_MENU", value="mobile_ios", label="iOS App", sort_order=2, active=True, next_state="COLLECT_NAME"),
            MenuOption(parent_state="MOBILE_MENU", value="mobile_ecommerce", label="E-Commerce App", sort_order=3, active=True, next_state="COLLECT_NAME"),
            MenuOption(parent_state="MOBILE_MENU", value="mobile_crm", label="CRM App", sort_order=4, active=True, next_state="COLLECT_NAME"),
            MenuOption(parent_state="MOBILE_MENU", value="mobile_flutter", label="Flutter App", sort_order=5, active=True, next_state="COLLECT_NAME"),
            MenuOption(parent_state="MOBILE_MENU", value="mobile_custom", label="Custom Mobile App", sort_order=6, active=True, next_state="COLLECT_NAME"),

            # 7. MARKETING_MENU (8 items)
            MenuOption(parent_state="MARKETING_MENU", value="marketing_technical_seo", label="Technical SEO", sort_order=1, active=True, next_state="COLLECT_NAME"),
            MenuOption(parent_state="MARKETING_MENU", value="marketing_google_ads", label="Google Ads (PPC)", sort_order=2, active=True, next_state="COLLECT_NAME"),
            MenuOption(parent_state="MARKETING_MENU", value="marketing_social_media", label="Social Media Marketing", sort_order=3, active=True, next_state="COLLECT_NAME"),
            MenuOption(parent_state="MARKETING_MENU", value="marketing_lead_gen", label="Lead Generation", sort_order=4, active=True, next_state="COLLECT_NAME"),
            MenuOption(parent_state="MARKETING_MENU", value="marketing_seo_audit", label="SEO Audit", sort_order=5, active=True, next_state="COLLECT_NAME"),
            MenuOption(parent_state="MARKETING_MENU", value="marketing_seo", label="Google SEO", sort_order=6, active=True, next_state="COLLECT_NAME"),
            MenuOption(parent_state="MARKETING_MENU", value="marketing_local_seo", label="Local SEO & Maps", sort_order=7, active=True, next_state="COLLECT_NAME"),
            MenuOption(parent_state="MARKETING_MENU", value="marketing_meta_ads", label="Meta Ads (FB & Insta)", sort_order=8, active=True, next_state="COLLECT_NAME"),

            # 8. COMMUNICATION_MENU (5 items)
            MenuOption(parent_state="COMMUNICATION_MENU", value="comm_whatsapp_api", label="WhatsApp Cloud API", sort_order=1, active=True, next_state="COLLECT_NAME"),
            MenuOption(parent_state="COMMUNICATION_MENU", value="comm_whatsapp_marketing", label="WhatsApp Marketing", sort_order=2, active=True, next_state="COLLECT_NAME"),
            MenuOption(parent_state="COMMUNICATION_MENU", value="comm_sms", label="Bulk SMS & SMS API", sort_order=3, active=True, next_state="COLLECT_NAME"),
            MenuOption(parent_state="COMMUNICATION_MENU", value="comm_voice", label="Bulk Voice & Voice API", sort_order=4, active=True, next_state="COLLECT_NAME"),
            MenuOption(parent_state="COMMUNICATION_MENU", value="comm_whatsapp_bot", label="WhatsApp Chatbot", sort_order=5, active=True, next_state="COLLECT_NAME"),

            # 9. STUDENT_MENU (5 items)
            MenuOption(parent_state="STUDENT_MENU", value="student_project", label="Final Year Project", sort_order=1, active=True, next_state="COLLECT_NAME"),
            MenuOption(parent_state="STUDENT_MENU", value="student_guidance", label="Project Guidance", sort_order=2, active=True, next_state="COLLECT_NAME"),
            MenuOption(parent_state="STUDENT_MENU", value="student_training", label="Technical Training", sort_order=3, active=True, next_state="COLLECT_NAME"),
            MenuOption(parent_state="STUDENT_MENU", value="student_internship", label="Internship Program", sort_order=4, active=True, next_state="COLLECT_NAME"),
            MenuOption(parent_state="STUDENT_MENU", value="student_career", label="Career Guidance", sort_order=5, active=True, next_state="COLLECT_NAME"),
        ]
        
        db.add_all(menus)
        await db.commit()
        print("MenuOptions cleared and reseeded successfully!")

if __name__ == "__main__":
    asyncio.run(seed_menus())
