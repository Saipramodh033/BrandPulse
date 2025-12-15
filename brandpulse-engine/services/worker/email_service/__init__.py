"""
Email Service Package
====================
SendGrid email service (renamed to avoid conflict with built-in email module)
"""

from services.worker.email_service.sender import send_insight_email, send_apology_email

__all__ = ['send_insight_email', 'send_apology_email']