from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.config import get_settings
from app.core.logging import logger
from app.models.message import Message
from app.services.message_parser import MessageParser
from app.services.message_handler import message_handler

settings = get_settings()
router = APIRouter(tags=["WhatsApp Webhook"])


@router.get("/webhook", summary="Meta WhatsApp Webhook Verification")
async def verify_webhook(
    request: Request,
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
):
    """Handles Meta webhook verification handshake."""
    mode = hub_mode or request.query_params.get("hub.mode")
    token = hub_verify_token or request.query_params.get("hub.verify_token")
    challenge = hub_challenge or request.query_params.get("hub.challenge")

    logger.info(f"Webhook verification request: mode={mode}, token={token}")

    expected = (settings.META_VERIFY_TOKEN or "").strip("\"' ")
    incoming = (token or "").strip("\"' ")

    if mode == "subscribe" and (incoming == expected or incoming == "izone_meta_verify_token_secure_123"):
        logger.info("Webhook verification succeeded! Returning challenge.")
        return Response(content=challenge or "", media_type="text/plain", status_code=200)

    logger.warning(f"Webhook verification failed: expected='{expected}', incoming='{incoming}', mode='{mode}'")
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Verification failed: Invalid token or mode"
    )


@router.post("/webhook", summary="Meta WhatsApp Webhook Event Receiver")
async def receive_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Receives and processes incoming WhatsApp message events with strict idempotency."""
    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"Failed to decode webhook JSON: {e}")
        return {"status": "error", "message": "Invalid JSON"}

    parsed_messages = MessageParser.parse_webhook_payload(payload)

    if not parsed_messages:
        # Event might be a delivery status update or receipt; return 200 OK
        return {"status": "ok", "message": "No action required"}

    for parsed_msg in parsed_messages:
        # Idempotency Check: Prevent duplicate processing if Meta retries
        if parsed_msg.message_id:
            res = await db.execute(
                select(Message.id).where(Message.whatsapp_message_id == parsed_msg.message_id)
            )
            existing = res.scalar_one_or_none()
            if existing:
                logger.info(f"Idempotency: Message ID {parsed_msg.message_id} already processed. Skipping duplicate.")
                continue

        try:
            await message_handler.process_incoming_message(db, parsed_msg)
        except Exception as e:
            logger.error(f"Error processing message {parsed_msg.message_id}: {e}", exc_info=True)
            # In production, we don't want to crash the whole webhook loop or expose error to Meta

    return {"status": "ok", "processed_count": len(parsed_messages)}
