import pytest
from httpx import AsyncClient
from sqlalchemy import select
from app.models import Conversation, User, Service, MenuOption, Lead


def make_webhook_msg(phone: str, text: str, msg_id: str, msg_type: str = "text", interactive_id: str = None):
    msg_obj = {
        "from": phone,
        "id": msg_id,
        "timestamp": "1700000000",
        "type": msg_type,
    }
    if msg_type == "text":
        msg_obj["text"] = {"body": text}
    elif msg_type == "interactive":
        msg_obj["interactive"] = {
            "type": "button_reply" if "btn" in (interactive_id or "") else "list_reply",
            ("button_reply" if "btn" in (interactive_id or "") else "list_reply"): {
                "id": interactive_id,
                "title": text
            }
        }

    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "10001",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {"phone_number_id": "109283746592837"},
                            "contacts": [{"profile": {"name": "Akash"}, "wa_id": phone}],
                            "messages": [msg_obj]
                        }
                    }
                ]
            }
        ]
    }


@pytest.mark.asyncio
async def test_full_lead_collection_journey(client: AsyncClient, db_session, mock_whatsapp):
    phone = "919940048776"

    # Seed Service and MenuOption
    service = Service(
        name="E-Commerce Website",
        slug="website-ecommerce",
        description="Online store with payment gateway",
        category="Website Development",
        sort_order=2,
        active=True
    )
    db_session.add(service)
    await db_session.commit()
    await db_session.refresh(service)

    menu_opt = MenuOption(
        parent_state="WEBSITE_MENU",
        label="E-Commerce Website",
        value="website_ecommerce",
        next_state="WEBSITE_ECOMMERCE",
        service_id=service.id,
        sort_order=2,
        active=True
    )
    db_session.add(menu_opt)
    await db_session.commit()

    # Step 0: User sends "Hi" -> MAIN_MENU
    await client.post("/webhook", json=make_webhook_msg(phone, "Hi", "m1"))

    # Step 1: User selects "Website Development" -> WEBSITE_MENU
    await client.post("/webhook", json=make_webhook_msg(phone, "1", "m2"))

    # Step 2: User selects "E-Commerce Website" -> COLLECT_NAME
    await client.post("/webhook", json=make_webhook_msg(phone, "E-Commerce Website", "m3", "interactive", "website_ecommerce"))
    res = await db_session.execute(select(Conversation).join(User).where(User.phone_number == phone))
    conv = res.scalar_one()
    assert conv.state == "COLLECT_NAME"

    # Step 3: User provides Name -> COLLECT_BUSINESS_TYPE
    await client.post("/webhook", json=make_webhook_msg(phone, "Akash", "m4"))
    await db_session.refresh(conv)
    assert conv.state == "COLLECT_BUSINESS_TYPE"
    assert conv.session_data["name"] == "Akash"

    # Step 4: User provides Business Type -> COLLECT_REQUIREMENT
    await client.post("/webhook", json=make_webhook_msg(phone, "Clothing & Apparel", "m5"))
    await db_session.refresh(conv)
    assert conv.state == "COLLECT_REQUIREMENT"
    assert conv.session_data["business_type"] == "Clothing & Apparel"

    # Step 5: User provides Requirement -> COLLECT_TIMELINE
    await client.post("/webhook", json=make_webhook_msg(phone, "I need an online clothing store with Razorpay integration", "m6"))
    await db_session.refresh(conv)
    assert conv.state == "COLLECT_TIMELINE"
    assert conv.session_data["requirement"] == "I need an online clothing store with Razorpay integration"

    # Step 6: User selects Timeline -> COLLECT_BUDGET
    await client.post("/webhook", json=make_webhook_msg(phone, "1 Month", "m7", "interactive", "time_standard"))
    await db_session.refresh(conv)
    assert conv.state == "COLLECT_BUDGET"
    assert conv.session_data["timeline"] == "Standard (1 Month)"

    # Step 7: User selects Budget -> COLLECT_EMAIL
    await client.post("/webhook", json=make_webhook_msg(phone, "₹50,000 – ₹1,00,000", "m8", "interactive", "budget_3"))
    await db_session.refresh(conv)
    assert conv.state == "COLLECT_EMAIL"
    assert conv.session_data["budget"] == "₹50,000 – ₹1,00,000"

    # Step 8: User provides Email -> COLLECT_PREFERRED_TIME
    await client.post("/webhook", json=make_webhook_msg(phone, "akash@example.com", "m9"))
    await db_session.refresh(conv)
    assert conv.state == "COLLECT_PREFERRED_TIME"
    assert conv.session_data["email"] == "akash@example.com"

    # Step 9: User selects Preferred Time -> COLLECT_CONTACT
    await client.post("/webhook", json=make_webhook_msg(phone, "Morning (10AM–1PM)", "m10", "interactive", "slot_morning"))
    await db_session.refresh(conv)
    assert conv.state == "COLLECT_CONTACT"
    assert "Morning" in conv.session_data["preferred_contact_time"]

    # Step 10: User confirms Phone -> LEAD_CONFIRMATION
    await client.post("/webhook", json=make_webhook_msg(phone, "OK", "m11"))
    await db_session.refresh(conv)
    assert conv.state == "LEAD_CONFIRMATION"

    # Step 11: User clicks "Confirm" -> Creates Lead and resets to MAIN_MENU
    await client.post("/webhook", json=make_webhook_msg(phone, "Confirm", "m12", "interactive", "btn_confirm_lead"))
    await db_session.refresh(conv)
    assert conv.state == "MAIN_MENU"

    # Verify Lead persisted in Database with all rich fields
    res_lead = await db_session.execute(select(Lead).where(Lead.phone_number == phone))
    lead = res_lead.scalar_one_or_none()
    assert lead is not None
    assert lead.name == "Akash"
    assert lead.email == "akash@example.com"
    assert lead.business_type == "Clothing & Apparel"
    assert lead.requirement == "I need an online clothing store with Razorpay integration"
    assert lead.timeline == "Standard (1 Month)"
    assert lead.budget == "₹50,000 – ₹1,00,000"
    assert "Morning" in lead.preferred_contact_time
    assert "₹28,500" in lead.estimated_amount or "₹" in lead.estimated_amount
    assert lead.status == "NEW"
    assert lead.service_id == service.id


