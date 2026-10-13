from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class ParsedMessage(BaseModel):
    message_id: str
    sender_phone: str
    sender_name: Optional[str] = None
    message_type: str  # text, interactive_button, interactive_list, location, image, unknown
    text_content: str  # Normalized text or selection value
    raw_text: str  # Original text typed/clicked
    selection_id: Optional[str] = None  # Button ID or List Row ID if interactive
    location_data: Optional[Dict[str, Any]] = None
    raw_payload: Dict[str, Any]


class MessageParser:
    @staticmethod
    def parse_webhook_payload(payload: Dict[str, Any]) -> List[ParsedMessage]:
        parsed_messages: List[ParsedMessage] = []

        if not payload or not isinstance(payload, dict):
            return parsed_messages

        entries = payload.get("entry", [])
        for entry in entries:
            for change in entry.get("changes", []):
                value = change.get("value", {})
                contacts = value.get("contacts", [])
                sender_name_map = {}
                for contact in contacts:
                    wa_id = contact.get("wa_id")
                    profile = contact.get("profile", {})
                    if wa_id and profile.get("name"):
                        sender_name_map[wa_id] = profile.get("name")

                messages = value.get("messages", [])
                for msg in messages:
                    msg_id = msg.get("id")
                    sender_phone = msg.get("from")
                    if not msg_id or not sender_phone:
                        continue

                    msg_type = msg.get("type", "unknown")
                    sender_name = sender_name_map.get(sender_phone)
                    text_content = ""
                    raw_text = ""
                    selection_id = None
                    location_data = None

                    if msg_type == "text":
                        text_obj = msg.get("text", {})
                        raw_text = text_obj.get("body", "").strip()
                        text_content = raw_text

                    elif msg_type == "interactive":
                        interactive_obj = msg.get("interactive", {})
                        inter_type = interactive_obj.get("type")

                        if inter_type == "button_reply":
                            btn_reply = interactive_obj.get("button_reply", {})
                            selection_id = btn_reply.get("id")
                            raw_text = btn_reply.get("title", "")
                            text_content = selection_id or raw_text
                            msg_type = "interactive_button"

                        elif inter_type == "list_reply":
                            list_reply = interactive_obj.get("list_reply", {})
                            selection_id = list_reply.get("id")
                            raw_text = list_reply.get("title", "")
                            text_content = selection_id or raw_text
                            msg_type = "interactive_list"

                    elif msg_type == "location":
                        loc_obj = msg.get("location", {})
                        location_data = {
                            "latitude": loc_obj.get("latitude"),
                            "longitude": loc_obj.get("longitude"),
                            "name": loc_obj.get("name"),
                            "address": loc_obj.get("address"),
                        }
                        raw_text = "[Location]"
                        text_content = "[Location]"

                    elif msg_type == "image":
                        raw_text = msg.get("image", {}).get("caption", "[Image]")
                        text_content = raw_text

                    else:
                        raw_text = f"[{msg_type.upper()}]"
                        text_content = raw_text

                    parsed_messages.append(
                        ParsedMessage(
                            message_id=msg_id,
                            sender_phone=sender_phone,
                            sender_name=sender_name,
                            message_type=msg_type,
                            text_content=text_content,
                            raw_text=raw_text,
                            selection_id=selection_id,
                            location_data=location_data,
                            raw_payload=msg,
                        )
                    )

        return parsed_messages
