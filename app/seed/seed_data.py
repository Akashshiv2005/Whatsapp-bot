import asyncio
import sys
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models import Service, MenuOption, FAQ, MessageTemplate, AutomationRule

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

SERVICES_DATA = [
    # 1. Website Development
    {
        "category": "Website Development",
        "name": "Business Website",
        "slug": "website-business",
        "description": "Professional corporate & business websites tailored to your brand.",
        "sort_order": 1,
        "parent_state": "WEBSITE_MENU",
        "next_state": "WEBSITE_BUSINESS",
        "menu_label": "Business Website",
        "menu_value": "website_business"
    },
    {
        "category": "Website Development",
        "name": "E-Commerce Website",
        "slug": "website-ecommerce",
        "description": "Online store with payment gateways & inventory management.",
        "sort_order": 2,
        "parent_state": "WEBSITE_MENU",
        "next_state": "WEBSITE_ECOMMERCE",
        "menu_label": "E-Commerce Website",
        "menu_value": "website_ecommerce"
    },
    {
        "category": "Website Development",
        "name": "CMS Website",
        "slug": "website-cms",
        "description": "WordPress, Strapi & CMS websites easy for non-tech teams to update.",
        "sort_order": 3,
        "parent_state": "WEBSITE_MENU",
        "next_state": "WEBSITE_CMS",
        "menu_label": "CMS Website",
        "menu_value": "website_cms"
    },
    {
        "category": "Website Development",
        "name": "Custom Web Application",
        "slug": "website-custom",
        "description": "Scalable web apps built for complex business requirements.",
        "sort_order": 4,
        "parent_state": "WEBSITE_MENU",
        "next_state": "WEBSITE_CUSTOM",
        "menu_label": "Custom Web Application",
        "menu_value": "website_custom"
    },
    {
        "category": "Website Development",
        "name": "Website Redesign",
        "slug": "website-redesign",
        "description": "Modernize and speed up your existing website with responsive UI/UX.",
        "sort_order": 5,
        "parent_state": "WEBSITE_MENU",
        "next_state": "WEBSITE_REDESIGN",
        "menu_label": "Website Redesign",
        "menu_value": "website_redesign"
    },

    # 2. Software Development & Products
    {
        "category": "Software Development",
        "name": "Hospital Management System (HMS)",
        "slug": "software-hms",
        "description": "OPD/IPD, doctor appointments, pharmacy inventory, lab & GST billing.",
        "sort_order": 1,
        "parent_state": "SOFTWARE_MENU",
        "next_state": "SOFTWARE_HMS",
        "menu_label": "Hospital Management HMS",
        "menu_value": "software_hms"
    },
    {
        "category": "Software Development",
        "name": "Learning Management System (LMS)",
        "slug": "software-lms",
        "description": "Online video courses, live classes, student quiz/exam & certificates.",
        "sort_order": 2,
        "parent_state": "SOFTWARE_MENU",
        "next_state": "SOFTWARE_LMS",
        "menu_label": "Learning Management LMS",
        "menu_value": "software_lms"
    },
    {
        "category": "Software Development",
        "name": "Chit Fund Management System",
        "slug": "software-chitfund",
        "description": "Chit group scheduling, auction, dividend calculation & payments.",
        "sort_order": 3,
        "parent_state": "SOFTWARE_MENU",
        "next_state": "SOFTWARE_CHITFUND",
        "menu_label": "Chit Fund Management",
        "menu_value": "software_chitfund"
    },
    {
        "category": "Software Development",
        "name": "CRM Software",
        "slug": "software-crm",
        "description": "CRM software to streamline leads and sales pipelines.",
        "sort_order": 4,
        "parent_state": "SOFTWARE_MENU",
        "next_state": "SOFTWARE_CRM",
        "menu_label": "CRM Software",
        "menu_value": "software_crm"
    },
    {
        "category": "Software Development",
        "name": "ERP Software",
        "slug": "software-erp",
        "description": "ERP system to unify operations, finance, and logistics.",
        "sort_order": 5,
        "parent_state": "SOFTWARE_MENU",
        "next_state": "SOFTWARE_ERP",
        "menu_label": "ERP Software",
        "menu_value": "software_erp"
    },
    {
        "category": "Software Development",
        "name": "Billing / Invoice Software",
        "slug": "software-billing",
        "description": "GST compliant billing, POS & inventory for retail and wholesale.",
        "sort_order": 6,
        "parent_state": "SOFTWARE_MENU",
        "next_state": "SOFTWARE_BILLING",
        "menu_label": "Billing Software",
        "menu_value": "software_billing"
    },
    {
        "category": "Software Development",
        "name": "Payroll Software",
        "slug": "software-payroll",
        "description": "Payroll calculations, attendance logs & compliance management.",
        "sort_order": 7,
        "parent_state": "SOFTWARE_MENU",
        "next_state": "SOFTWARE_PAYROLL",
        "menu_label": "Payroll Software",
        "menu_value": "software_payroll"
    },
    {
        "category": "Software Development",
        "name": "Custom Software",
        "slug": "software-custom",
        "description": "Bespoke software architecture for unique enterprise workflows.",
        "sort_order": 8,
        "parent_state": "SOFTWARE_MENU",
        "next_state": "SOFTWARE_CUSTOM",
        "menu_label": "Custom Software",
        "menu_value": "software_custom"
    },
    {
        "category": "Software Development",
        "name": "Student Projects Software",
        "slug": "software-student",
        "description": "Software help & coding projects for college/university students.",
        "sort_order": 9,
        "parent_state": "SOFTWARE_MENU",
        "next_state": "SOFTWARE_STUDENT",
        "menu_label": "Student Projects",
        "menu_value": "software_student"
    },
    {
        "category": "Software Development",
        "name": "Transport Management System (TMS)",
        "slug": "software-tms",
        "description": "Fleet management, dispatch, GPS tracking, driver logs & billing.",
        "sort_order": 10,
        "parent_state": "SOFTWARE_MENU",
        "next_state": "SOFTWARE_TMS",
        "menu_label": "Transport Management TMS",
        "menu_value": "software_tms"
    },
    {
        "category": "Software Development",
        "name": "Manufacturing Management System (MMS)",
        "slug": "software-mms",
        "description": "BOM, production plans, MRP, work orders & QA inspections.",
        "sort_order": 11,
        "parent_state": "SOFTWARE_MENU",
        "next_state": "SOFTWARE_MMS",
        "menu_label": "Manufacturing MMS",
        "menu_value": "software_mms"
    },
    {
        "category": "Software Development",
        "name": "Financial Management System (FMS)",
        "slug": "software-fms",
        "description": "Ledger, accounts payable/receivable, bank reconciliation & tax.",
        "sort_order": 12,
        "parent_state": "SOFTWARE_MENU",
        "next_state": "SOFTWARE_FMS",
        "menu_label": "Financial Management FMS",
        "menu_value": "software_fms"
    },
    {
        "category": "Software Development",
        "name": "Project Management System (PMS)",
        "slug": "software-pms",
        "description": "Gantt schedules, task boards, timesheets & project budgets.",
        "sort_order": 13,
        "parent_state": "SOFTWARE_MENU",
        "next_state": "SOFTWARE_PMS",
        "menu_label": "Project Management PMS",
        "menu_value": "software_pms"
    },
    {
        "category": "Software Development",
        "name": "Asset Management System (AMS)",
        "slug": "software-ams",
        "description": "Asset registry, QR tagging, custody & preventive maintenance.",
        "sort_order": 14,
        "parent_state": "SOFTWARE_MENU",
        "next_state": "SOFTWARE_AMS",
        "menu_label": "Asset Management AMS",
        "menu_value": "software_ams"
    },
    {
        "category": "Software Development",
        "name": "Order Management System (OMS)",
        "slug": "software-oms",
        "description": "Multi-channel order capture, stock rules & carrier shipping.",
        "sort_order": 15,
        "parent_state": "SOFTWARE_MENU",
        "next_state": "SOFTWARE_OMS",
        "menu_label": "Order Management OMS",
        "menu_value": "software_oms"
    },
    {
        "category": "Software Development",
        "name": "Warehouse Management System (WMS)",
        "slug": "software-wms",
        "description": "Directed putaway, bin inventory, pick/pack scans & replenishment.",
        "sort_order": 16,
        "parent_state": "SOFTWARE_MENU",
        "next_state": "SOFTWARE_WMS",
        "menu_label": "Warehouse Management WMS",
        "menu_value": "software_wms"
    },
    {
        "category": "Software Development",
        "name": "School Management System (SMS)",
        "slug": "software-sms",
        "description": "Student admissions, timetables, attendance, gradebook & fees.",
        "sort_order": 17,
        "parent_state": "SOFTWARE_MENU",
        "next_state": "SOFTWARE_SMS",
        "menu_label": "School Management SMS",
        "menu_value": "software_sms"
    },
    {
        "category": "Software Development",
        "name": "Business Management System (BMS)",
        "slug": "software-bms",
        "description": "CRM pipeline, sales invoicing, purchasing & dashboard KPIs.",
        "sort_order": 18,
        "parent_state": "SOFTWARE_MENU",
        "next_state": "SOFTWARE_BMS",
        "menu_label": "Business Management BMS",
        "menu_value": "software_bms"
    },

    # 3. Mobile App Development
    {
        "category": "Mobile App Development",
        "name": "Android App",
        "slug": "mobile-android",
        "description": "Native Android mobile apps optimized for high performance & Google Play.",
        "sort_order": 1,
        "parent_state": "MOBILE_MENU",
        "next_state": "MOBILE_ANDROID",
        "menu_label": "Android App",
        "menu_value": "mobile_android"
    },
    {
        "category": "Mobile App Development",
        "name": "iOS App",
        "slug": "mobile-ios",
        "description": "Native iOS mobile applications built for iPhone & iPad with Swift/Objective-C.",
        "sort_order": 2,
        "parent_state": "MOBILE_MENU",
        "next_state": "MOBILE_IOS",
        "menu_label": "iOS App",
        "menu_value": "mobile_ios"
    },
    {
        "category": "Mobile App Development",
        "name": "Flutter App",
        "slug": "mobile-flutter",
        "description": "Cross-platform mobile apps for Android and iOS using a single performant codebase.",
        "sort_order": 3,
        "parent_state": "MOBILE_MENU",
        "next_state": "MOBILE_FLUTTER",
        "menu_label": "Flutter App",
        "menu_value": "mobile_flutter"
    },
    {
        "category": "Mobile App Development",
        "name": "E-Commerce App",
        "slug": "mobile-ecommerce",
        "description": "Mobile shopping apps with smooth checkout, push alerts & analytics.",
        "sort_order": 4,
        "parent_state": "MOBILE_MENU",
        "next_state": "MOBILE_ECOMMERCE",
        "menu_label": "E-Commerce App",
        "menu_value": "mobile_ecommerce"
    },
    {
        "category": "Mobile App Development",
        "name": "CRM App",
        "slug": "mobile-crm",
        "description": "Field force mobile apps with GPS tracking and instant sync.",
        "sort_order": 5,
        "parent_state": "MOBILE_MENU",
        "next_state": "MOBILE_CRM",
        "menu_label": "CRM App",
        "menu_value": "mobile_crm"
    },
    {
        "category": "Mobile App Development",
        "name": "Custom Mobile Application",
        "slug": "mobile-custom",
        "description": "Custom mobile solutions for specialized business verticals.",
        "sort_order": 6,
        "parent_state": "MOBILE_MENU",
        "next_state": "MOBILE_CUSTOM",
        "menu_label": "Custom Mobile App",
        "menu_value": "mobile_custom"
    },

    # 4. SEO & Digital Marketing
    {
        "category": "SEO & Digital Marketing",
        "name": "Search Engine Optimization (SEO)",
        "slug": "marketing-seo",
        "description": "Rank higher on search engines with on-page and off-page SEO.",
        "sort_order": 1,
        "parent_state": "MARKETING_MENU",
        "next_state": "MARKETING_SEO",
        "menu_label": "Google SEO",
        "menu_value": "marketing_seo"
    },
    {
        "category": "SEO & Digital Marketing",
        "name": "Local SEO",
        "slug": "marketing-local-seo",
        "description": "Google My Business optimization to attract local buyers in your city.",
        "sort_order": 2,
        "parent_state": "MARKETING_MENU",
        "next_state": "MARKETING_LOCAL_SEO",
        "menu_label": "Local SEO & Maps",
        "menu_value": "marketing_local_seo"
    },
    {
        "category": "SEO & Digital Marketing",
        "name": "Technical SEO",
        "slug": "marketing-technical-seo",
        "description": "Speed optimization, schema markup & Core Web Vitals.",
        "sort_order": 3,
        "parent_state": "MARKETING_MENU",
        "next_state": "MARKETING_TECHNICAL_SEO",
        "menu_label": "Technical SEO",
        "menu_value": "marketing_technical_seo"
    },
    {
        "category": "SEO & Digital Marketing",
        "name": "Google Ads (PPC)",
        "slug": "marketing-google-ads",
        "description": "High-intent PPC campaigns that deliver direct ROI.",
        "sort_order": 4,
        "parent_state": "MARKETING_MENU",
        "next_state": "MARKETING_GOOGLE_ADS",
        "menu_label": "Google Ads (PPC)",
        "menu_value": "marketing_google_ads"
    },
    {
        "category": "SEO & Digital Marketing",
        "name": "Meta Ads (FB & Instagram)",
        "slug": "marketing-meta-ads",
        "description": "Targeted social ads with engaging creatives to generate leads.",
        "sort_order": 5,
        "parent_state": "MARKETING_MENU",
        "next_state": "MARKETING_META_ADS",
        "menu_label": "Meta Ads (FB & Insta)",
        "menu_value": "marketing_meta_ads"
    },
    {
        "category": "SEO & Digital Marketing",
        "name": "Social Media Marketing",
        "slug": "marketing-social-media",
        "description": "Organic branding, reels, content strategy, and community management.",
        "sort_order": 6,
        "parent_state": "MARKETING_MENU",
        "next_state": "MARKETING_SOCIAL_MEDIA",
        "menu_label": "Social Media Marketing",
        "menu_value": "marketing_social_media"
    },
    {
        "category": "SEO & Digital Marketing",
        "name": "Lead Generation Campaigns",
        "slug": "marketing-lead-gen",
        "description": "B2B and B2C qualified lead generation funnels with landing pages.",
        "sort_order": 7,
        "parent_state": "MARKETING_MENU",
        "next_state": "MARKETING_LEAD_GENERATION",
        "menu_label": "Lead Generation",
        "menu_value": "marketing_lead_gen"
    },
    {
        "category": "SEO & Digital Marketing",
        "name": "SEO Audit",
        "slug": "marketing-seo-audit",
        "description": "Comprehensive website audit identifying rankings, backlinks, and keyword gaps.",
        "sort_order": 8,
        "parent_state": "MARKETING_MENU",
        "next_state": "MARKETING_AUDIT",
        "menu_label": "SEO Audit",
        "menu_value": "marketing_seo_audit"
    },

    # 5. WhatsApp / SMS / Voice Services
    {
        "category": "WhatsApp / SMS / Voice Services",
        "name": "WhatsApp Cloud API",
        "slug": "comm-whatsapp-api",
        "description": "Official WhatsApp API setup, green tick & webhooks.",
        "sort_order": 1,
        "parent_state": "COMMUNICATION_MENU",
        "next_state": "COMMUNICATION_WHATSAPP",
        "menu_label": "WhatsApp Cloud API",
        "menu_value": "comm_whatsapp_api"
    },
    {
        "category": "WhatsApp / SMS / Voice Services",
        "name": "WhatsApp Chatbot & Automation",
        "slug": "comm-whatsapp-bot",
        "description": "Automated chatbots, CRM integrations & workflows.",
        "sort_order": 2,
        "parent_state": "COMMUNICATION_MENU",
        "next_state": "COMMUNICATION_WHATSAPP",
        "menu_label": "WhatsApp Chatbot",
        "menu_value": "comm_whatsapp_bot"
    },
    {
        "category": "WhatsApp / SMS / Voice Services",
        "name": "WhatsApp Marketing & Broadcast",
        "slug": "comm-whatsapp-marketing",
        "description": "Bulk broadcast campaigns with rich media & buttons.",
        "sort_order": 3,
        "parent_state": "COMMUNICATION_MENU",
        "next_state": "COMMUNICATION_WHATSAPP",
        "menu_label": "WhatsApp Marketing",
        "menu_value": "comm_whatsapp_marketing"
    },
    {
        "category": "WhatsApp / SMS / Voice Services",
        "name": "Bulk SMS & SMS API",
        "slug": "comm-sms",
        "description": "Transactional & promotional DLT-approved SMS gateways.",
        "sort_order": 4,
        "parent_state": "COMMUNICATION_MENU",
        "next_state": "COMMUNICATION_SMS",
        "menu_label": "Bulk SMS & SMS API",
        "menu_value": "comm_sms"
    },
    {
        "category": "WhatsApp / SMS / Voice Services",
        "name": "Bulk Voice Calls & Voice API",
        "slug": "comm-voice",
        "description": "Voice broadcasting, IVR systems & click-to-call.",
        "sort_order": 5,
        "parent_state": "COMMUNICATION_MENU",
        "next_state": "COMMUNICATION_VOICE",
        "menu_label": "Bulk Voice & Voice API",
        "menu_value": "comm_voice"
    },

    # 6. Student Services
    {
        "category": "Student Services",
        "name": "Final Year Projects",
        "slug": "student-project",
        "description": "Guidance for IEEE, Python, AI/ML, Web & Mobile final year projects.",
        "sort_order": 1,
        "parent_state": "STUDENT_MENU",
        "next_state": "STUDENT_PROJECT",
        "menu_label": "Final Year Project",
        "menu_value": "student_project"
    },
    {
        "category": "Student Services",
        "name": "Project Guidance & Mentorship",
        "slug": "student-guidance",
        "description": "One-on-one code reviews, thesis writing & viva prep assistance.",
        "sort_order": 2,
        "parent_state": "STUDENT_MENU",
        "next_state": "STUDENT_GUIDANCE",
        "menu_label": "Project Guidance",
        "menu_value": "student_guidance"
    },
    {
        "category": "Student Services",
        "name": "Technical Training",
        "slug": "student-training",
        "description": "Industrial training in Full-stack Web, Python, Flutter & Cloud.",
        "sort_order": 3,
        "parent_state": "STUDENT_MENU",
        "next_state": "STUDENT_TRAINING",
        "menu_label": "Technical Training",
        "menu_value": "student_training"
    },
    {
        "category": "Student Services",
        "name": "Internship Program",
        "slug": "student-internship",
        "description": "Real-world project experience, certificate & placement help.",
        "sort_order": 4,
        "parent_state": "STUDENT_MENU",
        "next_state": "STUDENT_INTERNSHIP",
        "menu_label": "Internship Program",
        "menu_value": "student_internship"
    },
    {
        "category": "Student Services",
        "name": "Career Guidance & Placement",
        "slug": "student-career",
        "description": "Resume reviews, mock interviews & referrals to hiring tech firms.",
        "sort_order": 5,
        "parent_state": "STUDENT_MENU",
        "next_state": "STUDENT_CAREER",
        "menu_label": "Career Guidance",
        "menu_value": "student_career"
    }
]

