import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models import User, Conversation, Message, Lead
from app.services.whatsapp import whatsapp_service
from app.services.message_parser import ParsedMessage
from app.services.message_handler import message_handler
from app.core.config import get_settings

settings = get_settings()
router = APIRouter(tags=["Testing & WhatsApp Simulator"])


class SimulatorSendRequest(BaseModel):
    phone_number: str = "919940048776"
    sender_name: Optional[str] = "Akash Kumar"
    message_text: str
    message_type: str = "text"  # text, interactive_button, interactive_list
    selection_id: Optional[str] = None


@router.post("/api/simulator/send", summary="Simulate Inbound WhatsApp Message")
async def simulator_send_message(
    req: SimulatorSendRequest,
    db: AsyncSession = Depends(get_db)
):
    """Simulates receiving a WhatsApp message without Meta Cloud API or webhook setup."""
    clean_phone = req.phone_number.replace("+", "").strip()
    msg_id = f"wamid.sim_{int(time.time()*1000)}"

    raw_payload = {
        "from": clean_phone,
        "id": msg_id,
        "timestamp": str(int(time.time())),
        "type": "text" if req.message_type == "text" else "interactive"
    }

    parsed_msg = ParsedMessage(
        message_id=msg_id,
        sender_phone=clean_phone,
        sender_name=req.sender_name,
        message_type=req.message_type,
        text_content=req.selection_id or req.message_text,
        raw_text=req.message_text,
        selection_id=req.selection_id,
        raw_payload=raw_payload
    )

    await message_handler.process_incoming_message(db, parsed_msg)

    # Get latest conversation state
    res_user = await db.execute(select(User).where(User.phone_number == clean_phone))
    user = res_user.scalar_one_or_none()

    state = "MAIN_MENU"
    session_data = {}
    if user:
        res_conv = await db.execute(
            select(Conversation).where(Conversation.user_id == user.id).order_by(Conversation.id.desc())
        )
        conv = res_conv.scalars().first()
        if conv:
            state = conv.state
            session_data = conv.session_data or {}

    outbox = whatsapp_service.get_outbox(clean_phone)

    return {
        "status": "success",
        "simulated_message_id": msg_id,
        "conversation_state": state,
        "session_data": session_data,
        "latest_bot_replies": outbox[-3:] if outbox else [],
    }


@router.get("/api/simulator/chat/{phone}", summary="Get Simulator Chat Transcript and State")
async def simulator_get_chat(
    phone: str,
    db: AsyncSession = Depends(get_db)
):
    clean_phone = phone.replace("+", "").strip()

    res_user = await db.execute(select(User).where(User.phone_number == clean_phone))
    user = res_user.scalar_one_or_none()

    if not user:
        return {
            "user": None,
            "conversation": None,
            "messages": [],
            "outbox": [],
            "leads": []
        }

    res_conv = await db.execute(
        select(Conversation).where(Conversation.user_id == user.id).order_by(Conversation.id.desc())
    )
    conv = res_conv.scalars().first()

    db_messages = []
    if conv:
        res_msgs = await db.execute(
            select(Message).where(Message.conversation_id == conv.id).order_by(Message.created_at.asc())
        )
        db_messages = res_msgs.scalars().all()

    res_leads = await db.execute(
        select(Lead).where(Lead.phone_number == clean_phone).order_by(Lead.id.desc())
    )
    leads = res_leads.scalars().all()

    outbox = whatsapp_service.get_outbox(clean_phone)

    return {
        "user": {
            "id": user.id,
            "name": user.name,
            "phone_number": user.phone_number,
        },
        "conversation": {
            "id": conv.id if conv else None,
            "state": conv.state if conv else "MAIN_MENU",
            "previous_state": conv.previous_state if conv else None,
            "status": conv.status if conv else "ACTIVE",
            "session_data": conv.session_data if conv else {},
        } if conv else None,
        "db_messages": [
            {
                "id": m.id,
                "direction": m.direction,
                "type": m.message_type,
                "text": m.message_text,
                "raw_payload": m.raw_payload,
                "created_at": m.created_at.isoformat() if m.created_at else None
            } for m in db_messages
        ],
        "outbox": outbox,
        "leads": [
            {
                "id": l.id,
                "name": l.name,
                "business_type": l.business_type,
                "requirement": l.requirement,
                "timeline": l.timeline,
                "budget": l.budget,
                "estimated_amount": l.estimated_amount,
                "preferred_contact_time": l.preferred_contact_time,
                "email": l.email,
                "status": l.status,
                "created_at": l.created_at.isoformat() if l.created_at else None
            } for l in leads
        ]
    }



@router.post("/api/simulator/reset/{phone}", summary="Reset Simulator User & Conversation")
async def simulator_reset_chat(
    phone: str,
    db: AsyncSession = Depends(get_db)
):
    clean_phone = phone.replace("+", "").strip()

    res_user = await db.execute(select(User).where(User.phone_number == clean_phone))
    user = res_user.scalar_one_or_none()

    if user:
        # Clean up leads for this test user
        await db.execute(delete(Lead).where(Lead.phone_number == clean_phone))
        await db.execute(delete(Lead).where(Lead.user_id == user.id))

        res_conv = await db.execute(
            select(Conversation).where(Conversation.user_id == user.id)
        )
        for conv in res_conv.scalars().all():
            conv.state = "MAIN_MENU"
            conv.status = "ACTIVE"
            conv.session_data = {}
            # Clean up messages
            await db.execute(delete(Message).where(Message.conversation_id == conv.id))
        await db.commit()
    else:
        await db.execute(delete(Lead).where(Lead.phone_number == clean_phone))
        await db.commit()

    whatsapp_service.clear_outbox(clean_phone)
    return {"status": "reset_successful", "phone": clean_phone}


class SimulatorForwardEmailReq(BaseModel):
    target_email: Optional[str] = None

@router.post("/api/simulator/lead/{lead_id}/forward-email", summary="Forward Lead Form to Any Email")
async def simulator_forward_lead_email(
    lead_id: int,
    req: SimulatorForwardEmailReq,
    db: AsyncSession = Depends(get_db)
):
    """Forward a completed lead form summary to any target email address."""
    from app.services.email_service import email_service
    res = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = res.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

    return await email_service.send_lead_notification(lead, target_email=req.target_email)


TEMPLATE_PATH = Path(__file__).parent.parent / "templates" / "simulator.html"

@router.get("/simulator", response_class=HTMLResponse, summary="WhatsApp Web Simulator UI")
async def simulator_web_ui():
    """Renders an interactive WhatsApp Web simulation UI for testing without Meta credentials."""
    if not TEMPLATE_PATH.exists():
        raise HTTPException(status_code=500, detail="Simulator UI template not found")
    html_content = TEMPLATE_PATH.read_text(encoding="utf-8")
    return HTMLResponse(
        content=html_content,
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )

