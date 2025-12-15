"""
Task: Generate New Insights
===========================
Find companies due for processing and generate insights
"""

import logging
from datetime import datetime
from sqlalchemy.orm import Session

from services.shared.models import Company, Insight, CompanyStatusEnum, InsightStatusEnum
from services.worker.agent.core import generate_insight
from services.worker.utils.time import calculate_next_run_time

logger = logging.getLogger(__name__)


def generate_new_insights(session: Session) -> int:
    """
    Generate insights for companies with next_run_time <= now.
    
    Returns:
        Number of insights generated
    """
    logger.info("🔍 Checking for companies due for processing...")
    
    try:
        due_companies = session.query(Company).filter(
            Company.status == CompanyStatusEnum.ACTIVE,
            Company.next_run_time <= datetime.utcnow()
        ).all()
        
        if not due_companies:
            logger.info("✅ No companies due")
            return 0
        
        logger.info(f"📋 Found {len(due_companies)} company(ies)")
        
        generated_count = 0
        
        for company in due_companies:
            logger.info(f"🏢 Processing {company.name}")
            
            # Check pending limit (1 per company)
            pending_count = session.query(Insight).filter(
                Insight.company_id == company.id,
                Insight.status == InsightStatusEnum.PENDING
            ).count()
            
            if pending_count > 0:
                logger.warning(f"⏭️ Skipping {company.name} (has pending insight)")
                company.next_run_time = calculate_next_run_time(
                    datetime.utcnow(),
                    company.frequency_hours
                )
                continue
            
            # Generate insight
            try:
                content, processing_time, token_count = generate_insight(
                    company=company,
                    session=session
                )
                
                # Create record
                new_insight = Insight(
                    company_id=company.id,
                    content=content,
                    status=InsightStatusEnum.PENDING,
                    processing_time=processing_time,
                    token_count=token_count,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                session.add(new_insight)
                
                # Update next run time
                company.next_run_time = calculate_next_run_time(
                    datetime.utcnow(),
                    company.frequency_hours
                )
                
                logger.info(f"✅ Generated insight #{new_insight.id}")
                logger.info(f"⏰ Next run: {company.next_run_time}")
                
                generated_count += 1
                
            except Exception as e:
                logger.error(f"❌ Failed for {company.name}: {e}")
                continue
        
        session.commit()
        logger.info(f"✅ Generated {generated_count} insight(s)")
        
        return generated_count
        
    except Exception as e:
        logger.error(f"❌ Error in generation task: {e}")
        session.rollback()
        return 0