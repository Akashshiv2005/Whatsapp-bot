import pytest
from httpx import AsyncClient
from sqlalchemy import select
from app.models import Conversation, User, Service, MenuOption, FAQ
from app.services.workflow_engine import WorkflowEngine


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
                            "contacts": [{"profile": {"name": "Tester"}, "wa_id": phone}],
                            "messages": [msg_obj]
                        }
                    }
                ]
            }
        ]
    }


@pytest.mark.asyncio
async def test_main_menu_navigation(client: AsyncClient, db_session, mock_whatsapp):
    phone = "919000000001"

    # 1. Send "Hi" -> Expect MAIN_MENU
    await client.post("/webhook", json=make_webhook_msg(phone, "Hi", "msg_001"))
    res = await db_session.execute(
        select(Conversation).join(User).where(User.phone_number == phone)
    )
    conv = res.scalar_one()
    assert conv.state == "MAIN_MENU"

    # 2. Send "1" (Website Development) -> Expect WEBSITE_MENU
    await client.post("/webhook", json=make_webhook_msg(phone, "1", "msg_002"))
    await db_session.refresh(conv)
    assert conv.state == "WEBSITE_MENU"

    # 3. Send "back" -> Return to MAIN_MENU
    await client.post("/webhook", json=make_webhook_msg(phone, "back", "msg_003"))
    await db_session.refresh(conv)
    assert conv.state == "MAIN_MENU"

    # 4. Send "2" (Software Development) -> Expect SOFTWARE_MENU
    await client.post("/webhook", json=make_webhook_msg(phone, "2", "msg_004"))
    await db_session.refresh(conv)
    assert conv.state == "SOFTWARE_MENU"

    # 5. Send "menu" -> Reset to MAIN_MENU
    await client.post("/webhook", json=make_webhook_msg(phone, "menu", "msg_005"))
    await db_session.refresh(conv)
    assert conv.state == "MAIN_MENU"


@pytest.mark.asyncio
async def test_human_handoff(client: AsyncClient, db_session, mock_whatsapp):
    phone = "919000000002"

    # Send "support"
    await client.post("/webhook", json=make_webhook_msg(phone, "support", "msg_sup_1"))
    res = await db_session.execute(
        select(Conversation).join(User).where(User.phone_number == phone)
    )
    conv = res.scalar_one()
    assert conv.state == "HUMAN_HANDOFF"
    assert conv.status == "HUMAN_HANDOFF"

    # Send "menu" to return to bot
    await client.post("/webhook", json=make_webhook_msg(phone, "menu", "msg_sup_2"))
    await db_session.refresh(conv)
    assert conv.state == "MAIN_MENU"
    assert conv.status == "ACTIVE"


@pytest.mark.asyncio
async def test_faq_fallback_matching(client: AsyncClient, db_session, mock_whatsapp):
    phone = "919000000003"

    # Seed an FAQ
    faq = FAQ(
        question="What are your working hours?",
        answer="Monday to Saturday 10 AM to 6:30 PM",
        keywords=["working hours", "timing", "open"],
        active=True
    )
    db_session.add(faq)
    await db_session.commit()

    # User asks "What is your timing?"
    await client.post("/webhook", json=make_webhook_msg(phone, "What is your timing?", "msg_faq_1"))
    assert any("Monday to Saturday 10 AM to 6:30 PM" in str(msg) for msg in mock_whatsapp)


@pytest.mark.asyncio
async def test_product_info_flow(client: AsyncClient, db_session, mock_whatsapp):
    phone = "919000000004"

    # Seed HMS Service & MenuOption
    hms_service = Service(
        name="Hospital Management System (HMS)",
        slug="software-hms",
        description="OPD/IPD medical ERP",
        category="Software Development",
        sort_order=1,
        active=True
    )
    db_session.add(hms_service)
    await db_session.commit()
    await db_session.refresh(hms_service)

    hms_opt = MenuOption(
        parent_state="MAIN_MENU",
        label="Hospital Management (HMS)",
        value="menu_hms",
        next_state="COLLECT_HMS",
        service_id=hms_service.id,
        sort_order=7,
        active=True
    )
    db_session.add(hms_opt)
    await db_session.commit()

    # 1. Select HMS from Main Menu -> Expect state PRODUCT_INFO
    await client.post("/webhook", json=make_webhook_msg(phone, "7", "msg_p1"))
    res = await db_session.execute(
        select(Conversation).join(User).where(User.phone_number == phone)
    )
    conv = res.scalar_one()
    assert conv.state == "PRODUCT_INFO"
    assert conv.session_data["service_name"] == "Hospital Management System (HMS)"

    # 2. Select a specific module to describe -> Expect state stays PRODUCT_INFO
    await client.post("/webhook", json=make_webhook_msg(phone, "2. OPD & Waiting Queue", "msg_p2", "interactive", "hms_opd"))
    await db_session.refresh(conv)
    assert conv.state == "PRODUCT_INFO"

    # 2.b Click Next Module -> Expect state stays PRODUCT_INFO
    await client.post("/webhook", json=make_webhook_msg(phone, "Next Module ➡️", "msg_p2_b", "interactive", "next_hms_clinical"))
    await db_session.refresh(conv)
    assert conv.state == "PRODUCT_INFO"

    # 3. Click Go Back/Explore Modules -> Expect state stays PRODUCT_INFO
    await client.post("/webhook", json=make_webhook_msg(phone, "Explore Modules 📋", "msg_p3", "interactive", "btn_explore_modules"))
    await db_session.refresh(conv)
    assert conv.state == "PRODUCT_INFO"

    # 4. Click Request Demo -> Expect state COLLECT_NAME
    await client.post("/webhook", json=make_webhook_msg(phone, "Request Quote & Demo ✅", "msg_p4", "interactive", "btn_start_demo"))
    await db_session.refresh(conv)
    assert conv.state == "COLLECT_NAME"


