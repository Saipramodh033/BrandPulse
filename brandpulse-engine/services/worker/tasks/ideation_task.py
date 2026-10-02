"""
Celery Task: Ideation
=====================
Dispatches and runs the ideation graph for companies asynchronously.
"""

import json
import logging
from datetime import datetime
from celery import shared_task

from sqlalchemy.orm import Session
from services.shared.database import get_db_session
from services.shared.models import (
    Company, GeneratedIdea, RunLog,
    CompanyStatusEnum, IdeaStatusEnum,
)
from services.worker.agent.core import run_ideation_v4
from services.worker.utils.time import calculate_next_run_time

import redis
import os

logger = logging.getLogger(__name__)
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")


@shared_task
def queue_generation_tasks():
    """
    Celery Beat task: Finds due companies and dispatches a Celery task for each.
    """
    logger.info("🔍 Checking for companies due for processing...")
    
    try:
        redis_client = redis.from_url(redis_url)
        lock = redis_client.lock("queue_generation_tasks_lock", timeout=55)
        if not lock.acquire(blocking=False):
            logger.info("⏭️ Previous queue task still running, skipping")
            return 0
    except Exception as e:
        logger.warning(f"⚠️ Redis lock failed, proceeding without lock: {e}")
        lock = None
        
    try:
        with get_db_session() as session:
            # Find companies that are active, due, and not already processing
            due_companies = session.query(Company).filter(
                Company.status == CompanyStatusEnum.ACTIVE,
                Company.next_run_time <= datetime.utcnow(),
                Company.is_processing == False
            ).all()
    
            if not due_companies:
                logger.info("✅ No companies due")
                return 0
    
            logger.info(f"📋 Found {len(due_companies)} company(ies) due for ideation")
            
            for company in due_companies:
                # Lock the company
                company.is_processing = True
            session.commit()
            
            for company in due_companies:
                # Dispatch background task
                process_company_ideation.delay(company.id)
                logger.info(f"🚀 Dispatched task for company {company.name}")
                
            return len(due_companies)
    finally:
        if lock:
            try:
                lock.release()
            except Exception:
                pass


@shared_task(bind=True, max_retries=3)
def process_company_ideation(self, company_id: int):
    """
    Celery Worker task: Executes autonomous ReAct ideation for a single company,
    handling WebSocket progress notifications, quality-pruned empty runs, and managed retries.
    """
    with get_db_session() as session:
        company = session.query(Company).filter(Company.id == company_id).first()
        
        if not company:
            logger.error(f"❌ Company {company_id} not found")
            return
            
        logger.info(f"🏢 Processing {company.name} in background task")

        try:
            # Guard: skip if ideas already pending review or currently rewriting
            pending_count = session.query(GeneratedIdea).filter(
                GeneratedIdea.company_id == company.id,
                GeneratedIdea.status.in_([IdeaStatusEnum.PENDING.value, IdeaStatusEnum.REFINING.value])
            ).count()

            if pending_count > 0:
                logger.warning(f"⏭️ Skipping {company.name} ({pending_count} ideas pending or refining)")
                _unlock_and_reschedule(session, company)
                return

            ideas, final_state = run_ideation_v4(company=company, session=session)

            # Save RunLog trace
            run_log = RunLog(
                company_id=company.id,
                status="error" if final_state.get("error") else "success",
                trace={
                    "nodes": final_state.get("trace_events", []),
                    "search_query": final_state.get("search_query", ""),
                    "search_results": final_state.get("search_results", []),
                    "signal": final_state.get("signal"),
                    "signal_strength": final_state.get("signal_strength", "none"),
                    "chosen_angle": final_state.get("chosen_angle"),
                    "evergreen": final_state.get("evergreen", False),
                    "ideas_generated": len(ideas),
                },
                created_at=datetime.utcnow()
            )
            session.add(run_log)
            session.flush()

            if not ideas:
                logger.warning(f"⚠️ 0 ideas survived validation for {company.name}. Saving empty RunLog.")
                # Save empty run log so run history shows what happened
                empty_run = RunLog(
                    company_id=company.id,
                    status="empty",
                    trace={
                        "nodes": final_state.get("trace_events", []),
                        "error": "No ideas survived quality validation",
                        "ideas_generated": 0,
                    },
                    created_at=datetime.utcnow()
                )
                session.add(empty_run)
                session.flush()
                _unlock_and_reschedule(session, company)
                return

            for idea_data in ideas:
                idea = GeneratedIdea(
                    company_id=company.id,
                    idea_summary=idea_data.get('hook', '')[:200],
                    hook=idea_data.get('hook', ''),
                    body=idea_data.get('body', ''),
                    cta=idea_data.get('cta', ''),
                    full_content=(
                        f"{idea_data.get('hook', '')}\n\n"
                        f"{idea_data.get('body', '')}\n\n"
                        f"{idea_data.get('cta', '')}"
                    ),
                    platform=idea_data.get('platform', 'linkedin'),
                    implication_type=idea_data.get('implication_type', ''),
                    angle_category=idea_data.get('angle_category', ''),
                    angle_detail=idea_data.get('angle_detail', ''),
                    is_wildcard=idea_data.get('is_wildcard', False),
                    signal_used=idea_data.get('signal_used', ''),
                    status='pending',
                    run_log_id=run_log.id,
                    evergreen=final_state.get("evergreen", False),
                    created_at=datetime.utcnow(),
                )
                session.add(idea)

            _unlock_and_reschedule(session, company)
            logger.info(f"✅ Stored {len(ideas)} ideas for {company.name}")

        except Exception as e:
            logger.error(f"❌ Failed for {company.name}: {e}")
            try:
                session.rollback()
            except Exception:
                pass

            # Publish retry or fatal event to WebSocket
            try:
                r = redis.from_url(redis_url)
                if self.request.retries >= self.max_retries:
                    r.publish(f"trace:{company_id}", json.dumps({
                        "node": "fatal",
                        "status": "error",
                        "timestamp": datetime.utcnow().isoformat(),
                        "message": "Run failed after all retry attempts"
                    }))
                else:
                    r.publish(f"trace:{company_id}", json.dumps({
                        "node": "retry",
                        "status": "warning",
                        "timestamp": datetime.utcnow().isoformat(),
                        "attempt": self.request.retries + 1,
                        "max_retries": self.max_retries
                    }))
            except Exception:
                pass

            if self.request.retries >= self.max_retries:
                # Save error RunLog and release lock on final failure
                try:
                    with get_db_session() as recovery_session:
                        error_run = RunLog(
                            company_id=company_id,
                            status="error",
                            trace={"nodes": [], "error": str(e)},
                            created_at=datetime.utcnow()
                        )
                        recovery_session.add(error_run)
                        comp = recovery_session.query(Company).filter(Company.id == company_id).first()
                        if comp:
                            comp.is_processing = False
                        recovery_session.commit()
                except Exception as inner_e:
                    logger.error(f"Failed to save error RunLog: {inner_e}")

            raise self.retry(exc=e, countdown=60)