@pytest.mark.asyncio
async def test_name_and_phone_validation(client: AsyncClient, db_session, mock_whatsapp):
    phone = "919940049999"

    # Seed Service and MenuOption
    service = Service(
        name="Billing Software",
        slug="software-billing",
        description="POS and invoice system",
        category="Software Development",
        sort_order=1,
        active=True
    )
    db_session.add(service)
    await db_session.commit()
    await db_session.refresh(service)

    menu_opt = MenuOption(
        parent_state="SOFTWARE_MENU",
        label="Billing Software",
        value="software_billing",
        next_state="COLLECT_NAME",
        service_id=service.id,
        sort_order=1,
        active=True
    )
    db_session.add(menu_opt)
    await db_session.commit()

    # Step 0: User starts -> MAIN_MENU -> SOFTWARE_MENU
    await client.post("/webhook", json=make_webhook_msg(phone, "Hi", "v1"))
    await client.post("/webhook", json=make_webhook_msg(phone, "2", "v2"))
    await client.post("/webhook", json=make_webhook_msg(phone, "Billing Software", "v3", "interactive", "software_billing"))

    res = await db_session.execute(select(Conversation).join(User).where(User.phone_number == phone))
    conv = res.scalar_one()
    assert conv.state == "COLLECT_NAME"

    # 1. Invalid Name: containing numbers
    await client.post("/webhook", json=make_webhook_msg(phone, "Akash123", "v4"))
    await db_session.refresh(conv)
    assert conv.state == "COLLECT_NAME"
    assert any("Name must not contain any numbers" in str(msg) for msg in mock_whatsapp)

    # 2. Invalid Name: only numbers
    await client.post("/webhook", json=make_webhook_msg(phone, "98765", "v5"))
    await db_session.refresh(conv)
    assert conv.state == "COLLECT_NAME"

    # 3. Valid Name: letters only -> advances to COLLECT_BUSINESS_TYPE
    await client.post("/webhook", json=make_webhook_msg(phone, "Akash Kumar", "v6"))
    await db_session.refresh(conv)
    assert conv.state == "COLLECT_BUSINESS_TYPE"
    assert conv.session_data["name"] == "Akash Kumar"

    # Advance steps to reach COLLECT_CONTACT
    await client.post("/webhook", json=make_webhook_msg(phone, "Supermarket", "v7"))
    await client.post("/webhook", json=make_webhook_msg(phone, "POS with barcode", "v8"))
    await client.post("/webhook", json=make_webhook_msg(phone, "Urgent (< 2 Weeks)", "v9", "interactive", "time_urgent"))
    await client.post("/webhook", json=make_webhook_msg(phone, "Below ₹25,000", "v10", "interactive", "budget_1"))
    await client.post("/webhook", json=make_webhook_msg(phone, "skip", "v11"))
    await client.post("/webhook", json=make_webhook_msg(phone, "Morning (10AM–1PM)", "v12", "interactive", "slot_morning"))

    await db_session.refresh(conv)
    assert conv.state == "COLLECT_CONTACT"

    # 4. Invalid Phone: contains words/letters
    await client.post("/webhook", json=make_webhook_msg(phone, "call my phone please", "v13"))
    await db_session.refresh(conv)
    assert conv.state == "COLLECT_CONTACT"
    assert any("Mobile number must not contain any words or letters" in str(msg) for msg in mock_whatsapp)

    # 5. Invalid Phone: word mixed with digits
    await client.post("/webhook", json=make_webhook_msg(phone, "mob 9876543210", "v14"))
    await db_session.refresh(conv)
    assert conv.state == "COLLECT_CONTACT"

    # 6. Valid Phone: digits only
    await client.post("/webhook", json=make_webhook_msg(phone, "9876543210", "v15"))
    await db_session.refresh(conv)
    assert conv.state == "LEAD_CONFIRMATION"
    assert conv.session_data["phone"] == "9876543210"


