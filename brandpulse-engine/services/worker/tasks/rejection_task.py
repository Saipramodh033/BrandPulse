"""
Task: Auto-Reject Expired Pending Insights
==========================================
Finds insights that exceeded review window and sends apology emails
"""

import logging
from datetime import datetime
from sqlalchemy.orm import Session

from services.shared.models import GeneratedIdea
from services.worker.email_service.sender import send_apology_email  # ← UPDATED IMPORT
from services.worker.utils.time import is_insight_expired

logger = logging.getLogger(__name__)


def auto_reject_expired_insights(session: Session) -> int:
    """
    Find and auto-reject expired pending insights.
    
    Returns:
        Number of insights rejected
    """
    logger.info("🔍 Checking for expired pending insights...")
    
    try:
        pending_insights = session.query(GeneratedIdea).filter(
            GeneratedIdea.status == 'pending'
        ).all()
        
        rejected_count = 0
        
        for insight in pending_insights:
            company = insight.company
            
            if is_insight_expired(insight, company):
                logger.warning(
                    f"⏰ Auto-rejecting insight #{insight.id} for {company.name}"
                )
                
                # Update insight
                insight.status = 'rejected'
                insight.admin_feedback = (
                    f"AUTO-REJECTED: Review not completed within "
                    f"{company.frequency_hours}h window (created {insight.created_at})"
                )
                insight.updated_at = datetime.utcnow()
                
                # Send apology
                try:
                    send_apology_email(
                        company=company,
                        reason=f"Review delayed for insight scheduled {insight.created_at.strftime('%B %d, %Y')}",
                        session=session
                    )
                    logger.info(f"📧 Apology sent to {company.email}")
                except Exception as e:
                    logger.error(f"❌ Failed to send apology: {e}")
                
                rejected_count += 1
        
        session.commit()
        
        if rejected_count > 0:
            logger.info(f"✅ Auto-rejected {rejected_count} insight(s)")
        else:
            logger.info("✅ No expired insights")
        
        return rejected_count
        
    except Exception as e:
        logger.error(f"❌ Error in rejection task: {e}")
        session.rollback()
        return 0