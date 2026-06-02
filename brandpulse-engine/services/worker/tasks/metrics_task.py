"""
Task: Update System Metrics
===========================
Calculate and update global statistics
"""

import logging
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.orm import Session

from services.shared.models import Metric, GeneratedIdea, EmailLog, EmailTypeEnum

logger = logging.getLogger(__name__)


def update_system_metrics(session: Session):
    """Update global metrics table"""
    logger.info("📊 Updating system metrics...")
    
    try:
        # Get or create metrics row
        metric = session.query(Metric).first()
        if not metric:
            metric = Metric()
            session.add(metric)
        
        # Count insights by status
        total_insights = session.query(GeneratedIdea).count()
        pending_count = session.query(GeneratedIdea).filter(
            GeneratedIdea.status == 'pending'
        ).count()
        approved_count = session.query(GeneratedIdea).filter(
            GeneratedIdea.status == 'approved'
        ).count()
        rejected_count = session.query(GeneratedIdea).filter(
            GeneratedIdea.status == 'rejected'
        ).count()
        
        # Average processing time
        avg_time = session.execute(
            text("SELECT AVG(processing_time) FROM insights WHERE processing_time IS NOT NULL")
        ).scalar()
        avg_processing_time = float(avg_time) if avg_time else 0.0
        
        # Total tokens
        total_tokens = session.execute(
            text("SELECT SUM(token_count) FROM insights WHERE token_count IS NOT NULL")
        ).scalar() or 0
        
        # Email counts
        total_emails = session.query(EmailLog).filter(
            EmailLog.email_type == EmailTypeEnum.INSIGHT,
            EmailLog.sent_successfully == True
        ).count()
        
        total_apology_emails = session.query(EmailLog).filter(
            EmailLog.email_type == EmailTypeEnum.APOLOGY,
            EmailLog.sent_successfully == True
        ).count()
        
        # Update metric
        metric.total_insights = total_insights
        metric.pending_count = pending_count
        metric.approved_count = approved_count
        metric.rejected_count = rejected_count
        metric.avg_processing_time = avg_processing_time
        metric.total_tokens_used = total_tokens
        metric.total_emails_sent = total_emails
        metric.total_apology_emails = total_apology_emails
        metric.last_scheduler_run = datetime.utcnow()
        metric.last_updated = datetime.utcnow()
        
        session.commit()
        
        logger.info(
            f"✅ Metrics: {total_insights} total, "
            f"{pending_count} pending, {approved_count} approved"
        )
        
    except Exception as e:
        logger.error(f"❌ Error updating metrics: {e}")
        session.rollback()