@pytest.mark.asyncio
async def test_requirement_options_and_other_selection(client: AsyncClient, db_session, mock_whatsapp):
    phone = "919940047777"

    # Seed Service and MenuOption
    service = Service(
        name="Hospital Management HMS",
        slug="software-hms",
        description="OPD/IPD medical ERP",
        category="Software Development",
        sort_order=1,
        active=True
    )
    db_session.add(service)
    await db_session.commit()
    await db_session.refresh(service)

    menu_opt = MenuOption(
        parent_state="ERP_MENU_1",
        label="Hospital Management HMS",
        value="software_hms",
        next_state="COLLECT_NAME",
        service_id=service.id,
        sort_order=1,
        active=True
    )
    db_session.add(menu_opt)
    await db_session.commit()

    # Start and select Hospital Management HMS (Option 6 -> ERP_MENU_1, then Option 1 -> HMS)
    await client.post("/webhook", json=make_webhook_msg(phone, "Hi", "req_1"))
    await client.post("/webhook", json=make_webhook_msg(phone, "6", "req_2"))
    await client.post("/webhook", json=make_webhook_msg(phone, "1", "req_2b"))
    
    res = await db_session.execute(select(Conversation).join(User).where(User.phone_number == phone))
    conv = res.scalar_one()

    # If it went to PRODUCT_INFO or direct, start demo to reach COLLECT_NAME
    if conv.state == "PRODUCT_INFO":
        await client.post("/webhook", json=make_webhook_msg(phone, "Request Quote & Demo ✅", "req_3", "interactive", "btn_start_demo"))
        await db_session.refresh(conv)

    assert conv.state == "COLLECT_NAME"

    # Step 1: Provide Name -> COLLECT_BUSINESS_TYPE
    await client.post("/webhook", json=make_webhook_msg(phone, "Dr. Ramesh", "req_4"))
    await db_session.refresh(conv)
    assert conv.state == "COLLECT_BUSINESS_TYPE"

    # Step 2: Provide Business Type -> COLLECT_REQUIREMENT (sends interactive list)
    await client.post("/webhook", json=make_webhook_msg(phone, "Multi-Speciality Hospital", "req_5"))
    await db_session.refresh(conv)
    assert conv.state == "COLLECT_REQUIREMENT"

    # Case A: User clicks "Other" -> COLLECT_CUSTOM_REQUIREMENT
    await client.post("/webhook", json=make_webhook_msg(phone, "Other / Custom", "req_6", "interactive", "req_other"))
    await db_session.refresh(conv)
    assert conv.state == "COLLECT_CUSTOM_REQUIREMENT"
    assert any("Custom Requirement:" in str(msg) for msg in mock_whatsapp)

    # User enters specific requirement text
    await client.post("/webhook", json=make_webhook_msg(phone, "ICU ventilator monitoring & tele-consultation", "req_7"))
    await db_session.refresh(conv)
    assert conv.state == "COLLECT_TIMELINE"
    assert conv.session_data["requirement"] == "ICU ventilator monitoring & tele-consultation"