def _unlock_and_reschedule(session: Session, company: Company):
    """Helper to unlock company and set next run time."""
    company.is_processing = False
    
    from datetime import timedelta
    if company.next_run_time:
        next_run = company.next_run_time + timedelta(hours=company.frequency_hours)
        if next_run < datetime.utcnow():
            next_run = calculate_next_run_time(datetime.utcnow(), company.frequency_hours)
    else:
        next_run = calculate_next_run_time(datetime.utcnow(), company.frequency_hours)
        
    company.next_run_time = next_run
    session.commit()

@shared_task(bind=True, max_retries=3)
def process_idea_refinement(self, idea_id: int):
    """
    Celery Worker task: Executes Human-in-the-Loop (HITL) idea rewrite using admin feedback.
    """
    from services.worker.agent.core import refine_generated_idea
    
    with get_db_session() as session:
        idea = session.query(GeneratedIdea).filter(GeneratedIdea.id == idea_id).first()
        
        if not idea:
            logger.error(f"❌ Idea {idea_id} not found")
            return
            
        if idea.status != 'refining':
            logger.warning(f"⚠️ Idea {idea_id} is not in refining status. Skipping.")
            return
            
        logger.info(f"🔧 Refining Idea #{idea.id} for company #{idea.company_id}")

        try:
            refined_idea = refine_generated_idea(idea=idea, session=session)
            
            # Update the idea with refined content
            idea.hook = refined_idea.get('hook', idea.hook)
            idea.body = refined_idea.get('body', idea.body)
            idea.cta = refined_idea.get('cta', idea.cta)
            idea.full_content = (
                f"{idea.hook}\n\n{idea.body}\n\n{idea.cta}"
            )
            idea.status = 'pending'  # put it back in pending for re-review
            idea.admin_feedback = None # clear feedback
            idea.updated_at = datetime.utcnow()
            
            session.commit()
            logger.info(f"✅ Successfully refined Idea #{idea.id}")

        except Exception as e:
            logger.error(f"❌ Failed to refine Idea #{idea.id}: {e}")
            try:
                session.rollback()
            except Exception:
                pass

            if self.request.retries >= self.max_retries:
                # Reset idea to pending so user can try again
                try:
                    with get_db_session() as recovery_session:
                        idea_rec = recovery_session.query(GeneratedIdea).filter(
                            GeneratedIdea.id == idea_id
                        ).first()
                        if idea_rec:
                            original_feedback = idea_rec.admin_feedback or ""
                            idea_rec.status = 'pending'
                            idea_rec.admin_feedback = (
                                f"[Rewrite failed — please try again with different feedback]\n\n"
                                f"Original feedback: {original_feedback}"
                            )
                            recovery_session.commit()
                            logger.info(f"Reset stuck idea #{idea_id} back to pending")
                except Exception as inner_e:
                    logger.error(f"Failed to reset stuck idea: {inner_e}")
            else:
                raise self.retry(exc=e, countdown=60)
