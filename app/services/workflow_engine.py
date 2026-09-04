from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.config import get_settings
from app.models import MenuOption, Service
from app.services.whatsapp import whatsapp_service
from app.core.logging import logger

settings = get_settings()

BUDGET_OPTIONS = [
    {"id": "budget_1", "title": "Below ₹25,000", "description": "Entry-level / starter project"},
    {"id": "budget_2", "title": "₹25,000 – ₹50,000", "description": "Standard business solution"},
    {"id": "budget_3", "title": "₹50,000 – ₹1,00,000", "description": "Advanced / custom application"},
    {"id": "budget_4", "title": "Above ₹1,00,000", "description": "Enterprise-grade solution"},
    {"id": "budget_5", "title": "Flexible / Not Decided", "description": "Discuss with tech consultant"},
]

TIMELINE_OPTIONS = [
    {"id": "time_urgent", "title": "Urgent (< 2 Weeks)", "description": "Fast-track priority delivery"},
    {"id": "time_standard", "title": "1 Month", "description": "Standard development cycle"},
    {"id": "time_extended", "title": "2–3 Months", "description": "Large multi-phase deployment"},
    {"id": "time_flexible", "title": "Flexible / Exploring", "description": "Early research & planning"},
]

PREFERRED_TIME_OPTIONS = [
    {"id": "slot_morning", "title": "Morning (10AM–1PM)", "description": "Business hours opening"},
    {"id": "slot_afternoon", "title": "Afternoon (2PM–5PM)", "description": "Mid-day discussion"},
    {"id": "slot_evening", "title": "Evening (5PM–7PM)", "description": "End-of-day consultation"},
    {"id": "slot_chat_only", "title": "WhatsApp Chat Only", "description": "Text messaging only"},
]

OPTION_METADATA: Dict[str, tuple] = {
    # 1. ERP Systems (Page 1)
    "software_hms": ("Hospital Management HMS", "OPD, IPD, Pharmacy, Lab & Billing"),
    "software_lms": ("Learning Management LMS", "Courses, Live Classes & Student Portal"),
    "software_tms": ("Transport Management TMS", "Fleet, Dispatch, GPS & Fuel Tracking"),
    "software_mms": ("Manufacturing MMS", "BOM, MRP, Work Orders & Quality Control"),
    "software_fms": ("Financial Management FMS", "Ledger, Invoicing, GST & Financial Reports"),
    "software_pms": ("Project Management PMS", "Gantt, Kanban Tasks & Timesheets"),
    "software_ams": ("Asset Management AMS", "Asset Registry, Tracking, Custody & Audit"),
    "software_oms": ("Order Management OMS", "Order Capture, Inventory & Shipping"),
    "nav_erp_page_2": ("Next Page ➡️", "View WMS, SMS, BMS & More Systems"),

    # 2. ERP Systems (Page 2)
    "software_wms": ("Warehouse Management WMS", "Receiving, Bins, Picking & Stock"),
    "software_sms": ("School Management SMS", "Admissions, Attendance, Fees & Exams"),
    "software_bms": ("Business Management BMS", "All-in-One Enterprise ERP & Analytics"),
    "nav_erp_page_1": ("⬅️ Previous Page", "Return to Page 1 Management Systems"),

    # 3. Software Development
    "software_billing": ("Billing Software", "GST Invoicing, POS & Inventory"),
    "software_crm": ("CRM Software", "Leads, Sales Pipeline & Support Tickets"),
    "software_erp": ("ERP Software", "Integrated Operations, Finance & HR"),
    "software_payroll": ("Payroll Software", "Salary Slips, Attendance & PF/ESI"),
    "software_custom": ("Custom Software", "Tailor-made Business Automation"),
    "software_student": ("Student Projects", "Academic Projects, Code & Guidance"),
    "software_chitfund": ("Chit Fund Management", "Subscribers, Auctions, Dividends & Ledger"),

    # 4. Website Development
    "website_business": ("Business Website", "Fast, Responsive Corporate Presence"),
    "website_ecommerce": ("E-Commerce Website", "Online Store, Catalog & Payment Gateways"),
    "website_cms": ("CMS Website", "WordPress & Easy Content Management"),
    "website_custom": ("Custom Web App", "Full-Stack Web Application Solutions"),
    "website_redesign": ("Website Redesign", "Modern UI/UX Revamp & Speed Boost"),

    # 5. Mobile App Development
    "mobile_android": ("Android App", "Native Java/Kotlin High-Performance Apps"),
    "mobile_ios": ("iOS App", "Native Swift iPhone & iPad Applications"),
    "mobile_ecommerce": ("E-Commerce App", "Shopping, Cart & Razorpay/Stripe Checkout"),
    "mobile_crm": ("CRM App", "Sales Force Mobility & Instant Alerts"),
    "mobile_flutter": ("Flutter App", "Cross-Platform Android & iOS Solution"),
    "mobile_custom": ("Custom Mobile App", "Tailored Mobile Architecture & Features"),

    # 6. SEO & Digital Marketing
    "marketing_technical_seo": ("Technical SEO", "Speed, Core Web Vitals & Indexing"),
    "marketing_google_ads": ("Google Ads (PPC)", "High-ROI Search & Display Ads"),
    "marketing_social_media": ("Social Media Marketing", "Instagram, LinkedIn & Facebook Growth"),
    "marketing_lead_gen": ("Lead Generation", "Qualified Inquiries & Conversion Funnels"),
    "marketing_seo_audit": ("SEO Audit", "Complete 100-Point Website Health Check"),
    "marketing_seo": ("Google SEO", "Keyword Ranking & Organic Traffic"),
    "marketing_local_seo": ("Local SEO & Maps", "Google Maps & Local Search Ranking"),
    "marketing_meta_ads": ("Meta Ads", "Facebook & Instagram Targeted Funnels"),

    # 7. WhatsApp & SMS APIs
    "comm_whatsapp_api": ("WhatsApp Cloud API", "Official Meta Cloud API & Green Badge"),
    "comm_whatsapp_marketing": ("WhatsApp Marketing", "Bulk Broadcasts & Promotional Campaigns"),
    "comm_sms": ("Bulk SMS & SMS API", "Transactional DLT SMS & Promotions"),
    "comm_voice": ("Bulk Voice & Voice API", "Automated Voice Broadcasts & IVR"),
    "comm_whatsapp_bot": ("WhatsApp Chatbot", "Interactive AI & Workflow Automation Bot"),

    # 8. Student Services
    "student_project": ("Final Year Project", "IEEE Source Code, Documentation & Viva"),
    "student_guidance": ("Project Guidance", "1-on-1 Mentorship & Architecture Review"),
    "student_training": ("Technical Training", "Python, Full-Stack, AI & Cloud Bootcamps"),
    "student_internship": ("Internship Program", "Hands-on Industry Project Experience"),
    "student_career": ("Career Guidance", "Resume Building & Mock Technical Interviews"),

    # 9. Core Services Menu
    "menu_website": ("Website Development", "Custom, E-Commerce, CMS & Redesign"),
    "menu_software": ("Software Development", "CRM, Billing, ERP & Custom Software"),
    "menu_mobile": ("Mobile App Development", "Android, iOS & Flutter Applications"),
    "menu_marketing": ("SEO & Digital Marketing", "Google Ads, Meta Ads & Search Ranking"),
    "menu_communication": ("WhatsApp & SMS APIs", "Official Meta Cloud APIs & Bulk Messaging"),
    "menu_student": ("Student Services", "Final Year Projects, Internships & Training"),
}