@pytest.mark.asyncio
async def test_tms_product_info_flow(client: AsyncClient, db_session, mock_whatsapp):
    phone = "919000000009"

    # Seed TMS Service & MenuOption
    tms_service = Service(
        name="Transport Management System (TMS)",
        slug="software-tms",
        description="Complete fleet management",
        category="Software Development",
        sort_order=10,
        active=True
    )
    db_session.add(tms_service)
    await db_session.commit()
    await db_session.refresh(tms_service)

    tms_opt = MenuOption(
        parent_state="MAIN_MENU",
        label="Transport Management (TMS)",
        value="menu_tms",
        next_state="COLLECT_TMS",
        service_id=tms_service.id,
        sort_order=9,
        active=True
    )
    db_session.add(tms_opt)
    await db_session.commit()

    # 1. Select TMS from Main Menu (mapped as option '9') -> Expect state PRODUCT_INFO
    await client.post("/webhook", json=make_webhook_msg(phone, "9", "msg_p1"))
    res = await db_session.execute(
        select(Conversation).join(User).where(User.phone_number == phone)
    )
    conv = res.scalar_one()
    assert conv.state == "PRODUCT_INFO"
    assert conv.session_data["service_name"] == "Transport Management System (TMS)"

    # 2. Select a specific module to describe -> Expect state stays PRODUCT_INFO
    await client.post("/webhook", json=make_webhook_msg(phone, "1. Fleet Registry", "msg_p2", "interactive", "tms_fleet"))
    await db_session.refresh(conv)
    assert conv.state == "PRODUCT_INFO"

    # 3. Click Next Module -> Expect state stays PRODUCT_INFO (tms_dispatch is next)
    await client.post("/webhook", json=make_webhook_msg(phone, "Next Module ➡️", "msg_p3", "interactive", "next_tms_dispatch"))
    await db_session.refresh(conv)
    assert conv.state == "PRODUCT_INFO"

    # 4. Click Request Demo -> Expect state COLLECT_NAME
    await client.post("/webhook", json=make_webhook_msg(phone, "Request Quote & Demo ✅", "msg_p4", "interactive", "btn_start_demo"))
    await db_session.refresh(conv)
    assert conv.state == "COLLECT_NAME"


@pytest.mark.asyncio
async def test_mms_product_info_flow(client: AsyncClient, db_session, mock_whatsapp):
    phone = "919000000010"

    # Seed MMS Service & MenuOption
    mms_service = Service(
        name="Manufacturing Management System (MMS)",
        slug="software-mms",
        description="Complete manufacturing",
        category="Software Development",
        sort_order=11,
        active=True
    )
    db_session.add(mms_service)
    await db_session.commit()
    await db_session.refresh(mms_service)

    mms_opt = MenuOption(
        parent_state="MAIN_MENU",
        label="Manufacturing Management (MMS)",
        value="menu_mms",
        next_state="COLLECT_MMS",
        service_id=mms_service.id,
        sort_order=10,
        active=True
    )
    db_session.add(mms_opt)
    await db_session.commit()

    # 1. Select MMS from Main Menu (mapped as option '10') -> Expect state PRODUCT_INFO
    await client.post("/webhook", json=make_webhook_msg(phone, "10", "msg_p1"))
    res = await db_session.execute(
        select(Conversation).join(User).where(User.phone_number == phone)
    )
    conv = res.scalar_one()
    assert conv.state == "PRODUCT_INFO"
    assert conv.session_data["service_name"] == "Manufacturing Management System (MMS)"

    # 2. Select a specific module to describe -> Expect state stays PRODUCT_INFO
    await client.post("/webhook", json=make_webhook_msg(phone, "1. Bill of Materials", "msg_p2", "interactive", "mms_bom"))
    await db_session.refresh(conv)
    assert conv.state == "PRODUCT_INFO"

    # 3. Click Next Module -> Expect state stays PRODUCT_INFO (mms_planning is next)
    await client.post("/webhook", json=make_webhook_msg(phone, "Next Module ➡️", "msg_p3", "interactive", "next_mms_planning"))
    await db_session.refresh(conv)
    assert conv.state == "PRODUCT_INFO"