MAIN_MENU_OPTIONS = [
    {
        "parent_state": "MAIN_MENU",
        "label": "Website Development",
        "value": "menu_website",
        "next_state": "WEBSITE_MENU",
        "sort_order": 1
    },
    {
        "parent_state": "MAIN_MENU",
        "label": "Software Development",
        "value": "menu_software",
        "next_state": "SOFTWARE_MENU",
        "sort_order": 2
    },
    {
        "parent_state": "MAIN_MENU",
        "label": "Mobile App Development",
        "value": "menu_mobile",
        "next_state": "MOBILE_MENU",
        "sort_order": 3
    },
    {
        "parent_state": "MAIN_MENU",
        "label": "SEO & Digital Marketing",
        "value": "menu_marketing",
        "next_state": "MARKETING_MENU",
        "sort_order": 4
    },
    {
        "parent_state": "MAIN_MENU",
        "label": "WhatsApp & SMS APIs",
        "value": "menu_communication",
        "next_state": "COMMUNICATION_MENU",
        "sort_order": 5
    },
    {
        "parent_state": "MAIN_MENU",
        "label": "Student Services",
        "value": "menu_student",
        "next_state": "STUDENT_MENU",
        "sort_order": 6
    },
    {
        "parent_state": "MAIN_MENU",
        "label": "Hospital Management HMS",
        "value": "menu_hms",
        "next_state": "COLLECT_HMS",
        "sort_order": 7
    },
    {
        "parent_state": "MAIN_MENU",
        "label": "Learning Management LMS",
        "value": "menu_lms",
        "next_state": "COLLECT_LMS",
        "sort_order": 8
    },
    {
        "parent_state": "MAIN_MENU",
        "label": "Transport Management TMS",
        "value": "menu_tms",
        "next_state": "COLLECT_TMS",
        "sort_order": 9
    },
    {
        "parent_state": "MAIN_MENU",
        "label": "Manufacturing MMS",
        "value": "menu_mms",
        "next_state": "COLLECT_MMS",
        "sort_order": 10
    },
    {
        "parent_state": "MAIN_MENU",
        "label": "Financial Management FMS",
        "value": "menu_fms",
        "next_state": "COLLECT_FMS",
        "sort_order": 11
    },
    {
        "parent_state": "MAIN_MENU",
        "label": "Project Management PMS",
        "value": "menu_pms",
        "next_state": "COLLECT_PMS",
        "sort_order": 12
    },
    {
        "parent_state": "MAIN_MENU",
        "label": "Asset Management AMS",
        "value": "menu_ams",
        "next_state": "COLLECT_AMS",
        "sort_order": 13
    },
    {
        "parent_state": "MAIN_MENU",
        "label": "Order Management OMS",
        "value": "menu_oms",
        "next_state": "COLLECT_OMS",
        "sort_order": 14
    },
    {
        "parent_state": "MAIN_MENU",
        "label": "Warehouse Management WMS",
        "value": "menu_wms",
        "next_state": "COLLECT_WMS",
        "sort_order": 15
    },
    {
        "parent_state": "MAIN_MENU",
        "label": "School Management SMS",
        "value": "menu_sms",
        "next_state": "COLLECT_SMS",
        "sort_order": 16
    },
    {
        "parent_state": "MAIN_MENU",
        "label": "Business Management BMS",
        "value": "menu_bms",
        "next_state": "COLLECT_BMS",
        "sort_order": 17
    },
    {
        "parent_state": "MAIN_MENU",
        "label": "Contact iZone",
        "value": "menu_contact",
        "next_state": "CONTACT_MENU",
        "sort_order": 18
    },
    {
        "parent_state": "MAIN_MENU",
        "label": "Talk to Support",
        "value": "menu_support",
        "next_state": "HUMAN_HANDOFF",
        "sort_order": 19
    }
]

