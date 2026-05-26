"""
Ideas Router
============
Endpoints for managing generated content ideas.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from services.api.dependencies import get_db
from services.api.schemas.idea import IdeaResponse, IdeaFeedback
from services.shared.models import GeneratedIdea

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ideas", tags=["Ideas"])


@router.get("/", response_model=List[IdeaResponse])
def list_ideas(
    company_id: Optional[int] = Query(None, description="Filter by company"),
    status: Optional[str] = Query(None, description="Filter by status: pending/approved/rejected"),
    db: Session = Depends(get_db),
):
    """List ideas with optional filters."""
    q = db.query(GeneratedIdea)
    if company_id:
        q = q.filter(GeneratedIdea.company_id == company_id)
    if status:
        q = q.filter(GeneratedIdea.status == status)
    return q.order_by(GeneratedIdea.created_at.desc()).all()


@router.get("/{idea_id}", response_model=IdeaResponse)
def get_idea(idea_id: int, db: Session = Depends(get_db)):
    """Get a single idea by ID."""
    idea = db.query(GeneratedIdea).filter(GeneratedIdea.id == idea_id).first()
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    return idea


@router.patch("/{idea_id}/approve", response_model=IdeaResponse)
def approve_idea(idea_id: int, db: Session = Depends(get_db)):
    """Approve a pending idea."""
    idea = db.query(GeneratedIdea).filter(GeneratedIdea.id == idea_id).first()
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    if idea.status not in ('pending', 'refining'):
        raise HTTPException(status_code=400, detail=f"Cannot approve idea in '{idea.status}' status")
    idea.status = "approved"
    db.commit()
    db.refresh(idea)
    logger.info(f"Approved idea {idea_id}")
    return idea


@router.patch("/{idea_id}/reject", response_model=IdeaResponse)
def reject_idea(idea_id: int, payload: IdeaFeedback, db: Session = Depends(get_db)):
    """Reject an idea with optional feedback."""
    idea = db.query(GeneratedIdea).filter(GeneratedIdea.id == idea_id).first()
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    if idea.status not in ('pending', 'refining'):
        raise HTTPException(status_code=400, detail=f"Cannot reject idea in '{idea.status}' status")
    idea.status = "rejected"
    idea.admin_feedback = payload.feedback
    db.commit()
    db.refresh(idea)
    logger.info(f"Rejected idea {idea_id}")
    return idea


@router.post("/{idea_id}/refine", response_model=IdeaResponse)
def request_refinement(idea_id: int, payload: IdeaFeedback, db: Session = Depends(get_db)):
    from services.worker.celery_app import app as celery_app
    
    idea = db.query(GeneratedIdea).filter(GeneratedIdea.id == idea_id).first()
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    idea.status = "refining"
    idea.admin_feedback = payload.feedback
    db.commit()
    db.refresh(idea)
    
    # Dispatch HITL refinement task using the explicitly configured app
    celery_app.send_task(
        "services.worker.tasks.ideation_task.process_idea_refinement",
        args=[idea.id]
    )
    
    logger.info(f"Idea {idea_id} marked for refinement and task dispatched")
    return idea
