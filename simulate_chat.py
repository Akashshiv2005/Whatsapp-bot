"""
iZone Technologies WhatsApp Bot — Interactive CLI Simulator
Test the state machine, menus, and lead collection directly in your terminal without Meta credentials.
"""

import asyncio
import sys
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.services.whatsapp import whatsapp_service
from app.services.message_parser import ParsedMessage
from app.services.message_handler import message_handler
from app.models import Conversation, User, Lead

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def print_banner():
    print("=" * 65)
    print("  iZone Technologies — WhatsApp Bot Interactive Terminal Tester")
    print("=" * 65)
    print("Commands:")
    print("  - Type 'menu' or '0' for Main Menu")
    print("  - Type 'back' to step backward")
    print("  - Type 'cancel' to cancel ongoing workflow")
    print("  - Type 'support' for Human Handoff")
    print("  - Type 'exit' or 'quit' to end simulation")
    print("=" * 65)


def display_bot_message(payload: dict):
    msg_type = payload.get("type", "text")
    print("\n" + "🤖 iZone Bot:".ljust(65, "-"))

    if msg_type == "text":
        print(payload.get("text", {}).get("body", ""))

    elif msg_type == "interactive":
        inter = payload.get("interactive", {})
        if inter.get("header"):
            print(f"[{inter['header']['text']}]")
        if inter.get("body"):
            print(inter["body"]["text"])

        # Display buttons
        if inter.get("type") == "button":
            print("\n[Action Buttons]:")
            for idx, btn in enumerate(inter.get("action", {}).get("buttons", []), start=1):
                print(f"  [{idx}] {btn['reply']['title']} (ID: {btn['reply']['id']})")

        # Display list sections
        elif inter.get("type") == "list":
            for sec in inter.get("action", {}).get("sections", []):
                print(f"\n--- {sec.get('title', 'Options')} ---")
                for r in sec.get("rows", []):
                    desc = f" - {r['description']}" if r.get("description") else ""
                    print(f"  • {r['title']}{desc} (ID: {r['id']})")

        if inter.get("footer"):
            print(f"\n({inter['footer']['text']})")

    elif msg_type == "location":
        loc = payload.get("location", {})
        print(f"📍 Location Pin: {loc.get('name')}")
        print(f"   Address: {loc.get('address')}")
        print(f"   Coords: Lat {loc.get('latitude')}, Lng {loc.get('longitude')}")

    print("-" * 65 + "\n")


async def run_cli():
    print_banner()
    phone = input("Enter test WhatsApp phone number [Default: 919940048776]: ").strip()
    if not phone:
        phone = "919940048776"
    sender_name = input("Enter your name [Default: Akash]: ").strip()
    if not sender_name:
        sender_name = "Akash"

    print(f"\n[Starting chat session for {sender_name} ({phone})...]")

    # Send initial greeting
    async with AsyncSessionLocal() as db:
        whatsapp_service.clear_outbox(phone)
        parsed = ParsedMessage(
            message_id=f"wamid.cli_start_{phone}",
            sender_phone=phone,
            sender_name=sender_name,
            message_type="text",
            text_content="Hi",
            raw_text="Hi",
            raw_payload={"from": phone, "type": "text"}
        )
        await message_handler.process_incoming_message(db, parsed)
        outbox = whatsapp_service.get_outbox(phone)
        for msg in outbox:
            display_bot_message(msg)
        whatsapp_service.clear_outbox(phone)

    # Chat loop
    while True:
        try:
            user_input = input(f"👤 {sender_name} > ").strip()
            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit", "q"]:
                print("\n[Simulator Session Terminated. Goodbye!]")
                break

            async with AsyncSessionLocal() as db:
                whatsapp_service.clear_outbox(phone)
                parsed = ParsedMessage(
                    message_id=f"wamid.cli_{asyncio.get_event_loop().time()}",
                    sender_phone=phone,
                    sender_name=sender_name,
                    message_type="text",
                    text_content=user_input,
                    raw_text=user_input,
                    raw_payload={"from": phone, "type": "text", "body": user_input}
                )
                await message_handler.process_incoming_message(db, parsed)

                # Fetch bot replies
                outbox = whatsapp_service.get_outbox(phone)
                for msg in outbox:
                    display_bot_message(msg)
                whatsapp_service.clear_outbox(phone)

                # Show state info
                res_user = await db.execute(select(User).where(User.phone_number == phone))
                u = res_user.scalar_one_or_none()
                if u:
                    res_c = await db.execute(select(Conversation).where(Conversation.user_id == u.id))
                    c = res_c.scalar_one_or_none()
                    if c:
                        print(f"📊 [Current State: {c.state} | Status: {c.status}]")

        except KeyboardInterrupt:
            print("\n[Exiting...]")
            break
        except Exception as e:
            print(f"\n❌ Error during execution: {e}")


if __name__ == "__main__":
    asyncio.run(run_cli())
