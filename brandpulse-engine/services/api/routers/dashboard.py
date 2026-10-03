"""
Dashboard Router
================
Endpoints for cross-company aggregate stats and activity feeds.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any

from services.api.dependencies import get_db
from services.shared.models import GeneratedIdea, RunLog, Company

router = APIRouter(tags=["Dashboard"])

@router.get("/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Aggregate stats for the dashboard header."""
    total_ideas = db.query(func.count(GeneratedIdea.id)).scalar() or 0
    approved = db.query(func.count(GeneratedIdea.id)).filter(GeneratedIdea.status == 'approved').scalar() or 0
    pending = db.query(func.count(GeneratedIdea.id)).filter(GeneratedIdea.status == 'pending').scalar() or 0
    win_rate = round((approved / total_ideas * 100)) if total_ideas > 0 else 0
    
    return {
        "total_ideas_generated": total_ideas,
        "total_approved": approved,
        "total_pending": pending,
        "overall_win_rate": win_rate,
    }

@router.get("/activity")
def get_activity(limit: int = 20, db: Session = Depends(get_db)):
    """A unified timeline of recent events across all companies."""
    from sqlalchemy.orm import joinedload
    
    # Eagerly load associated Company record in the same query to prevent N+1 overhead
    runs = (
        db.query(RunLog)
        .options(joinedload(RunLog.company))
        .order_by(RunLog.created_at.desc())
        .limit(limit)
        .all()
    )
    events = []
    
    for run in runs:
        trace = run.trace or {}
        if isinstance(trace, list):
            trace = {"nodes": trace}
            
        events.append({
            "type": "run",
            "company_id": run.company_id,
            "company_name": run.company.name if run.company else "Unknown",
            "status": run.status,
            "ideas_generated": trace.get("ideas_generated", 0),
            "evergreen": trace.get("evergreen", False),
            "created_at": run.created_at.isoformat() if run.created_at else None,
            "run_id": run.id,
        })
        
    return sorted(events, key=lambda e: e["created_at"] or "", reverse=True)
