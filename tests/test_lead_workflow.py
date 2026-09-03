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
    assert conv.session_data["preferred_contact_time"] == "Morning (10:00 AM – 1:00 PM)"

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
    assert lead.preferred_contact_time == "Morning (10:00 AM – 1:00 PM)"
    assert "₹28,500" in lead.estimated_amount or "₹" in lead.estimated_amount
    assert lead.status == "NEW"
    assert lead.service_id == service.id
