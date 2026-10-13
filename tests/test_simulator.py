import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_simulator_send_and_get_chat(client: AsyncClient, db_session):
    phone = "919940048776"

    # 1. Send simulated message
    send_payload = {
        "phone_number": phone,
        "sender_name": "Akash",
        "message_text": "Hi",
        "message_type": "text"
    }
    res = await client.post("/api/simulator/send", json=send_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["conversation_state"] == "MAIN_MENU"

    # 2. Query chat history
    chat_res = await client.get(f"/api/simulator/chat/{phone}")
    assert chat_res.status_code == 200
    chat_data = chat_res.json()
    assert chat_data["user"]["phone_number"] == phone
    assert chat_data["conversation"]["state"] == "MAIN_MENU"
    assert len(chat_data["db_messages"]) >= 1

    # 3. Reset chat
    reset_res = await client.post(f"/api/simulator/reset/{phone}")
    assert reset_res.status_code == 200
    assert reset_res.json()["status"] == "reset_successful"


@pytest.mark.asyncio
async def test_simulator_html_ui(client: AsyncClient):
    res = await client.get("/simulator")
    assert res.status_code == 200
    assert "WhatsApp Business Simulator" in res.text
    assert "iZone Technologies" in res.text
