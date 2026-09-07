import asyncio
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, Optional, Union

from app.core.config import get_settings
from app.core.logging import logger
from app.models import Lead

settings = get_settings()


class EmailService:
    @staticmethod
    def format_lead_email_html(
        lead_id: int,
        name: str,
        phone_number: str,
        email: Optional[str] = None,
        business_type: Optional[str] = None,
        service_name: Optional[str] = None,
        requirement: Optional[str] = None,
        timeline: Optional[str] = None,
        budget: Optional[str] = None,
        estimated_amount: Optional[str] = None,
        preferred_contact_time: Optional[str] = None,
        status: str = "NEW",
        source: str = "WHATSAPP_BOT",
        created_at: Optional[datetime] = None
    ) -> str:
        """Format HTML email template containing all completed lead form fields."""
        clean_phone = (phone_number or "").replace("+", "").replace(" ", "").strip()
        wa_link = f"https://wa.me/{clean_phone}" if clean_phone else "#"
        created_str = created_at.strftime("%d-%b-%Y %I:%M %p") if created_at and hasattr(created_at, 'strftime') else datetime.now().strftime("%d-%b-%Y %I:%M %p")
        srv_name = service_name or "Custom Technology Solution"

        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: 'Segoe UI', Helvetica, Arial, sans-serif; background-color: #0f172a; margin: 0; padding: 20px; color: #f8fafc; }}
        .container {{ max-width: 620px; background: #1e293b; border-radius: 12px; overflow: hidden; box-shadow: 0 10px 25px rgba(0,0,0,0.5); margin: 0 auto; border: 1px solid #334155; }}
        .header {{ background: #00a884; color: #111b21; padding: 24px; text-align: center; font-weight: bold; }}
        .header h2 {{ margin: 0; font-size: 22px; color: #0b141a; }}
        .badge-bar {{ text-align: center; padding: 10px 20px; background: #0b141a; border-bottom: 1px solid #334155; }}
        .badge {{ background: #00a884; color: #111b21; display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; margin: 2px 4px; }}
        .badge-outline {{ background: #1e293b; color: #94a3b8; border: 1px solid #475569; display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; margin: 2px 4px; }}
        .content {{ padding: 24px; }}
        .field-card {{ background: #0f172a; border-left: 4px solid #00a884; padding: 12px 16px; margin-bottom: 12px; border-radius: 6px; border: 1px solid #1e293b; }}
        .field-title {{ font-size: 11px; text-transform: uppercase; color: #94a3b8; font-weight: bold; margin-bottom: 4px; letter-spacing: 0.5px; }}
        .field-value {{ font-size: 15px; font-weight: 600; color: #f8fafc; line-height: 1.5; }}
        .whatsapp-btn {{ display: block; width: 100%; text-align: center; background: #25D366; color: #ffffff; text-decoration: none; padding: 12px 0; border-radius: 8px; font-weight: bold; font-size: 15px; margin-top: 16px; box-shadow: 0 4px 12px rgba(37,211,102,0.3); }}
        .footer {{ background: #0f172a; padding: 16px; text-align: center; font-size: 12px; color: #64748b; border-top: 1px solid #334155; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>🚀 iZone Technologies — Customer Lead Form</h2>
        </div>
        <div class="badge-bar">
            <span class="badge">#LEAD-{lead_id:04d}</span>
            <span class="badge-outline">Status: {status}</span>
            <span class="badge-outline">Source: {source}</span>
        </div>
        <div class="content">
            <div class="field-card">
                <div class="field-title">📅 Submission Timestamp</div>
                <div class="field-value">{created_str}</div>
            </div>
            <div class="field-card">
                <div class="field-title">👤 Client Name</div>
                <div class="field-value">{name or 'N/A'}</div>
            </div>
            <div class="field-card">
                <div class="field-title">💼 Business / Organization Name</div>
                <div class="field-value">{business_type or 'N/A'}</div>
            </div>
            <div class="field-card">
                <div class="field-title">🛠️ Service Category</div>
                <div class="field-value" style="color:#00a884;">{srv_name}</div>
            </div>
            <div class="field-card">
                <div class="field-title">📝 Detailed Project Requirement</div>
                <div class="field-value">{requirement or 'N/A'}</div>
            </div>
            <div class="field-card">
                <div class="field-title">⏳ Target Launch Timeline</div>
                <div class="field-value">{timeline or 'Standard (1 Month)'}</div>
            </div>
            <div class="field-card">
                <div class="field-title">💰 Budget Preference</div>
                <div class="field-value">{budget or 'Flexible'}</div>
            </div>
            <div class="field-card">
                <div class="field-title">🏷️ Estimated Quote Scope</div>
                <div class="field-value" style="color:#00a884; font-size:17px;">{estimated_amount or 'Custom Quote'}</div>
            </div>
            <div class="field-card">
                <div class="field-title">📞 Contact Phone Number</div>
                <div class="field-value">{phone_number}</div>
            </div>
            <div class="field-card">
                <div class="field-title">✉️ Email Address</div>
                <div class="field-value">{email or 'Not provided'}</div>
            </div>
            <div class="field-card">
                <div class="field-title">🕒 Best Calling / Discussion Slot</div>
                <div class="field-value">{preferred_contact_time or 'Business Hours (10 AM - 6:30 PM)'}</div>
            </div>

            <a href="{wa_link}" target="_blank" class="whatsapp-btn">💬 Chat Directly on WhatsApp ({phone_number})</a>
        </div>
        <div class="footer">
            Dispatched via <b>iZone Technologies WhatsApp Business Automation Platform</b>
        </div>
    </div>
</body>
</html>
"""

    @staticmethod
    async def send_lead_notification(
        lead_or_id: Optional[Union[Lead, int]] = None,
        lead_id: Optional[int] = None,
        name: Optional[str] = None,
        phone_number: Optional[str] = None,
        email: Optional[str] = None,
        business_type: Optional[str] = None,
        service_name: Optional[str] = None,
        requirement: Optional[str] = None,
        timeline: Optional[str] = None,
        budget: Optional[str] = None,
        estimated_amount: Optional[str] = None,
        preferred_contact_time: Optional[str] = None,
        status: str = "NEW",
        source: str = "WHATSAPP_BOT",
        target_email: Optional[str] = None,
        created_at: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Dispatch lead notification email to configured admin email or custom recipient."""
        # Support passing a Lead model object directly or passing fields
        if isinstance(lead_or_id, Lead):
            lead = lead_or_id
            lid = lead.id
            lname = lead.name
            lphone = lead.phone_number
            lemail = lead.email
            lbusiness = lead.business_type
            lsrv = service_name or (getattr(lead, "service_name", None) if hasattr(lead, "service_name") else None)
            lreq = lead.requirement
            ltime = lead.timeline
            lbudget = lead.budget
            lest = lead.estimated_amount
            lpref = lead.preferred_contact_time
            lstatus = lead.status
            lsrc = lead.source
            lcreated = lead.created_at
        else:
            lid = lead_id or (int(lead_or_id) if lead_or_id is not None else 0)
            lname = name or "Valued Client"
            lphone = phone_number or "N/A"
            lemail = email
            lbusiness = business_type
            lsrv = service_name
            lreq = requirement
            ltime = timeline
            lbudget = budget
            lest = estimated_amount
            lpref = preferred_contact_time
            lstatus = status
            lsrc = source
            lcreated = created_at

        recipient = target_email or settings.NOTIFICATION_EMAIL or settings.COMPANY_EMAIL or "info@izonetech.in"
        subject = f"NEW LEAD [#LEAD-{lid:04d}]: {lname} ({lbusiness or 'Inquiry'})"

        html_body = EmailService.format_lead_email_html(
            lead_id=lid,
            name=lname,
            phone_number=lphone,
            email=lemail,
            business_type=lbusiness,
            service_name=lsrv,
            requirement=lreq,
            timeline=ltime,
            budget=lbudget,
            estimated_amount=lest,
            preferred_contact_time=lpref,
            status=lstatus,
            source=lsrc,
            created_at=lcreated
        )

        logger.info(f"Preparing lead email notification for #LEAD-{lid:04d} to recipient: {recipient}")

        if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
            logger.info(f"[SIMULATED EMAIL DISPATCH] Lead #LEAD-{lid:04d} forwarded to {recipient} (No SMTP credentials)")
            return {
                "status": "sent_simulated",
                "recipient": recipient,
                "lead_id": lid,
                "subject": subject,
                "message": f"Lead #LEAD-{lid:04d} form successfully forwarded to {recipient}"
            }

        try:
            def _send():
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = settings.SMTP_USER
                msg["To"] = recipient
                msg.attach(MIMEText(html_body, "html"))

                with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15.0) as server:
                    server.starttls()
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                    server.sendmail(settings.SMTP_USER, [recipient], msg.as_string())

            await asyncio.to_thread(_send)
            logger.info(f"Successfully dispatched lead email for #LEAD-{lid:04d} to {recipient}")
            return {
                "status": "sent_success",
                "recipient": recipient,
                "lead_id": lid,
                "message": f"Lead #LEAD-{lid:04d} form successfully emailed to {recipient}"
            }

        except Exception as e:
            logger.error(f"Failed to send email notification for #LEAD-{lid:04d}: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "recipient": recipient,
                "lead_id": lid
            }


email_service = EmailService()