FAQS_DATA = [
    {
        "question": "What services do you provide?",
        "answer": "iZone Technologies provides Website Development, Custom Software (CRM/ERP/Billing), Mobile App Development (Android/iOS/Flutter), SEO & Digital Marketing, WhatsApp/SMS/Voice APIs, and Student Projects & Internships.",
        "keywords": ["services", "what do you do", "offerings", "about", "provide", "solutions"]
    },
    {
        "question": "Where is iZone Technologies located?",
        "answer": "Our primary office is located at:\n3rd Floor, Aruvi Arcade Complex,\n5th Cross Thillainagar, North Extension Road,\nTiruchirappalli, Tamil Nadu – 620018.\nPhone: +91-9940048776",
        "keywords": ["location", "address", "where", "office", "trichy", "thillainagar", "directions"]
    },
    {
        "question": "What are your working hours?",
        "answer": "Our team is available Monday to Saturday from 10:00 AM to 6:30 PM (IST).",
        "keywords": ["hours", "working hours", "timing", "open", "schedule", "time"]
    },
    {
        "question": "How can I get a quote or proposal?",
        "answer": "You can easily select your desired service from our menu to submit your requirements. Our sales engineering team will review and share a tailored quote within 24 hours.",
        "keywords": ["quote", "cost", "pricing", "rate", "proposal", "estimate", "charges"]
    },
    {
        "question": "What features are included in your Hospital Management System (HMS)?",
        "answer": "Our HMS (Hospital Management System) is a complete cloud-based medical ERP featuring:\n• OPD & IPD Patient Registration & Bed Management\n• Doctor Appointments & Token Display System\n• Pharmacy & Inventory Management with Batch/Expiry Tracking\n• Diagnostic Laboratory & Radiology Reports\n• Electronic Health Records (EHR) & Prescription History\n• Insurance TPA Claims, Cashless Processing & GST Invoicing\n• WhatsApp Automated Patient Reports & Appointment Reminders.\n\nType *2* or *hms* to request a free live demo!",
        "keywords": ["hms", "hospital", "hospital management", "clinic software", "doctor appointment", "opd", "ipd", "medical erp", "pharmacy software"]
    },
    {
        "question": "What features are included in your Learning Management System (LMS)?",
        "answer": "Our LMS (Learning Management System) is an all-in-one e-learning and academic platform featuring:\n• DRM-Protected Video Course Player & Chapter Quizzes\n• Live Classes via Zoom, Google Meet & YouTube Live\n• Online Exam Engine with MCQs, Negative Marking & Instant Rank Cards\n• Automated Verifiable Certificates with QR Verification\n• Integrated Payment Gateway (Razorpay/Stripe/UPI) with Auto-Enrollment\n• Dedicated Student & Teacher Portals + Android/iOS Mobile Apps.\n\nType *2* or *lms* to request a free live demo!",
        "keywords": ["lms", "learning management", "online course", "coaching software", "school lms", "college lms", "exam portal", "quiz software"]
    },
    {
        "question": "What features are included in your Chit Fund Management System?",
        "answer": "Our Chit Fund Management System is a secure, compliant financial ERP featuring:\n• Subscriber Registration & KYC Document Upload\n• Multi-Group Creation (Chit Value, Installments, Commission)\n• Automated Auction & Bid Management with Dividend Ledger\n• Dynamic Dividend Calculation & Bid/Non-Bid Subscriber Trackers\n• SMS/WhatsApp Payment Reminders & UPI/NetBanking Collections\n• Detailed Subscriber Ledgers, Agent Commission reports & Cash book.\n\nType *3* or *chitfund* to request a free live demo!",
        "keywords": ["chit fund", "chitfund", "chit software", "auction management", "bid management", "subscriber ledger", "dividend calculation", "chit finance"]
    },
    {
        "question": "Do you provide student project guidance and internships?",
        "answer": "Yes! iZone Technologies provides final year project guidance, IEEE domain projects, hands-on internships, and career training for engineering and computer science students.",
        "keywords": ["student", "project", "final year", "internship", "college", "training", "ieee"]
    }
]

