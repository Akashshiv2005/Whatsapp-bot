from typing import Any, Dict, List, Optional
import time
import httpx
from app.core.config import get_settings
from app.core.logging import logger

settings = get_settings()


class WhatsAppService:
    def __init__(self, access_token: Optional[str] = None, phone_number_id: Optional[str] = None):
        self.access_token = access_token or settings.META_ACCESS_TOKEN
        self.phone_number_id = phone_number_id or settings.META_PHONE_NUMBER_ID
        self.base_url = f"https://graph.facebook.com/{settings.META_API_VERSION}/{self.phone_number_id}/messages"
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        # In-memory testing outbox for simulator and verification
        self.outbox_history: List[Dict[str, Any]] = []

    def get_outbox(self, to_phone: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve recent dispatched messages for a recipient or all recipients."""
        if not to_phone:
            return list(self.outbox_history)
        clean_target = to_phone.replace("+", "").strip()
        return [
            msg for msg in self.outbox_history
            if msg.get("to", "").replace("+", "").strip() == clean_target
        ]

    def clear_outbox(self, to_phone: Optional[str] = None) -> None:
        """Clear outbox history."""
        if not to_phone:
            self.outbox_history.clear()
        else:
            clean_target = to_phone.replace("+", "").strip()
            self.outbox_history = [
                msg for msg in self.outbox_history
                if msg.get("to", "").replace("+", "").strip() != clean_target
            ]

    async def _send_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Internal helper to dispatch message payload to Meta Graph API or Mock Simulator."""
        recipient = payload.get("to", "unknown")
        msg_type = payload.get("type", "unknown")
        logger.info(f"Dispatching WhatsApp message to {recipient} (type: {msg_type})")

        # Save to local outbox history
        recorded_item = dict(payload)
        recorded_item["timestamp"] = int(time.time())
        self.outbox_history.append(recorded_item)

        # In testing/dummy mode if token is dummy placeholder
        if self.access_token.startswith("placeholder_") or self.access_token.startswith("EAAB_TEST"):
            mock_id = f"wamid.mock_{int(time.time()*1000)}"
            logger.info(f"[TEST/SIMULATOR MODE] WhatsApp message to {recipient} simulated successfully: {mock_id}")
            return {
                "messaging_product": "whatsapp",
                "contacts": [{"input": recipient, "wa_id": recipient}],
                "messages": [{"id": mock_id}],
                "payload": payload,
            }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(self.base_url, headers=self.headers, json=payload)
                response.raise_for_status()
                data = response.json()
                data["payload"] = payload
                logger.info(f"WhatsApp message sent successfully to {recipient}: {data.get('messages', [{}])[0].get('id')}")
                return data

        except httpx.HTTPStatusError as e:
            error_text = e.response.text
            logger.error(f"WhatsApp API HTTP error ({e.response.status_code}): {error_text}")
            return {"error": True, "status_code": e.response.status_code, "details": error_text, "payload": payload}
        except (httpx.TimeoutException, httpx.RequestError) as e:
            logger.error(f"WhatsApp API network/timeout error: {e}")
            return {"error": True, "status_code": 500, "details": str(e), "payload": payload}

    async def send_text(self, to: str, text: str, preview_url: bool = False) -> Dict[str, Any]:
        """Send a standard text message."""
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {
                "preview_url": preview_url,
                "body": text,
            }
        }
        return await self._send_payload(payload)

    async def send_interactive_buttons(
        self,
        to: str,
        body_text: str,
        buttons: List[Dict[str, str]],  # [{"id": "btn_1", "title": "Option 1"}] (max 3 buttons)
        header: Optional[str] = None,
        footer: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send an interactive button reply message (up to 3 buttons supported by Meta)."""
        formatted_buttons = []
        for btn in buttons[:3]:
            formatted_buttons.append({
                "type": "reply",
                "reply": {
                    "id": str(btn["id"]),
                    "title": str(btn["title"])[:20],
                }
            })

        action_payload: Dict[str, Any] = {"buttons": formatted_buttons}

        interactive_obj: Dict[str, Any] = {
            "type": "button",
            "body": {"text": body_text},
            "action": action_payload,
        }

        if header:
            interactive_obj["header"] = {"type": "text", "text": header[:60]}
        if footer:
            interactive_obj["footer"] = {"text": footer[:60]}

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "interactive",
            "interactive": interactive_obj,
        }
        return await self._send_payload(payload)

    async def send_interactive_list(
        self,
        to: str,
        body_text: str,
        button_label: str,
        sections: List[Dict[str, Any]],
        header: Optional[str] = None,
        footer: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send an interactive list message (supports up to 10 rows across sections)."""
        formatted_sections = []
        for sec in sections:
            formatted_rows = []
            for row in sec.get("rows", []):
                r_item: Dict[str, Any] = {
                    "id": str(row["id"]),
                    "title": str(row["title"])[:24],
                }
                if row.get("description"):
                    r_item["description"] = str(row["description"])[:72]
                formatted_rows.append(r_item)

            formatted_sections.append({
                "title": str(sec.get("title", "Options"))[:24],
                "rows": formatted_rows,
            })

        interactive_obj: Dict[str, Any] = {
            "type": "list",
            "body": {"text": body_text},
            "action": {
                "button": button_label[:20],
                "sections": formatted_sections,
            }
        }

        if header:
            interactive_obj["header"] = {"type": "text", "text": header[:60]}
        if footer:
            interactive_obj["footer"] = {"text": footer[:60]}

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "interactive",
            "interactive": interactive_obj,
        }
        return await self._send_payload(payload)

    async def send_location(
        self,
        to: str,
        latitude: float,
        longitude: float,
        name: str,
        address: str,
    ) -> Dict[str, Any]:
        """Send a map location pin."""
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "location",
            "location": {
                "latitude": latitude,
                "longitude": longitude,
                "name": name,
                "address": address,
            }
        }
        return await self._send_payload(payload)

    async def send_image(self, to: str, image_url: str, caption: Optional[str] = None) -> Dict[str, Any]:
        """Send an image via URL."""
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "image",
            "image": {
                "link": image_url,
                **({"caption": caption} if caption else {})
            }
        }
        return await self._send_payload(payload)

    async def send_document(
        self,
        to: str,
        document_url: str,
        caption: Optional[str] = None,
        filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send a PDF or document via URL."""
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "document",
            "document": {
                "link": document_url,
                **({"caption": caption} if caption else {}),
                **({"filename": filename} if filename else {})
            }
        }
        return await self._send_payload(payload)

    async def send_template(
        self,
        to: str,
        template_name: str,
        language_code: str = "en",
        components: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Send an approved WhatsApp template message."""
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
                **({"components": components} if components else {})
            }
        }
        return await self._send_payload(payload)


whatsapp_service = WhatsAppService()