def calculate_dummy_estimate(service_name: str, budget: Optional[str] = None, timeline: Optional[str] = None) -> Dict[str, Any]:
    """Generates a realistic dummy quotation estimate and feature breakdown."""
    s_lower = (service_name or "").lower()
    
    if "hms" in s_lower or "hospital" in s_lower or "clinic" in s_lower or "doctor" in s_lower or "medical" in s_lower:
        base_range = "₹45,000 – ₹1,20,000"
        features = "OPD/IPD Registration, Doctor Schedules & Tokens, Pharmacy Inventory, Lab Diagnostic Reports, Electronic Health Records (EHR), Insurance TPA & GST Invoicing"
        delivery = "2–4 Weeks"
    elif "lms" in s_lower or "learning" in s_lower or "course" in s_lower or "academy" in s_lower or "coaching" in s_lower or "institute" in s_lower:
        base_range = "₹35,000 – ₹85,000"
        features = "Video Course Streaming, Live Zoom/Meet Classes, Quiz & Online Exam Engine, Automated Certificates, Razorpay Payment Gateway & Student Mobile App"
        delivery = "2–3 Weeks"
    elif "chitfund" in s_lower or "chit fund" in s_lower or "chit" in s_lower:
        base_range = "₹40,000 – ₹95,000"
        features = "Subscriber Registration, KYC Document Upload, Multi-Group Creation, Automated Auction & Bid Management, Dividend Calculations, SMS/WhatsApp Reminders & Subscriber Ledger"
        delivery = "3–4 Weeks"
    elif "ecommerce" in s_lower or "e-commerce" in s_lower or "shopping" in s_lower:
        base_range = "₹28,500 – ₹45,000"
        features = "Product Catalog, Razorpay/Stripe Gateway, Cart & Checkout, Admin Inventory Portal, SSL & 1 Year Cloud Hosting"
        delivery = "2–3 Weeks"
    elif "website" in s_lower or "web" in s_lower or "redesign" in s_lower or "wordpress" in s_lower:
        base_range = "₹16,000 – ₹28,000"
        features = "Mobile-Responsive UI/UX, High-Speed Loading, SEO Meta Setup, Contact Forms, WhatsApp Direct Connect"
        delivery = "7–14 Days"
    elif "crm" in s_lower or "erp" in s_lower or "billing" in s_lower or "software" in s_lower:
        base_range = "₹48,000 – ₹85,000"
        features = "Role-based Access Control, GST Invoice Generation, PostgreSQL Cloud Database, Automated Daily Backups"
        delivery = "3–5 Weeks"
    elif "mobile" in s_lower or "app" in s_lower or "android" in s_lower or "ios" in s_lower or "flutter" in s_lower:
        base_range = "₹52,000 – ₹95,000"
        features = "Cross-platform Android & iOS Apps, Real-time Push Notifications, REST APIs, Google Play Store Publishing"
        delivery = "4–6 Weeks"
    elif "marketing" in s_lower or "seo" in s_lower or "ads" in s_lower:
        base_range = "₹14,000 – ₹25,000 / month"
        features = "Top Keyword Ranking, On-Page & Off-Page SEO, Google Ads Setup, Social Media Creatives, Monthly KPI Analytics"
        delivery = "Monthly Retainer"
    elif "whatsapp" in s_lower or "sms" in s_lower or "voice" in s_lower:
        base_range = "₹8,500 – ₹18,000"
        features = "Official Meta Cloud API Setup, Verified Green Badge Guidance, Interactive Buttons/Lists, Multi-Agent Chat Panel"
        delivery = "3–5 Days"
    elif "student" in s_lower or "project" in s_lower or "internship" in s_lower:
        base_range = "₹7,500 – ₹14,000"
        features = "IEEE Base Paper, Complete Python/Java Source Code, PPT & Report Documentation, 1-on-1 Viva Preparation"
        delivery = "3–7 Days"
    else:
        base_range = "₹22,000 – ₹42,000"
        features = "Custom Tailored Architecture, Dedicated Project Manager, Cloud Deployment, 3 Months Free Maintenance Support"
        delivery = "2–4 Weeks"

    return {
        "estimated_range": base_range,
        "features_included": features,
        "delivery_time": delivery
    }


def get_workflow_description(service_name: str) -> Optional[str]:
    """Return a structured workflow description for key products."""
    s_lower = (service_name or "").lower()
    if "hms" in s_lower or "hospital" in s_lower:
        return (
            "*Product Workflow & Modules:*\n"
            "1. *Patient Admission* (OPD/IPD Registration & Bed Management)\n"
            "2. *Doctor Scheduling* (Appointments, Consultations & Token Display)\n"
            "3. *Lab & Diagnostics* (Lab Tests & Patient Diagnostic Reports)\n"
            "4. *Pharmacy Billing* (Medicine Inventory, Expiry Tracking & POS Billing)\n"
            "5. *Discharge & Invoicing* (TPA Insurance Claims & GST Compliant Billing)"
        )
    elif "lms" in s_lower or "learning" in s_lower:
        return (
            "*Product Workflow & Modules:*\n"
            "1. *Course Creation* (DRM-Protected Video Streaming & Syllabus Management)\n"
            "2. *Live Classes* (Google Meet / Zoom Integration & YouTube Live Streams)\n"
            "3. *Student Exam Engine* (Online Quizzes, MCQ Tests & Automated Grading)\n"
            "4. *Certificate Engine* (Automated Course Certificates with QR Verification)\n"
            "5. *Payment & Access* (Payment Gateway Integration & Automatic Student Enrollment)"
        )
    elif "chitfund" in s_lower or "chit fund" in s_lower:
        return (
            "*Product Workflow & Modules:*\n"
            "1. *Member Enrollment* (Subscriber Registration & KYC Document Upload)\n"
            "2. *Chit Group Setup* (Chit Value, Installment, Ticket Allocation & Commission Settings)\n"
            "3. *Auction Process* (Monthly Auction Bid Submission & Minimum Bid Calculations)\n"
            "4. *Dividend Ledger* (Dividend Calculations & Non-Bid Member Share Allocation)\n"
            "5. *Payment & Collection* (UPI Payment Gateway, Subscription Collection & Agent Commission Tracking)"
        )
    return None


