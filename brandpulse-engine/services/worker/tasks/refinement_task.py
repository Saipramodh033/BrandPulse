"""
Task: Process Refinement Requests
=================================
Regenerate insights with admin feedback
"""

import logging
from datetime import datetime
from sqlalchemy.orm import Session

from services.shared.models import Insight, InsightStatusEnum
from services.worker.agent.core import refine_insight

logger = logging.getLogger(__name__)


def process_refinement_requests(session: Session) -> int:
    """
    Process insights with status=REFINING.
    
    Returns:
        Number of insights refined
    """
    logger.info("🔄 Checking for refinement requests...")
    
    try:
        refining_insights = session.query(Insight).filter(
            Insight.status == InsightStatusEnum.REFINING
        ).all()
        
        if not refining_insights:
            logger.info("✅ No refinement requests")
            return 0
        
        refined_count = 0
        
        for insight in refining_insights:
            company = insight.company
            logger.info(f"🔧 Refining insight #{insight.id} for {company.name}")
            
            try:
                # Generate refined version
                new_content, processing_time, token_count = refine_insight(
                    company=company,
                    previous_content=insight.content,
                    admin_feedback=insight.admin_feedback,
                    session=session
                )
                
                # Update insight
                insight.content = new_content
                insight.status = InsightStatusEnum.PENDING
                insight.processing_time = processing_time
                insight.token_count = token_count
                insight.updated_at = datetime.utcnow()
                
                logger.info(f"✅ Refined insight #{insight.id}")
                refined_count += 1
                
            except Exception as e:
                logger.error(f"❌ Failed to refine insight #{insight.id}: {e}")
                continue
        
        session.commit()
        logger.info(f"✅ Processed {refined_count} refinement(s)")
        
        return refined_count
        
    except Exception as e:
        logger.error(f"❌ Error in refinement task: {e}")
        session.rollback()
        return 0