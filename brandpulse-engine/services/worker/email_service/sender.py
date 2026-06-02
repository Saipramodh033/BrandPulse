"""
Email Sender - Resend Integration
=================================
Sends emails using Jinja2 templates from templates/ folder
"""

import os
import logging
from datetime import datetime
from sqlalchemy.orm import Session

import resend
from jinja2 import Environment, FileSystemLoader
import markdown

from services.shared.models import Company, GeneratedIdea, EmailTypeEnum
from services.worker.email_service.logger import log_email_delivery

logger = logging.getLogger(__name__)

# Initialize Jinja2 (points to templates/ folder)
template_dir = os.path.join(os.path.dirname(__file__), '../../../templates')
jinja_env = Environment(loader=FileSystemLoader(template_dir))


def markdown_to_html(markdown_text: str) -> str:
    """Convert Markdown to HTML"""
    return markdown.markdown(
        markdown_text,
        extensions=['extra', 'codehilite', 'tables']
    )


def should_send_emails() -> bool:
    """Check if emails should be sent (dev mode flag)"""
    return os.getenv('SEND_EMAILS', 'false').lower() == 'true'


def init_resend_client():
    """Initialize Resend API client"""
    api_key = os.getenv('RESEND_API_KEY')
    if not api_key:
        raise ValueError("RESEND_API_KEY not configured")
    resend.api_key = api_key


def send_insight_email(insight: GeneratedIdea, company: Company, session: Session) -> bool:
    """
    Send approved insight to company email.
    
    Args:
        insight: Approved insight
        company: Company recipient
        session: Database session
        
    Returns:
        True if sent successfully
    """
    logger.info(f"📧 Preparing insight email for {company.email}")
    
    # Render Jinja2 template
    try:
        template = jinja_env.get_template('insight_email.html')
        html_content = template.render(
            company_name=company.name,
            content_html=markdown_to_html(insight.full_content),
            insight_id=insight.id,
            generated_date=insight.created_at.strftime('%B %d, %Y')
        )
    except Exception as e:
        logger.error(f"❌ Template rendering failed: {e}")
        return False
    
    subject = f"Market Intelligence - {datetime.utcnow().strftime('%B %d, %Y')}"
    from_email = os.getenv('RESEND_FROM_EMAIL', 'noreply@brandpulse.ai')
    
    # Dev mode: Skip actual sending
    if not should_send_emails():
        logger.info("⚠️ SEND_EMAILS=false - Logging only (dev mode)")
        log_email_delivery(
            session=session,
            company=company,
            insight=insight,
            email_type=EmailTypeEnum.INSIGHT,
            subject=subject,
            success=True,
            message_id="DEV_MODE_SKIP"
        )
        return True
    
    # Send via Resend
    try:
        init_resend_client()
        
        response = resend.Emails.send({
            "from": from_email,
            "to": company.email,
            "subject": subject,
            "html": html_content
        })
        
        # Resend returns {"id": "message_id"} on success
        success = response and 'id' in response
        message_id = response.get('id', 'unknown') if success else None
        
        log_email_delivery(
            session=session,
            company=company,
            insight=insight,
            email_type=EmailTypeEnum.INSIGHT,
            subject=subject,
            success=success,
            message_id=message_id
        )
        
        if success:
            logger.info(f"✅ Email sent to {company.email} (ID: {message_id})")
        else:
            logger.error(f"❌ Resend API failed")
        
        return success
        
    except Exception as e:
        logger.error(f"❌ Email send exception: {e}")
        log_email_delivery(
            session=session,
            company=company,
            insight=insight,
            email_type=EmailTypeEnum.INSIGHT,
            subject=subject,
            success=False,
            error_message=str(e)
        )
        return False


def send_apology_email(company: Company, reason: str, session: Session) -> bool:
    """
    Send apology email for auto-rejected insight.
    
    Args:
        company: Company recipient
        reason: Reason for apology
        session: Database session
        
    Returns:
        True if sent successfully
    """
    logger.info(f"📧 Preparing apology email for {company.email}")
    
    # Render template
    try:
        template = jinja_env.get_template('apology_email.html')
        html_content = template.render(
            company_name=company.name,
            reason=reason,
            next_run_time=company.next_run_time.strftime('%B %d at %H:%M UTC')
        )
    except Exception as e:
        logger.error(f"❌ Template rendering failed: {e}")
        return False
    
    subject = "Apology - Delayed Insight Review"
    from_email = os.getenv('RESEND_FROM_EMAIL', 'noreply@brandpulse.ai')
    
    # Dev mode
    if not should_send_emails():
        logger.info("⚠️ SEND_EMAILS=false - Logging only")
        log_email_delivery(
            session=session,
            company=company,
            insight=None,
            email_type=EmailTypeEnum.APOLOGY,
            subject=subject,
            success=True,
            message_id="DEV_MODE_SKIP"
        )
        return True
    
    # Send via Resend
    try:
        init_resend_client()
        
        response = resend.Emails.send({
            "from": from_email,
            "to": company.email,
            "subject": subject,
            "html": html_content
        })
        
        success = response and 'id' in response
        message_id = response.get('id') if success else None
        
        log_email_delivery(
            session=session,
            company=company,
            insight=None,
            email_type=EmailTypeEnum.APOLOGY,
            subject=subject,
            success=success,
            message_id=message_id
        )
        
        if success:
            logger.info(f"✅ Apology sent to {company.email} (ID: {message_id})")
        else:
            logger.error(f"❌ Resend API failed")
        
        return success
        
    except Exception as e:
        logger.error(f"❌ Apology send exception: {e}")
        log_email_delivery(
            session=session,
            company=company,
            insight=None,
            email_type=EmailTypeEnum.APOLOGY,
            subject=subject,
            success=False,
            error_message=str(e)
        )
        return False