import pytest
from httpx import AsyncClient
from sqlalchemy import select
from app.models import Message, User, Conversation


@pytest.mark.asyncio
async def test_webhook_verification_success(client: AsyncClient):
    response = await client.get(
        "/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "test_verify_token",
            "hub.challenge": "1158201444"
        }
    )
    assert response.status_code == 200
    assert response.text == "1158201444"


@pytest.mark.asyncio
async def test_webhook_verification_invalid_token(client: AsyncClient):
    response = await client.get(
        "/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong_token",
            "hub.challenge": "1158201444"
        }
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_webhook_receive_text_message(client: AsyncClient, db_session, mock_whatsapp):
    payload = {
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
                            "contacts": [{"profile": {"name": "Akash"}, "wa_id": "919940048776"}],
                            "messages": [
                                {
                                    "from": "919940048776",
                                    "id": "wamid.HBgLMTE1ODI...",
                                    "timestamp": "1700000000",
                                    "type": "text",
                                    "text": {"body": "Hi"}
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }

    response = await client.post("/webhook", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

    # Verify user created
    res = await db_session.execute(select(User).where(User.phone_number == "919940048776"))
    user = res.scalar_one_or_none()
    assert user is not None
    assert user.name == "Akash"

    # Verify conversation created in MAIN_MENU
    res_conv = await db_session.execute(select(Conversation).where(Conversation.user_id == user.id))
    conv = res_conv.scalar_one_or_none()
    assert conv is not None
    assert conv.state == "MAIN_MENU"

    # Verify outbound WhatsApp message captured
    assert len(mock_whatsapp) >= 1
    assert mock_whatsapp[0]["to"] == "919940048776"


@pytest.mark.asyncio
async def test_webhook_idempotency_duplicate_message(client: AsyncClient, db_session, mock_whatsapp):
    payload = {
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
                            "contacts": [{"profile": {"name": "Test User"}, "wa_id": "919876543210"}],
                            "messages": [
                                {
                                    "from": "919876543210",
                                    "id": "wamid.DUPLICATE_TEST_ID_123",
                                    "timestamp": "1700000000",
                                    "type": "text",
                                    "text": {"body": "Hello"}
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }

    # First delivery
    res1 = await client.post("/webhook", json=payload)
    assert res1.status_code == 200

    count_msgs_first = len(mock_whatsapp)

    # Second duplicate delivery with same whatsapp_message_id
    res2 = await client.post("/webhook", json=payload)
    assert res2.status_code == 200

    # Verify no additional messages were processed/sent
    assert len(mock_whatsapp) == count_msgs_first

    # Verify only 1 record exists in messages table for this message ID
    res = await db_session.execute(
        select(Message).where(Message.whatsapp_message_id == "wamid.DUPLICATE_TEST_ID_123")
    )
    all_msgs = res.scalars().all()
    assert len(all_msgs) == 1