@pytest.mark.asyncio
async def test_business_type_selection_and_other(client: AsyncClient, db_session, mock_whatsapp):
    phone = "919940049999"

    service = Service(
        name="Business Website",
        slug="website-business",
        description="Corporate web presence",
        category="Website Development",
        sort_order=1,
        active=True
    )
    db_session.add(service)
    await db_session.commit()

    menu_opt = MenuOption(
        parent_state="WEBSITE_MENU",
        label="Business Website",
        value="website_business",
        next_state="COLLECT_NAME",
        service_id=service.id,
        sort_order=1,
        active=True
    )
    db_session.add(menu_opt)
    await db_session.commit()

    # Reach COLLECT_NAME
    await client.post("/webhook", json=make_webhook_msg(phone, "Hi", "bt_1"))
    await client.post("/webhook", json=make_webhook_msg(phone, "1", "bt_2"))
    await client.post("/webhook", json=make_webhook_msg(phone, "1", "bt_2b"))

    res = await db_session.execute(select(Conversation).join(User).where(User.phone_number == phone))
    conv = res.scalar_one()

    if conv.state == "PRODUCT_INFO":
        await client.post("/webhook", json=make_webhook_msg(phone, "Request Quote & Demo ✅", "bt_3", "interactive", "btn_start_demo"))
        await db_session.refresh(conv)

    assert conv.state == "COLLECT_NAME"

    # Step 1: Name -> triggers send_business_type_selection
    await client.post("/webhook", json=make_webhook_msg(phone, "Rajesh Kumar", "bt_4"))
    await db_session.refresh(conv)
    assert conv.state == "COLLECT_BUSINESS_TYPE"
    assert any("Business or Organization Type" in str(m) for m in mock_whatsapp)

    # Step 2: Choose "Other / Custom"
    await client.post("/webhook", json=make_webhook_msg(phone, "Other / Custom", "bt_5", "interactive", "biz_other"))
    await db_session.refresh(conv)
    assert conv.state == "COLLECT_CUSTOM_BUSINESS_TYPE"
    assert any("Custom Business Type:" in str(m) for m in mock_whatsapp)

    # Step 2b: Enter custom business type
    await client.post("/webhook", json=make_webhook_msg(phone, "Organic Dairy Farm", "bt_6"))
    await db_session.refresh(conv)
    assert conv.state == "COLLECT_REQUIREMENT"
    assert conv.session_data["business_type"] == "Organic Dairy Farm"

    # Step 3: Choose standard requirement
    await client.post("/webhook", json=make_webhook_msg(phone, "Corporate Website", "bt_7", "interactive", "req_web_corp"))
    await db_session.refresh(conv)
    assert conv.state == "COLLECT_TIMELINE"

    # Step 4: Choose Other / Custom Timeline
    await client.post("/webhook", json=make_webhook_msg(phone, "Other / Custom", "bt_8", "interactive", "time_other"))
    await db_session.refresh(conv)
    assert conv.state == "COLLECT_CUSTOM_TIMELINE"
    assert any("Custom Project Timeline:" in str(m) for m in mock_whatsapp)

    # Step 4b: Enter custom timeline text
    await client.post("/webhook", json=make_webhook_msg(phone, "Within 10 Days", "bt_9"))
    await db_session.refresh(conv)
    assert conv.state == "COLLECT_BUDGET"
    assert conv.session_data["timeline"] == "Within 10 Days"

    # Step 5: Choose Other / Custom Budget
    await client.post("/webhook", json=make_webhook_msg(phone, "Other / Custom", "bt_10", "interactive", "budget_other"))
    await db_session.refresh(conv)
    assert conv.state == "COLLECT_CUSTOM_BUDGET"
    assert any("Custom Budget:" in str(m) for m in mock_whatsapp)

    # Step 5b: Enter custom budget text
    await client.post("/webhook", json=make_webhook_msg(phone, "Around 60,000 INR", "bt_11"))
    await db_session.refresh(conv)
    assert conv.state == "COLLECT_EMAIL"
    assert conv.session_data["budget"] == "Around 60,000 INR"

    # Step 6: Provide email
    await client.post("/webhook", json=make_webhook_msg(phone, "rajesh@dairy.com", "bt_12"))
    await db_session.refresh(conv)
    assert conv.state == "COLLECT_PREFERRED_TIME"

    # Step 7: Choose Other / Custom Preferred Time
    await client.post("/webhook", json=make_webhook_msg(phone, "Other / Custom", "bt_13", "interactive", "slot_other"))
    await db_session.refresh(conv)
    assert conv.state == "COLLECT_CUSTOM_PREFERRED_TIME"
    assert any("Custom Preferred Time:" in str(m) for m in mock_whatsapp)

    # Step 7b: Enter custom preferred time text
    await client.post("/webhook", json=make_webhook_msg(phone, "Every Sunday 11 AM", "bt_14"))
    await db_session.refresh(conv)
    assert conv.state == "COLLECT_CONTACT"
    assert conv.session_data["preferred_contact_time"] == "Every Sunday 11 AM"