TEMPLATES_DATA = [
    {
        "name": "Welcome Greeting",
        "template_key": "welcome_greeting",
        "content": "Welcome to *iZone Technologies* 👋\nHow can we help you today?",
        "language": "en"
    },
    {
        "name": "Lead Received Confirmation",
        "template_key": "lead_confirmed",
        "content": "Thank you, {name}! ✅\n\nYour requirement for *{service_name}* has been successfully received.\nOur iZone Technologies team will contact you shortly on {phone}.\n\nHave questions? Type *menu* to explore more services.",
        "language": "en"
    },
    {
        "name": "Human Handoff Confirmation",
        "template_key": "human_handoff",
        "content": "👤 You have been connected with our Support Team.\nOne of our specialists will reply to your chat during business hours (Mon-Sat, 10 AM - 6:30 PM).\n\nType *menu* at any time to return to automated options.",
        "language": "en"
    }
]


async def seed():
    print("Starting database seeding for iZone Technologies...")
    async with AsyncSessionLocal() as session:
        # 1. Seed Services
        service_map = {}
        for s_data in SERVICES_DATA:
            res = await session.execute(select(Service).where(Service.slug == s_data["slug"]))
            existing_service = res.scalar_one_or_none()
            if not existing_service:
                service = Service(
                    name=s_data["name"],
                    slug=s_data["slug"],
                    description=s_data["description"],
                    category=s_data["category"],
                    sort_order=s_data["sort_order"],
                    active=True
                )
                session.add(service)
                await session.flush()
                service_map[s_data["slug"]] = service
                print(f"Created Service: {service.name}")
            else:
                existing_service.name = s_data["name"]
                existing_service.description = s_data["description"]
                existing_service.category = s_data["category"]
                existing_service.sort_order = s_data["sort_order"]
                service_map[s_data["slug"]] = existing_service
                print(f"Updated Service: {existing_service.name}")

        # 2. Seed Main Menu Options
        for opt_data in MAIN_MENU_OPTIONS:
            res = await session.execute(
                select(MenuOption).where(
                    MenuOption.parent_state == opt_data["parent_state"],
                    MenuOption.value == opt_data["value"]
                )
            )
            existing_opt = res.scalar_one_or_none()
            if not existing_opt:
                menu_opt = MenuOption(
                    parent_state=opt_data["parent_state"],
                    label=opt_data["label"],
                    value=opt_data["value"],
                    next_state=opt_data["next_state"],
                    sort_order=opt_data["sort_order"],
                    active=True
                )
                session.add(menu_opt)
            else:
                existing_opt.label = opt_data["label"]
                existing_opt.next_state = opt_data["next_state"]
                existing_opt.sort_order = opt_data["sort_order"]

        # 3. Seed Submenu Options
        for s_data in SERVICES_DATA:
            service = service_map.get(s_data["slug"])
            res = await session.execute(
                select(MenuOption).where(
                    MenuOption.parent_state == s_data["parent_state"],
                    MenuOption.value == s_data["menu_value"]
                )
            )
            existing_opt = res.scalar_one_or_none()
            if not existing_opt:
                menu_opt = MenuOption(
                    parent_state=s_data["parent_state"],
                    label=s_data["menu_label"],
                    value=s_data["menu_value"],
                    next_state=s_data["next_state"],
                    service_id=service.id if service else None,
                    sort_order=s_data["sort_order"],
                    active=True
                )
                session.add(menu_opt)
            else:
                existing_opt.label = s_data["menu_label"]
                existing_opt.next_state = s_data["next_state"]
                existing_opt.service_id = service.id if service else None
                existing_opt.sort_order = s_data["sort_order"]

        # 4. Seed FAQs
        for faq_data in FAQS_DATA:
            res = await session.execute(select(FAQ).where(FAQ.question == faq_data["question"]))
            existing_faq = res.scalar_one_or_none()
            if not existing_faq:
                faq = FAQ(
                    question=faq_data["question"],
                    answer=faq_data["answer"],
                    keywords=faq_data["keywords"],
                    active=True
                )
                session.add(faq)
            else:
                existing_faq.answer = faq_data["answer"]
                existing_faq.keywords = faq_data["keywords"]

        # 5. Seed Templates
        for t_data in TEMPLATES_DATA:
            res = await session.execute(select(MessageTemplate).where(MessageTemplate.template_key == t_data["template_key"]))
            existing_tmpl = res.scalar_one_or_none()
            if not existing_tmpl:
                tmpl = MessageTemplate(
                    name=t_data["name"],
                    template_key=t_data["template_key"],
                    content=t_data["content"],
                    language=t_data["language"],
                    active=True
                )
                session.add(tmpl)
            else:
                existing_tmpl.name = t_data["name"]
                existing_tmpl.content = t_data["content"]
                existing_tmpl.language = t_data["language"]

        await session.commit()
        print("Database seeding completed successfully!")


if __name__ == "__main__":
    asyncio.run(seed())