class WorkflowEngine:
    @staticmethod
    async def get_menu_options(db: AsyncSession, parent_state: str) -> List[MenuOption]:
        """Fetch active menu options for a given parent state from DB with eager loaded services."""
        res = await db.execute(
            select(MenuOption)
            .where(MenuOption.parent_state == parent_state, MenuOption.active == True)
            .options(selectinload(MenuOption.service))
            .order_by(MenuOption.sort_order)
        )
        return list(res.scalars().all())

    @staticmethod
    async def send_main_menu(to: str, user_name: Optional[str] = None) -> Dict[str, Any]:
        """Send interactive main menu list with rich fallback text formatting."""
        greeting = f"Hello {user_name}! 👋" if user_name else "Welcome to *iZone Technologies*! 👋"
        body_text = (
            f"{greeting}\n\n"
            "We provide end-to-end software, web, mobile, digital marketing, and student solutions.\n\n"
            "🛠️ *Our Core Services:*\n"
            "• *Website Development* (Custom, E-Commerce, CMS)\n"
            "• *Software Development* (CRM, ERP, Billing, Custom)\n"
            "• *Mobile App Development* (Android, iOS, Flutter)\n"
            "• *SEO & Digital Marketing* (Google Ads, Meta Ads)\n"
            "• *WhatsApp & SMS APIs* (Official Meta APIs)\n"
            "• *Student Services & Projects* (Final Year Projects, Training)\n\n"
            "🚀 *Our Management Systems:*\n"
            "• *Hospital Management (HMS)*\n"
            "• *Learning Management (LMS)*\n"
            "• *Transport Management (TMS)*\n"
            "• *Manufacturing Management (MMS)*\n"
            "• *Financial Management (FMS)*\n"
            "• *Project Management (PMS)*\n"
            "• *Asset Management (AMS)*\n"
            "• *Order Management (OMS)*\n"
            "• *Warehouse Management (WMS)*\n"
            "• *School Management (SMS)*\n"
            "• *Business Management (BMS)*\n\n"
            "👤 *Help & Support:*\n"
            "• *Contact & Office Location*\n"
            "• *Talk to Human Support*\n\n"
            "👉 _Select an option from the menu list below:_"
        )

        sections = [
            {
                "title": "Our Services & Systems",
                "rows": [
                    {"id": "menu_website", "title": "Website Development", "description": "Custom, E-Commerce, CMS"},
                    {"id": "menu_software", "title": "Software Development", "description": "CRM, Billing, Custom Software"},
                    {"id": "menu_mobile", "title": "Mobile App Development", "description": "Android, iOS, Flutter"},
                    {"id": "menu_marketing", "title": "SEO & Digital Marketing", "description": "Google Ads, Meta Ads, SEO"},
                    {"id": "menu_communication", "title": "WhatsApp & SMS APIs", "description": "Official Meta APIs, Bulk SMS"},
                    {"id": "menu_student", "title": "Student Services", "description": "Final Year Projects, Training"},
                    {"id": "menu_erp", "title": "Management Systems", "description": "HMS, LMS, TMS, MMS, FMS & more"},
                    {"id": "menu_contact", "title": "Help & Support", "description": "Contact info, Office location, Support"},
                ]
            }
        ]

        return await whatsapp_service.send_interactive_list(
            to=to,
            body_text=body_text,
            button_label="Explore Options",
            sections=sections,
            header="iZone Technologies",
            footer="Select an option from the list",
        )

    @staticmethod
    async def send_submenu(
        to: str,
        db: AsyncSession,
        parent_state: str,
        title: str,
        description: str
    ) -> Dict[str, Any]:
        """Send dynamic database-driven submenu with clean structured formatting."""
        options = await WorkflowEngine.get_menu_options(db, parent_state)

        num_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        rows = []
        body_lines = [
            f"*{title}* 🚀",
            "━━━━━━━━━━━━━━━━━━━━",
            f"{description}\n"
        ]

        idx_count = 0
        for opt in options:
            meta = OPTION_METADATA.get(opt.value)
            if meta:
                display_label, desc = meta
            else:
                display_label = opt.label
                desc = opt.service.description if (opt.service and opt.service.description) else f"Explore {opt.label}"

            display_label = display_label[:24]
            desc = desc[:72]

            rows.append({
                "id": opt.value,
                "title": display_label,
                "description": desc
            })

            clean_title = display_label.replace("⬅️", "").replace("➡️", "").strip()
            if "previous" in opt.value.lower() or "prev" in opt.value.lower() or "previous" in display_label.lower() or "prev" in display_label.lower():
                body_lines.append(f"⬅️ *{clean_title}* — _{desc}_")
            elif "next" in opt.value.lower() or "page" in opt.value.lower():
                body_lines.append(f"➡️ *{clean_title}* — _{desc}_")
            else:
                icon = num_emojis[idx_count] if idx_count < len(num_emojis) else "•"
                body_lines.append(f"{icon} *{display_label}*\n   _{desc}_\n")
                idx_count += 1

        if len(rows) < 10:
            rows.append({"id": "nav_main_menu", "title": "Main Menu 🏠", "description": "Return to main menu"})

        body_lines.append("🏠 *Main Menu* (Type *menu* or *back*)")
        body_lines.append("\n👉 _Tap *Select Option* below to explore:_")

        body = "\n".join(body_lines)
        sections = [{"title": title[:24], "rows": rows}]

        return await whatsapp_service.send_interactive_list(
            to=to,
            body_text=body,
            button_label="Select Option",
            sections=sections,
            header="iZone Services",
            footer="Select an option or type 'menu'",
        )

    @staticmethod
    async def send_contact_info(to: str) -> Dict[str, Any]:
        """Send contact info with action buttons."""
        body = (
            f"🏢 *{settings.COMPANY_NAME}*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📍 *Location:*\n{settings.COMPANY_ADDRESS}\n\n"
            f"📞 *Phone:* {settings.COMPANY_PHONE}\n"
            f"✉️ *Email:* {settings.COMPANY_EMAIL}\n"
            f"🌐 *Website:* {settings.COMPANY_WEBSITE}\n"
            f"🕒 *Working Hours:* {settings.COMPANY_WORKING_HOURS}\n"
        )

        buttons = [
            {"id": "btn_send_location", "title": "📍 Send Map Pin"},
            {"id": "menu_support", "title": "👤 Talk to Support"},
            {"id": "nav_main_menu", "title": "🏠 Main Menu"},
        ]

        return await whatsapp_service.send_interactive_buttons(
            to=to,
            body_text=body,
            buttons=buttons,
            header="Contact Information",
            footer="Type 'map' or 'menu'",
        )

    @staticmethod
    async def send_location_pin(to: str) -> Dict[str, Any]:
        """Send Google Map pin."""
        return await whatsapp_service.send_location(
            to=to,
            latitude=settings.COMPANY_LOCATION_LATITUDE,
            longitude=settings.COMPANY_LOCATION_LONGITUDE,
            name=settings.COMPANY_NAME,
            address=settings.COMPANY_ADDRESS,
        )

    @staticmethod
    async def send_timeline_selection(to: str) -> Dict[str, Any]:
        """Send timeline selector (Step 4 of 8)."""
        body = (
            "⏳ *Step 4 of 8: Project Timeline*\n\n"
            "How soon would you like to start and launch this project?\n\n"
            "• *Urgent (< 2 Weeks)* - Fast-track priority delivery\n"
            "• *Standard (1 Month)* - Standard development cycle\n"
            "• *2–3 Months* - Large multi-phase deployment\n"
            "• *Flexible / Exploring* - Early research & planning\n\n"
            "👉 _Select an option below:_"
        )

        sections = [
            {
                "title": "Timeline Options",
                "rows": TIMELINE_OPTIONS
            }
        ]

        return await whatsapp_service.send_interactive_list(
            to=to,
            body_text=body,
            button_label="Choose Timeline",
            sections=sections,
            footer="Select an option above",
        )

    @staticmethod
    async def send_budget_selection(to: str) -> Dict[str, Any]:
        """Send budget range selector (Step 5 of 8)."""
        body = (
            "💰 *Step 5 of 8: Approximate Budget*\n\n"
            "What is your intended budget for this project?\n\n"
            "• *Below ₹25,000* - Entry-level / starter project\n"
            "• *₹25,000 – ₹50,000* - Standard business solution\n"
            "• *₹50,000 – ₹1,00,000* - Advanced / custom application\n"
            "• *Above ₹1,00,000* - Enterprise-grade solution\n"
            "• *Flexible / Not Decided* - Discuss with tech consultant\n\n"
            "👉 _Select an option below:_"
        )

        sections = [
            {
                "title": "Budget Ranges",
                "rows": BUDGET_OPTIONS
            }
        ]

        return await whatsapp_service.send_interactive_list(
            to=to,
            body_text=body,
            button_label="Select Budget",
            sections=sections,
            footer="Select an option above",
        )

    @staticmethod
    async def send_preferred_time_selection(to: str) -> Dict[str, Any]:
        """Send preferred calling slot selector (Step 7 of 8)."""
        body = (
            "🕒 *Step 7 of 8: Best Time to Connect*\n\n"
            "When is the most convenient time for our tech consultant to contact you?\n\n"
            "• *Morning (10:00 AM – 1:00 PM)*\n"
            "• *Afternoon (2:00 PM – 5:00 PM)*\n"
            "• *Evening (5:00 PM – 7:00 PM)*\n"
            "• *WhatsApp Chat Only*\n\n"
            "👉 _Select an option below:_"
        )

        sections = [
            {
                "title": "Available Slots",
                "rows": PREFERRED_TIME_OPTIONS
            }
        ]

        return await whatsapp_service.send_interactive_list(
            to=to,
            body_text=body,
            button_label="Select Time Slot",
            sections=sections,
            footer="Select an option above",
        )

    @staticmethod
    async def send_lead_confirmation_card(to: str, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send detailed requirement summary card with dynamic dummy estimate calculation and action buttons."""
        service_name = session_data.get("service_name", "Custom Solution")
        name = session_data.get("name", "N/A")
        business_type = session_data.get("business_type", "N/A")
        requirement = session_data.get("requirement", "N/A")
        timeline = session_data.get("timeline", "Standard (1 Month)")
        budget = session_data.get("budget", "Flexible")
        email = session_data.get("email") or "Not provided"
        preferred_time = session_data.get("preferred_contact_time", "Anytime during business hours")
        phone = session_data.get("phone", to)

        estimate_info = calculate_dummy_estimate(service_name, budget, timeline)
        est_amount = estimate_info["estimated_range"]
        est_features = estimate_info["features_included"]
        session_data["estimated_amount"] = est_amount

        body = (
            "📋 *PROJECT REQUIREMENT & ESTIMATE:*\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 *Client Name:* {name}\n"
            f"💼 *Business Type:* {business_type}\n"
            f"🛠️ *Service:* {service_name}\n"
            f"📝 *Details:* {requirement}\n"
            f"⏳ *Timeline:* {timeline}\n"
            f"💰 *Budget Preference:* {budget}\n\n"
            f"🏷️ *Instant Dummy Estimate:* *{est_amount}*\n"
            f"📦 *Key Scope:* _{est_features}_\n\n"
            f"✉️ *Email:* {email}\n"
            f"🕒 *Best Calling Time:* {preferred_time}\n"
            f"📞 *Contact Phone:* {phone}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Would you like to submit this requirement to our engineering team?"
        )

        buttons = [
            {"id": "btn_confirm_lead", "title": "Confirm ✅"},
            {"id": "btn_edit_lead", "title": "Edit ✏️"},
            {"id": "btn_cancel_lead", "title": "Cancel ❌"},
        ]

        return await whatsapp_service.send_interactive_buttons(
            to=to,
            body_text=body,
            buttons=buttons,
            header="Requirement & Estimate",
            footer="Click Confirm or reply 'confirm'",
        )

    @staticmethod
    async def send_hms_info(to: str) -> Dict[str, Any]:
        """Send complete HMS product overview with roles and functionality."""
        return await WorkflowEngine.send_hms_tour_menu(to)

    @staticmethod
    async def send_lms_info(to: str) -> Dict[str, Any]:
        """Send complete LMS product overview with roles and functionality."""
        return await WorkflowEngine.send_lms_tour_menu(to)

    @staticmethod
    async def send_hms_tour_menu(to: str) -> Dict[str, Any]:
        """Send interactive list menu to explore HMS modules."""
        body = (
            "🏥 *iZone Hospital Management System (HMS) Tour*\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Select an area below to explore its features and roles, or click request quote directly."
        )
        sections = [
            {
                "title": "Tour Actions",
                "rows": [
                    {"id": "btn_start_demo", "title": "Request Quote & Demo ✅", "description": "Proceed to request proposal & customized quote"},
                    {"id": "nav_main_menu", "title": "🏠 Return to Main Menu", "description": "Exit tour and go back to main menu"},
                ]
            },
            {
                "title": "Explore HMS Modules",
                "rows": [
                    {"id": "hms_admin", "title": "1. Admin & Setup", "description": "Rosters, departments, RBAC matrix"},
                    {"id": "hms_opd", "title": "2. OPD & Waiting Queue", "description": "Patient intake, UHID, waitlists"},
                    {"id": "hms_clinical", "title": "3. Clinical & Nurse IPD", "description": "Consultations, vitals, IPD beds"},
                    {"id": "hms_lab_pharmacy", "title": "4. Lab & Pharmacy POS", "description": "Orders, processing, FEFO dispensing"},
                    {"id": "hms_store", "title": "5. Central Inventory", "description": "Procurements (PO to GRN), adjustment logs"},
                    {"id": "hms_er", "title": "6. ER & Trauma", "description": "Triage priority, rapid admissions"},
                    {"id": "hms_billing", "title": "7. Invoices & Finance", "description": "Invoices, payment modes, audit trails"},
                ]
            }
        ]
        return await whatsapp_service.send_interactive_list(
            to=to,
            body_text=body,
            button_label="Explore HMS Modules 📋",
            sections=sections,
            header="HMS Interactive Tour",
            footer="Scroll and select an area",
        )

    @staticmethod
    async def send_lms_tour_menu(to: str) -> Dict[str, Any]:
        """Send interactive list menu to explore LMS modules."""
        body = (
            "🎓 *iZone Learning Management System (LMS) Tour*\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Select an area below to explore its features and roles, or click request quote directly."
        )
        sections = [
            {
                "title": "Tour Actions",
                "rows": [
                    {"id": "btn_start_demo", "title": "Request Quote & Demo ✅", "description": "Proceed to request proposal & customized quote"},
                    {"id": "nav_main_menu", "title": "🏠 Return to Main Menu", "description": "Exit tour and go back to main menu"},
                ]
            },
            {
                "title": "Explore LMS Modules",
                "rows": [
                    {"id": "lms_access", "title": "1. User Access & Roles", "description": "Multi-role login and guards"},
                    {"id": "lms_admin", "title": "2. Institute Admin", "description": "Courses, batches, CRM tracker"},
                    {"id": "lms_teacher", "title": "3. Instructor Module", "description": "Live classrooms, quiz, attendance"},
                    {"id": "lms_student", "title": "4. Student Experience", "description": "Dashboard, classes, exams, certs"},
                ]
            }
        ]
        return await whatsapp_service.send_interactive_list(
            to=to,
            body_text=body,
            button_label="Explore LMS Modules 📋",
            sections=sections,
            header="LMS Interactive Tour",
            footer="Scroll and select an area",
        )

    @staticmethod
    async def send_tms_info(to: str) -> Dict[str, Any]:
        """Send complete TMS product overview with roles and functionality."""
        return await WorkflowEngine.send_tms_tour_menu(to)

    @staticmethod
    async def send_tms_tour_menu(to: str) -> Dict[str, Any]:
        """Send interactive list menu to explore TMS modules."""
        body = (
            "🚛 *iZone Transport Management System (TMS) Tour*\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Select an area below to explore its features and roles, or click request quote directly."
        )
        sections = [
            {
                "title": "Tour Actions",
                "rows": [
                    {"id": "btn_start_demo", "title": "Request Quote & Demo ✅", "description": "Proceed to request proposal & customized quote"},
                    {"id": "nav_main_menu", "title": "🏠 Return to Main Menu", "description": "Exit tour and go back to main menu"},
                ]
            },
            {
                "title": "Explore TMS Modules",
                "rows": [
                    {"id": "tms_fleet", "title": "1. Fleet & Compliance", "description": "Vehicles, permits, insurance tracking"},
                    {"id": "tms_dispatch", "title": "2. Route Dispatch", "description": "Trip schedules, loading, route mapping"},
                    {"id": "tms_driver", "title": "3. Driver App", "description": "Schedules, duty logs, digital POD uploads"},
                    {"id": "tms_fuel", "title": "4. Fuel & Service Logs", "description": "Fuel cards, service cards, breakdowns"},
                    {"id": "tms_gps", "title": "5. GPS & Geofences", "description": "Real-time location, speed logs, delays"},
                    {"id": "tms_billing", "title": "6. Freight Invoices", "description": "Client invoices, fuel surcharge, pay sheets"},
                ]
            }
        ]
        return await whatsapp_service.send_interactive_list(
            to=to,
            body_text=body,
            button_label="Explore TMS Modules 📋",
            sections=sections,
            header="TMS Interactive Tour",
            footer="Scroll and select an area",
        )

    @staticmethod
    async def send_mms_info(to: str) -> Dict[str, Any]:
        """Send complete MMS product overview with roles and functionality."""
        return await WorkflowEngine.send_mms_tour_menu(to)

    @staticmethod
    async def send_mms_tour_menu(to: str) -> Dict[str, Any]:
        """Send interactive list menu to explore MMS modules."""
        body = (
            "🏭 *iZone Manufacturing Management System (MMS) Tour*\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Select an area below to explore its features and roles, or click request quote directly."
        )
        sections = [
            {
                "title": "Tour Actions",
                "rows": [
                    {"id": "btn_start_demo", "title": "Request Quote & Demo ✅", "description": "Proceed to request proposal & customized quote"},
                    {"id": "nav_main_menu", "title": "🏠 Return to Main Menu", "description": "Exit tour and go back to main menu"},
                ]
            },
            {
                "title": "Explore MMS Modules",
                "rows": [
                    {"id": "mms_bom", "title": "1. BOM & Recipes", "description": "Engineering recipes & workstation routing"},
                    {"id": "mms_planning", "title": "2. Production & MRP", "description": "MPS scheduling & material requirements planning"},
                    {"id": "mms_orders", "title": "3. Work Orders", "description": "Job cards & real-time labor logs"},
                    {"id": "mms_qa", "title": "4. Quality Control", "description": "Inspection audits & quarantine controls"},
                    {"id": "mms_maintenance", "title": "5. Machine Maintenance", "description": "OEE runtime metrics vs. downtime logs"},
                    {"id": "mms_costing", "title": "6. Costing & Yield", "description": "Actual labor & material overhead variance"},
                ]
            }
        ]
        return await whatsapp_service.send_interactive_list(
            to=to,
            body_text=body,
            button_label="Explore MMS Modules 📋",
            sections=sections,
            header="MMS Interactive Tour",
            footer="Scroll and select an area",
        )

    @staticmethod
    async def send_fms_info(to: str) -> Dict[str, Any]:
        """Send complete FMS product overview with roles and functionality."""
        return await WorkflowEngine.send_fms_tour_menu(to)

    @staticmethod
    async def send_fms_tour_menu(to: str) -> Dict[str, Any]:
        """Send interactive list menu to explore FMS modules."""
        body = (
            "💰 *iZone Financial Management System (FMS) Tour*\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Select an area below to explore its features and roles, or click request quote directly."
        )
        sections = [
            {
                "title": "Tour Actions",
                "rows": [
                    {"id": "btn_start_demo", "title": "Request Quote & Demo ✅", "description": "Proceed to request proposal & customized quote"},
                    {"id": "nav_main_menu", "title": "🏠 Return to Main Menu", "description": "Exit tour and go back to main menu"},
                ]
            },
            {
                "title": "Explore FMS Modules",
                "rows": [
                    {"id": "fms_gl", "title": "1. General Ledger", "description": "Chart of Accounts & double-entry posting rules"},
                    {"id": "fms_ap", "title": "2. Accounts Payable", "description": "Supplier billing, payouts & 3-way matching"},
                    {"id": "fms_ar", "title": "3. Accounts Receivable", "description": "Client invoicing, collections matching & dues"},
                    {"id": "fms_cash", "title": "4. Cash & Bank Rec", "description": "Statement matching & short-term liquidity forecasts"},
                    {"id": "fms_tax", "title": "5. Tax & GST Compliance", "description": "GST returns, tax brackets & audit trails"},
                    {"id": "fms_audit", "title": "6. Financial Reporting", "description": "P&L statements, Trial Balance & Balance Sheets"},
                ]
            }
        ]
        return await whatsapp_service.send_interactive_list(
            to=to,
            body_text=body,
            button_label="Explore FMS Modules 📋",
            sections=sections,
            header="FMS Interactive Tour",
            footer="Scroll and select an area",
        )

    @staticmethod
    async def send_pms_info(to: str) -> Dict[str, Any]:
        """Send complete PMS product overview with roles and functionality."""
        return await WorkflowEngine.send_pms_tour_menu(to)

    @staticmethod
    async def send_pms_tour_menu(to: str) -> Dict[str, Any]:
        """Send interactive list menu to explore PMS modules."""
        body = (
            "📅 *iZone Project Management System (PMS) Tour*\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Select an area below to explore its features and roles, or click request quote directly."
        )
        sections = [
            {
                "title": "Tour Actions",
                "rows": [
                    {"id": "btn_start_demo", "title": "Request Quote & Demo ✅", "description": "Proceed to request proposal & customized quote"},
                    {"id": "nav_main_menu", "title": "🏠 Return to Main Menu", "description": "Exit tour and go back to main menu"},
                ]
            },
            {
                "title": "Explore PMS Modules",
                "rows": [
                    {"id": "pms_planning", "title": "1. WBS & Gantt Planner", "description": "Milestones planner & task dependencies mapping"},
                    {"id": "pms_tasks", "title": "2. Kanban Board & Tasks", "description": "Task lifecycle status, comments & attachments logs"},
                    {"id": "pms_resources", "title": "3. Staff Timesheets", "description": "Capacity heatmaps & timesheets submission approvals"},
                    {"id": "pms_budget", "title": "4. Budgeting & Expenses", "description": "Burn rates, expense claims & photo receipt uploads"},
                    {"id": "pms_client", "title": "5. Client Portal", "description": "Milestones review, deliverables feedback & approvals"},
                    {"id": "pms_billing", "title": "6. Invoicing", "description": "T&M billing invoices, cost/schedule variance reports"},
                ]
            }
        ]
        return await whatsapp_service.send_interactive_list(
            to=to,
            body_text=body,
            button_label="Explore PMS Modules 📋",
            sections=sections,
            header="PMS Interactive Tour",
            footer="Scroll and select an area",
        )

    @staticmethod
    async def send_ams_info(to: str) -> Dict[str, Any]:
        """Send complete AMS product overview with roles and functionality."""
        return await WorkflowEngine.send_ams_tour_menu(to)

    @staticmethod
    async def send_ams_tour_menu(to: str) -> Dict[str, Any]:
        """Send interactive list menu to explore AMS modules."""
        body = (
            "⚙️ *iZone Asset Management System (AMS) Tour*\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Select an area below to explore its features and roles, or click request quote directly."
        )
        sections = [
            {
                "title": "Tour Actions",
                "rows": [
                    {"id": "btn_start_demo", "title": "Request Quote & Demo ✅", "description": "Proceed to request proposal & customized quote"},
                    {"id": "nav_main_menu", "title": "🏠 Return to Main Menu", "description": "Exit tour and go back to main menu"},
                ]
            },
            {
                "title": "Explore AMS Modules",
                "rows": [
                    {"id": "ams_registry", "title": "1. QR Asset Registry", "description": "Generate QR labels, parent-child logs & values catalog"},
                    {"id": "ams_intake", "title": "2. Procurement & Intake", "description": "Audit items intake, warranty tracking & alerts logs"},
                    {"id": "ams_custody", "title": "3. Check-in/out Custody", "description": "Physical device handoffs & custodian signature tracking"},
                    {"id": "ams_maintenance", "title": "4. Service/Maintenance", "description": "Calibration schedules & spare parts logs"},
                    {"id": "ams_valuation", "title": "5. Asset Valuation", "description": "Straight-line depreciation calculation ledger"},
                    {"id": "ams_audit", "title": "6. Scan Audits", "description": "Verify assets via QR scans, write-offs & scraps log"},
                ]
            }
        ]
        return await whatsapp_service.send_interactive_list(
            to=to,
            body_text=body,
            button_label="Explore AMS Modules 📋",
            sections=sections,
            header="AMS Interactive Tour",
            footer="Scroll and select an area",
        )

    @staticmethod
    async def send_oms_info(to: str) -> Dict[str, Any]:
        """Send complete OMS product overview with roles and functionality."""
        return await WorkflowEngine.send_oms_tour_menu(to)

    @staticmethod
    async def send_oms_tour_menu(to: str) -> Dict[str, Any]:
        """Send interactive list menu to explore OMS modules."""
        body = (
            "🛍️ *iZone Order Management System (OMS) Tour*\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Select an area below to explore its features and roles, or click request quote directly."
        )
        sections = [
            {
                "title": "Tour Actions",
                "rows": [
                    {"id": "btn_start_demo", "title": "Request Quote & Demo ✅", "description": "Proceed to request proposal & customized quote"},
                    {"id": "nav_main_menu", "title": "🏠 Return to Main Menu", "description": "Exit tour and go back to main menu"},
                ]
            },
            {
                "title": "Explore OMS Modules",
                "rows": [
                    {"id": "oms_capture", "title": "1. Order Channels", "description": "Ingest B2B/B2C Shopify/Amazon orders into central console"},
                    {"id": "oms_allocation", "title": "2. Stock Allocation", "description": "Auto-reserve closest stock, handle split backorders"},
                    {"id": "oms_fraud", "title": "3. Fraud Validation", "description": "Risk scoring engine, hold verify manual logs"},
                    {"id": "oms_fulfillment", "title": "4. Fulfillment Releases", "description": "Directed pick-pack prints, partial dispatch groups"},
                    {"id": "oms_shipping", "title": "5. Shipping Rates", "description": "Real-time carrier rates shopping & labels print"},
                    {"id": "oms_returns", "title": "6. Returns & Refunds", "description": "Return labels tracking, refunds/credit processing logs"},
                ]
            }
        ]
        return await whatsapp_service.send_interactive_list(
            to=to,
            body_text=body,
            button_label="Explore OMS Modules 📋",
            sections=sections,
            header="OMS Interactive Tour",
            footer="Scroll and select an area",
        )

    @staticmethod
    async def send_wms_info(to: str) -> Dict[str, Any]:
        """Send complete WMS product overview with roles and functionality."""
        return await WorkflowEngine.send_wms_tour_menu(to)

    @staticmethod
    async def send_wms_tour_menu(to: str) -> Dict[str, Any]:
        """Send interactive list menu to explore WMS modules."""
        body = (
            "📦 *iZone Warehouse Management System (WMS) Tour*\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Select an area below to explore its features and roles, or click request quote directly."
        )
        sections = [
            {
                "title": "Tour Actions",
                "rows": [
                    {"id": "btn_start_demo", "title": "Request Quote & Demo ✅", "description": "Proceed to request proposal & customized quote"},
                    {"id": "nav_main_menu", "title": "🏠 Return to Main Menu", "description": "Exit tour and go back to main menu"},
                ]
            },
            {
                "title": "Explore WMS Modules",
                "rows": [
                    {"id": "wms_receiving", "title": "1. Receiving & Putaway", "description": "Directed putaway, note damages, audit PO intakes"},
                    {"id": "wms_location", "title": "2. Bin Transfers", "description": "Real-time bin capacity maps & scanner transfers logs"},
                    {"id": "wms_picking", "title": "3. Picking Wave & Pack", "description": "Optimize wave pick paths, scan validate carton packing"},
                    {"id": "wms_replenishment", "title": "4. Replenishments", "description": "Triggers replenishment alerts & cycle counting tasks"},
                    {"id": "wms_shipping", "title": "5. Manifest Staging", "description": "Verify carrier staging lanes & manifest weight checks"},
                    {"id": "wms_reports", "title": "6. Performance & Reports", "description": "Worker pick speed logs, bin occupancy ratios & error logs"},
                ]
            }
        ]
        return await whatsapp_service.send_interactive_list(
            to=to,
            body_text=body,
            button_label="Explore WMS Modules 📋",
            sections=sections,
            header="WMS Interactive Tour",
            footer="Scroll and select an area",
        )

    @staticmethod
    async def send_sms_info(to: str) -> Dict[str, Any]:
        """Send complete SMS product overview with roles and functionality."""
        return await WorkflowEngine.send_sms_tour_menu(to)

    @staticmethod
    async def send_sms_tour_menu(to: str) -> Dict[str, Any]:
        """Send interactive list menu to explore SMS modules."""
        body = (
            "🏫 *iZone School Management System (SMS) Tour*\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Select an area below to explore its features and roles, or click request quote directly."
        )
        sections = [
            {
                "title": "Tour Actions",
                "rows": [
                    {"id": "btn_start_demo", "title": "Request Quote & Demo ✅", "description": "Proceed to request proposal & customized quote"},
                    {"id": "nav_main_menu", "title": "🏠 Return to Main Menu", "description": "Exit tour and go back to main menu"},
                ]
            },
            {
                "title": "Explore SMS Modules",
                "rows": [
                    {"id": "sms_directory", "title": "1. Admissions", "description": "Student registries, parent contacts & documents lockers"},
                    {"id": "sms_academics", "title": "2. Timetables", "description": "Class schedules, course syllabus & lesson planners"},
                    {"id": "sms_attendance", "title": "3. Attendance Portal", "description": "Log daily attendance & auto-notify parent absent logs"},
                    {"id": "sms_exams", "title": "4. Exams & Grade Book", "description": "Weighted term marks maps & automated report cards generator"},
                    {"id": "sms_fees", "title": "5. Fees Collection", "description": "Invoicing fees structures, online parent payment gates"},
                    {"id": "sms_auxiliary", "title": "6. Library & Transit", "description": "Bus routing tracking, room allotments & library issuance logs"},
                ]
            }
        ]
        return await whatsapp_service.send_interactive_list(
            to=to,
            body_text=body,
            button_label="Explore SMS Modules 📋",
            sections=sections,
            header="SMS Interactive Tour",
            footer="Scroll and select an area",
        )

    @staticmethod
    async def send_bms_info(to: str) -> Dict[str, Any]:
        """Send complete BMS product overview with roles and functionality."""
        return await WorkflowEngine.send_bms_tour_menu(to)

    @staticmethod
    async def send_bms_tour_menu(to: str) -> Dict[str, Any]:
        """Send interactive list menu to explore BMS modules."""
        body = (
            "🏢 *iZone Business Management System (BMS) Tour*\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Select an area below to explore its features and roles, or click request quote directly."
        )
        sections = [
            {
                "title": "Tour Actions",
                "rows": [
                    {"id": "btn_start_demo", "title": "Request Quote & Demo ✅", "description": "Proceed to request proposal & customized quote"},
                    {"id": "nav_main_menu", "title": "🏠 Return to Main Menu", "description": "Exit tour and go back to main menu"},
                ]
            },
            {
                "title": "Explore BMS Modules",
                "rows": [
                    {"id": "bms_crm", "title": "1. CRM & Lead Pipelines", "description": "Sales pipelines, client calls log & demo scheduling"},
                    {"id": "bms_sales", "title": "2. Quotes & Orders", "description": "Generate quotations & invoices with tax/discount auto checks"},
                    {"id": "bms_purchasing", "title": "3. Procurement", "description": "PO approvals matrix & vendor evaluation registers"},
                    {"id": "bms_hr", "title": "4. HR & Payroll", "description": "Shift plans, timesheets log & automated payroll calculations"},
                    {"id": "bms_inventory", "title": "5. Stock Control", "description": "Item logs database, transfers log & counts tracking"},
                    {"id": "bms_bi", "title": "6. BI Dashboards & KPIs", "description": "Visual charts for revenue margins, cashflow KPIs & tax returns"},
                ]
            }
        ]
        return await whatsapp_service.send_interactive_list(
            to=to,
            body_text=body,
            button_label="Explore BMS Modules 📋",
            sections=sections,
            header="BMS Interactive Tour",
            footer="Scroll and select an area",
        )

    @staticmethod
    async def send_module_description(to: str, module_key: str) -> Dict[str, Any]:
        """Send the details and description of a selected HMS/LMS module."""
        descriptions = {
            # HMS Modules
            "hms_admin": (
                "🔑 *1. Admin & Hospital Setup*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Staff Accounts*: Set up secure logins for doctors, nurses, receptionists, pharmacists, and billing staff.\n"
                "• *Rosters & Shifts*: Manage staff working hours, shifts, attendance, and leave requests.\n"
                "• *Hospital Layout*: Configure hospital departments (like Cardiology) and add branch locations.\n"
                "• *Access Controls*: Control which staff member can view or edit records in each module."
            ),
            "hms_opd": (
                "👥 *2. OPD & Waiting Queue*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Patient Registration*: Register new walk-in patients and generate a Unique Hospital ID (UHID).\n"
                "• *Appointment Booking*: Schedule doctor visits or let patients book appointments online.\n"
                "• *Live Doctor Queue*: Issuing tokens and tracking patient status (Waiting, Checked-In, Completed) in real-time.\n"
                "• *Doctor Overview*: Shows doctors how many patients are waiting in their queue for the day."
            ),
            "hms_clinical": (
                "👨‍⚕️ *3. Clinical & Nurse IPD*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Doctor Checkup*: Doctors can write consultation notes, record vitals, issue prescriptions, and order tests.\n"
                "• *Patient History*: View a patient's past prescriptions, test reports, and visit records from any branch.\n"
                "• *In-Patient (IPD) Care*: Assign patients to wards/beds, log nursing notes, record daily vitals, and track medications."
            ),
            "hms_lab_pharmacy": (
                "🔬 *4. Lab & Pharmacy POS*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Lab Test Pipeline*: Track tests from sample collection to entering results and printing verified reports.\n"
                "• *Pharmacy POS Billing*: Quick counter sales that auto-deduct medicine stock and generate billing receipts.\n"
                "• *Expiry Tracking*: Track medicine batches and get alerts when stock is near expiry."
            ),
            "hms_store": (
                "📦 *5. Store & Central Inventory*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Purchase & Stock Intake*: Handle vendor Purchase Orders (PO) and Goods Receipt Notes (GRN) to add new stock.\n"
                "• *Stock Movements*: Log item distributions to departments and track adjustments.\n"
                "• *Low Stock Alerts*: Get automatic reminders to reorder when items run low."
            ),
            "hms_er": (
                "🚨 *6. Emergency & Trauma (ER)*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Fast-Track Registration*: Instantly register emergency arrivals (Ambulance, Walk-ins) with minimum details.\n"
                "• *Triage Priority*: Classify patient emergency level (Red, Yellow, Green, Black) for quick action.\n"
                "• *Treatment & Procedures*: Log bedside emergency operations (like CPR, suturing) and record patient outcomes."
            ),
            "hms_billing": (
                "💳 *7. Invoices & Billing Finance*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Combined Invoices*: Instantly generate bills combining doctor fees, bed charges, lab tests, and medicines.\n"
                "• *Payment Collection*: Process payments via Cash, Card, UPI, or mark as Insurance/TPA claims.\n"
                "• *Discounts & Auditing*: Manage refund approvals, apply discounts, and track all billing transaction logs."
            ),
            
            # LMS Modules
            "lms_access": (
                "🔐 *1. User Access & Roles*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Multi-Role Logins*: Secure separate portals for Academy Admins, Teachers, and Students.\n"
                "• *Role-Based Control*: Automatic restriction of menu pages depending on your role."
            ),
            "lms_admin": (
                "👑 *2. Institute Admin Module*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Course & Batch Setup*: Build course structures, upload videos, arrange chapters, and group students into batches.\n"
                "• *CRM Inquiry Tracker*: Manage student registrations and track admissions from initial contact to paid enrollment.\n"
                "• *Invoices & Billing*: Track class fee collection transactions and auto-generate receipts.\n"
                "• *Connected Apps*: Integration with Zoom, Google Meet, payment gateways (Razorpay/Stripe), and WhatsApp alerts."
            ),
            "lms_teacher": (
                "👩‍🏫 *3. Instructor Module*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Live Interactive Classes*: Schedule online video classes and track student attendance reports.\n"
                "• *Quizzes & Automated Tests*: Build timed tests with automatic grading and instant results.\n"
                "• *Assignments Grading*: Share homework files, review submissions, and provide marks with feedback.\n"
                "• *Class Communication*: Post batch announcements, share files, and chat with students 1-on-1."
            ),
            "lms_student": (
                "🎓 *4. Student Experience*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Interactive Video Classes*: Join live Zoom/Google Meet classrooms with a single click.\n"
                "• *Verifiable Certificates*: Get a verifiable completion certificate automatically when course requirements are met."
            ),
            # TMS Modules
            "tms_fleet": (
                "📋 *1. Fleet Registry & Compliance*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Asset Onboarding*: Keep details on trucks, trailers, load capacities, and fuel types.\n"
                "• *Document Alerts*: Auto-reminders for vehicle permits, fitness certs, and insurance renewals.\n"
                "• *Scoping*: Hub-restricted access, ensuring depots only view their assigned fleet assets."
            ),
            "tms_dispatch": (
                "📍 *2. Dispatch & Route Planning*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Consolidation*: Group customer orders into efficient shipments based on load weight.\n"
                "• *Route Optimization*: Generate optimal routes to reduce driving time and mileage.\n"
                "• *Trip Board*: Drag-and-drop shipment dispatch boards, tracking status from Loaded to Delivered."
            ),
            "tms_driver": (
                "👤 *3. Driver Management & App*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *License Tracker*: Monitor driver licensing, medical certificates, and driving hours limits.\n"
                "• *Driver App API*: Drivers can check-in/out of hubs and upload Proof of Delivery (POD) photos.\n"
                "• *Roster Control*: Ensure driver scheduling and duty shift limits match local regulations."
            ),
            "tms_fuel": (
                "⛽ *4. Fuel & Maintenance Logs*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Fuel Receipts*: Import fuel card logs and track fuel efficiency (MPG/KMPL) per vehicle.\n"
                "• *Work Orders*: Schedule routine maintenance (oil, tires) and record unexpected breakdowns.\n"
                "• *Tolls Integration*: Auto-link electronic highway toll cards directly to active trip IDs."
            ),
            "tms_gps": (
                "📡 *5. GPS & Geofence Alerts*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Live Tracking*: View truck locations, speed records, and route deviations in real-time.\n"
                "• *Geofencing*: Automatically notify customers and depots when a truck is within 5km of a hub.\n"
                "• *Behavior Logs*: Monitor harsh braking, over-speeding, and engine idling violations."
            ),
            "tms_billing": (
                "💳 *6. Freight Billing & Invoices*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Automatic Rates*: Compute client freight invoices with fuel surcharges, tolls, and loading fees.\n"
                "• *Driver Settlements*: Auto-generate driver trip payouts based on distance, hourly pay, or drops.\n"
                "• *Audit Trails*: Log financial adjustments and freeze invoices once finalized for accounting."
            ),
            # MMS Modules
            "mms_bom": (
                "📋 *1. Bill of Materials (BOM)*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Engineering Recipes*: Multi-level BOM structures including raw components, scrap factors, and byproducts.\n"
                "• *Workstations Routing*: Define exact sequential workstation routings with run cycle estimators."
            ),
            "mms_planning": (
                "📅 *2. Production Planning & MRP*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *MPS Scheduling*: Build master schedules aligned to customer backorders and sales forecasts.\n"
                "• *MRP Shortages*: Automatic shortage analyzer triggering direct replenishment purchase requisitions."
            ),
            "mms_orders": (
                "⚙️ *3. Work Orders & Shop Floor*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Work Order Logs*: Control shop operations from Released to Completed.\n"
                "• *Operator Job Cards*: Interactive terminal job cards to record labor time and raw stock backflushing."
            ),
            "mms_qa": (
                "🔬 *4. Quality Assurance (QA/QC)*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Inspection Audits*: Record QA metrics across production lines.\n"
                "• *Quarantine Controls*: Hold failed items, blocking them from inventory while auto-generating COAs."
            ),
            "mms_maintenance": (
                "🔧 *5. Machine Maintenance*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *OEE Performance*: Track OEE runtime metrics vs. idle periods.\n"
                "• *Downtime Logs*: Record stoppage reasons (e.g., breakdown, tool changes) and schedule preventive schedules."
            ),
            "mms_costing": (
                "💰 *6. Costing & Yield Variance*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Cost Accumulation*: Aggregate actual labor, materials, and overhead costs per work order.\n"
                "• *Variance Reports*: Compare standard budgets vs. actual expenditures to check yield variances."
            ),
            # FMS Modules
            "fms_gl": (
                "📖 *1. General Ledger & Journals*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Chart of Accounts*: Multi-entity account hierarchy tree.\n"
                "• *Ledger Posting*: Double-entry balancing checks and calendar monthly period lock constraints."
            ),
            "fms_ap": (
                "💳 *2. Accounts Payable (AP)*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Supplier Billings*: Log incoming bills and route through verification workflows.\n"
                "• *3-Way Matching*: Automated validation matching POs, GRNs, and vendor bills before payouts."
            ),
            "fms_ar": (
                "📈 *3. Accounts Receivable (AR)*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Invoicing*: Generate client invoices, track dues, and trigger automated reminders.\n"
                "• *Collections Matching*: Auto-reconcile cash receipts, cards, and bank deposits."
            ),
            "fms_cash": (
                "🏦 *4. Cash & Bank Rec*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Reconciliation Engine*: Automated statement matching against internal GL bank balances.\n"
                "• *Forecasts*: Short-term liquidity projections from open payables and receivables."
            ),
            "fms_tax": (
                "📊 *5. Tax & GST Compliance*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Tax Computations*: Automated sales tax, VAT, or GST calculation on invoices.\n"
                "• *Withholding Tax*: Process deductions on supplier invoices with direct file exports."
            ),
            "fms_audit": (
                "📝 *6. Financial Reporting*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Financial Statements*: Auto-generate Balance Sheets, Trial Balances, and P&L statements.\n"
                "• *Audit Trails*: Access logs tracking ledger adjustments with user IDs."
            ),
            # PMS Modules
            "pms_planning": (
                "🗺️ *1. WBS & Gantt Planner*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Gantt Milestones*: Map task dependencies, project milestones, and WBS templates.\n"
                "• *Baselines*: Establish planning baselines to track schedule delays."
            ),
            "pms_tasks": (
                "📋 *2. Kanban Board & Tasks*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Task Lifecycle*: Manage cards from Todo to Completed with comments and attachments.\n"
                "• *Assignments*: Allocate workload, preventing over-commitment of team members."
            ),
            "pms_resources": (
                "👥 *3. Resources & Timesheets*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Capacity Heatmaps*: View allocation charts and track billable/non-billable hours.\n"
                "• *Timesheets Approval*: Workers submit weekly timesheet reports for manager approval."
            ),
            "pms_budget": (
                "💵 *4. Budgeting & Expenses*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Burn Rates*: Compare actual project expenses against initial cost budgets.\n"
                "• *Expense Tracking*: Process project-specific expense claims with photo receipt uploads."
            ),
            "pms_client": (
                "👤 *5. Client Portal & Reviews*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Client Access*: Read-only portals sharing timelines and deliverables.\n"
                "• *Deliverables Feedback*: Client sign-off workflows directly on project milestones."
            ),
            "pms_billing": (
                "💳 *6. Invoicing & Performance*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *T&M Billings*: Auto-generate invoices from approved timesheet hours.\n"
                "• *SV Logs*: Analyze Schedule Variance (SV) and Cost Variance (CV) performance."
            ),
            # AMS Modules
            "ams_registry": (
                "🏷️ *1. Asset Registry & QR Tagging*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *QR Barcode Labels*: Generate barcodes and QR code labels for physical assets.\n"
                "• *Specifications*: Catalog models, costs, purchase dates, and parent-child dependencies."
            ),
            "ams_intake": (
                "📦 *2. Procurement & Intake*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Intake Commissioning*: Audit incoming assets against PO files and set condition ratings.\n"
                "• *Warranty Reminders*: Auto-alert administrators of warranty expiration dates."
            ),
            "ams_custody": (
                "🔑 *3. Check-in/out Custody*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Handoff Tracking*: Log physical asset handoffs with digital signature verification.\n"
                "• *Custody Logs*: Track histories of device custody allocations."
            ),
            "ams_maintenance": (
                "🔧 *4. Preventive Maintenance*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Calibration Schedules*: Maintain calibration guidelines and preventive maintenance schedules.\n"
                "• *Service Tickets*: Technicians log labor hours, spare parts, and downtime metrics."
            ),
            "ams_valuation": (
                "📉 *5. Valuation & Depreciation*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Straight-Line Engines*: Auto-compute asset book values over time.\n"
                "• *Valuations Ledger*: Track current net asset value details across cost centers."
            ),
            "ams_audit": (
                "📝 *6. Scan Audits & Disposal*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Physical Verification*: Mobilize audits via site QR code scans.\n"
                "• *Scrap Processing*: Manage write-off approvals, sales, and scrap recycling logs."
            ),
            # OMS Modules
            "oms_capture": (
                "📥 *1. Multi-Channel Capture*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *API Ingest*: Sync B2B/B2C store channels (Shopify, Amazon) into a single console.\n"
                "• *Status Tracking*: Monitor orders from Payment Pending to Delivered."
            ),
            "oms_allocation": (
                "🔄 *2. Stock Allocation Rules*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Allocation Rules*: Auto-reserve stock based on customer proximity.\n"
                "• *Backorders*: Split out-of-stock items into separate backorder shipments."
            ),
            "oms_fraud": (
                "🛡️ *3. Validation & Fraud Check*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Risk Scores*: Flag high-risk transactions and correct address coordinates.\n"
                "• *Verifications*: Place flagged orders into hold queues for manual verification."
            ),
            "oms_fulfillment": (
                "📦 *4. Fulfillment Releases*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Warehouse Handshake*: Re-route order shipments directly to pick-pack lines.\n"
                "• *Split Shipments*: Group partial order dispatches from separate depots."
            ),
            "oms_shipping": (
                "🚚 *5. Shipping & Carrier Rates*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Rate Shopping*: Live quotes comparison from carriers (DHL, FedEx, UPS).\n"
                "• *Label Printing*: Prints shipping labels and customs documentation automatically."
            ),
            "oms_returns": (
                "↩️ *6. RMA Returns & Refunds*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *RMA Creation*: Generate return shipping labels and track delivery updates.\n"
                "• *Refunds Approval*: Process store credits or refunds after inspection."
            ),
            # WMS Modules
            "wms_receiving": (
                "📥 *1. Receiving & Putaway*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Directed Putaway*: Direct workers to optimal storage bins using product velocity algorithms.\n"
                "• *Receiving Logs*: Log PO audits, verify quantities, and note damaged items."
            ),
            "wms_location": (
                "🗺️ *2. Location Bins & transfers*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Bin Inventory Maps*: Real-time bin capacity maps showing lot numbers and quantities.\n"
                "• *Transfers*: Log internal stock transfers using mobile barcode scanner apps."
            ),
            "wms_picking": (
                "📦 *3. Picking Wave & Pack*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Wave Paths*: Optimize worker routes inside aisles for picking batches.\n"
                "• *Pack Scan Validation*: Double-check items via scans before carton sealing."
            ),
            "wms_replenishment": (
                "🔄 *4. Replenishment & Counts*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Replenish Alerts*: Trigger inventory replenishment before stocks run dry.\n"
                "• *Cycle Counting*: Generate cycle count tasks without stopping warehouse workflows."
            ),
            "wms_shipping": (
                "🚚 *5. Staging Lanes & Manifest*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Carrier Lanes*: Staging lane verification checks by freight carrier.\n"
                "• *Manifest Logs*: Generate BOL documentation and track trailer weights."
            ),
            "wms_reports": (
                "📊 *6. Performance & Reports*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Velocity Logs*: View pick rates, bin occupancy trends, and error logs."
            ),
            # SMS Modules
            "sms_directory": (
                "🏫 *1. Admissions & Directory*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Student Onboarding*: Manage student registries, parents contacts, and document lockers.\n"
                "• *Directories*: Maintain directories for students, classes, and administrative staff."
            ),
            "sms_academics": (
                "📅 *2. Academics & Timetables*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Schedules Builder*: Create timetables to prevent classroom and teacher schedule overlaps.\n"
                "• *Curriculums*: Manage courses, syllabus tracks, and class assignments."
            ),
            "sms_attendance": (
                "📝 *3. Attendance Portal*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Attendance Logs*: Log attendance status (Absent, Present, Late) in real-time.\n"
                "• *Parent Alerts*: Send automated WhatsApp or SMS messages for unexcused student absences."
            ),
            "sms_exams": (
                "✍️ *4. Exams & Grade Book*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Report Cards*: Automatically compile term grades into downloadable report cards.\n"
                "• *Grade Mappings*: Record weights for homework, midterms, and final exam grades."
            ),
            "sms_fees": (
                "💳 *5. Fees Collection Portal*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Fee Schedules*: Automate fee structures, invoicing schedules, and parent portals.\n"
                "• *Gateways Integration*: Receive payments via credit cards, net banking, or UPI interfaces."
            ),
            "sms_auxiliary": (
                "🚌 *6. Library, Hostels & Bus*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Logistics Logs*: Track library book distributions, room layouts, and school bus routes."
            ),
            # BMS Modules
            "bms_crm": (
                "🤝 *1. CRM & Lead Pipelines*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Lead Funnels*: Track client inquiries from initial contact to won status.\n"
                "• *Sales Logs*: Record customer call notes and schedule sales presentations."
            ),
            "bms_sales": (
                "💰 *2. Sales Quotes & Orders*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Quotations*: Build quotations with automated tax and discount lookups.\n"
                "• *Sales Invoices*: Convert quotations into invoices and verify product availability."
            ),
            "bms_purchasing": (
                "🛒 *3. Procurement Lifecycle*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Vendor Logs*: Track vendor profiles, payment histories, and performance ratings.\n"
                "• *Approvals*: Route purchase orders for approval based on value thresholds."
            ),
            "bms_hr": (
                "👥 *4. Core HR & Payroll Rosters*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Shift Rosters*: Maintain employee shift logs, timesheets, and leave records.\n"
                "• *Payroll Engines*: Automate salary calculations, deductions, and payslip generation."
            ),
            "bms_inventory": (
                "📦 *5. Product Stock Control*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Item Catalogs*: Central database of raw, intermediate, and finished goods inventory.\n"
                "• *Cycle Counts*: Log warehouse adjustments, stock transfers, and count lists."
            ),
            "bms_bi": (
                "📈 *6. BI Dashboards & KPIs*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• *Revenue Dashboards*: Visual charts of daily cash flows, sales performance, and payroll logs.\n"
                "• *BI Reports*: Generate sales forecasts and tax reports."
            )
        }

        body = descriptions.get(module_key, "Module details not found.")
        body += "\n━━━━━━━━━━━━━━━━━━━━\nWhat would you like to do next?"

        next_key = WorkflowEngine.get_next_module_key(module_key)

        buttons = [
            {"id": "btn_start_demo", "title": "Request Quote & Demo ✅"},
            {"id": f"next_{next_key}", "title": "Next Module ➡️"},
            {"id": "btn_explore_modules", "title": "Explore Modules 📋"},
        ]
        
        if "_" in module_key:
            prefix = module_key.split("_")[0]
            header_text = f"{prefix.upper()} Module Detail"
        else:
            header_text = "Product Module Detail"
            
        return await whatsapp_service.send_interactive_buttons(
            to=to,
            body_text=body,
            buttons=buttons,
            header=header_text,
            footer="Select an option below",
        )

    @staticmethod
    def get_next_module_key(current_key: str) -> str:
        """Helper to get the next sequential module key for tours."""
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
        
        if "_" in current_key:
            prefix = current_key.split("_")[0]
            if prefix in sequences:
                seq = sequences[prefix]
                if current_key in seq:
                    idx = seq.index(current_key)
                    next_idx = (idx + 1) % len(seq)
                    return seq[next_idx]
        return ""


workflow_engine = WorkflowEngine()
