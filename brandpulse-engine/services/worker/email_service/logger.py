"""
Email Logger - Database Logging for Email Delivery
==================================================
Tracks all email attempts in EmailLog table
"""

from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from services.shared.models import Company, GeneratedIdea, EmailLog, EmailTypeEnum


def log_email_delivery(
    session: Session,
    company: Company,
    email_type: EmailTypeEnum,
    subject: str,
    success: bool,
    insight: Optional[GeneratedIdea] = None,
    message_id: Optional[str] = None,
    error_message: Optional[str] = None
):
    """
    Log email delivery attempt to database.
    
    Args:
        session: Database session
        company: Company recipient
        email_type: INSIGHT or APOLOGY
        subject: Email subject line
        success: Whether email was sent successfully
        insight: Related insight (None for apology emails)
        message_id: Resend message ID (or 'DEV_MODE')
        error_message: Error details if failed
    """
    email_log = EmailLog(
        company_id=company.id,
        insight_id=insight.id if insight else None,
        email_type=email_type,
        recipient_email=company.email,
        subject=subject,
        sent_successfully=success,
        sendgrid_message_id=message_id,
        error_message=error_message,
        sent_at=datetime.utcnow()
    )
    
    session.add(email_log)
    session.commit()