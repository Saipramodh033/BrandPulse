"""
Companies Router
================
CRUD endpoints for company management.
"""

import logging
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from services.api.dependencies import get_db
from services.api.schemas.company import CompanyCreate, CompanyUpdate, CompanyResponse
from services.shared.models import Company, CompanyStatusEnum, GeneratedIdea

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/companies", tags=["Companies"])


@router.get("/", response_model=List[CompanyResponse])
def list_companies(db: Session = Depends(get_db)):
    """List all companies ordered by creation date."""
    companies = db.query(Company).order_by(Company.created_at.desc()).all()
    
    # A3 Fix: Batch pending counts in a single query instead of N+1
    company_ids = [c.id for c in companies]
    pending_counts = {}
    if company_ids:
        rows = (
            db.query(GeneratedIdea.company_id, func.count(GeneratedIdea.id))
            .filter(
                GeneratedIdea.company_id.in_(company_ids),
                GeneratedIdea.status == 'pending'
            )
            .group_by(GeneratedIdea.company_id)
            .all()
        )
        pending_counts = {row[0]: row[1] for row in rows}
    
    result = []
    for c in companies:
        result.append(CompanyResponse(
            id=c.id, name=c.name, email=c.email,
            description=c.description,
            frequency_hours=c.frequency_hours,
            status=c.status.value,
            next_run_time=c.next_run_time,
            created_at=c.created_at,
            is_processing=c.is_processing,
            pending_ideas_count=pending_counts.get(c.id, 0),
        ))
    return result


@router.get("/{company_id}", response_model=CompanyResponse)
def get_company(company_id: int, db: Session = Depends(get_db)):
    """Get a single company by ID."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    pending_count = db.query(func.count(GeneratedIdea.id)).filter(
        GeneratedIdea.company_id == company_id,
        GeneratedIdea.status == 'pending'
    ).scalar()
    
    return CompanyResponse(
        id=company.id, name=company.name, email=company.email,
        description=company.description,
        frequency_hours=company.frequency_hours,
        status=company.status.value,
        next_run_time=company.next_run_time,
        created_at=company.created_at,
        is_processing=company.is_processing,
        pending_ideas_count=pending_count,
    )


@router.post("/", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
def create_company(payload: CompanyCreate, db: Session = Depends(get_db)):
    """Create a new company."""
    existing = db.query(Company).filter(Company.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    company = Company(
        name=payload.name,
        email=payload.email,
        description=payload.description,
        frequency_hours=payload.frequency_hours,
        status=CompanyStatusEnum.ACTIVE,
        next_run_time=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    logger.info(f"Created company: {company.name}")
    return CompanyResponse(
        id=company.id, name=company.name, email=company.email,
        description=company.description,
        frequency_hours=company.frequency_hours,
        status=company.status.value,
        next_run_time=company.next_run_time,
        created_at=company.created_at,
    )


@router.patch("/{company_id}", response_model=CompanyResponse)
def update_company(company_id: int, payload: CompanyUpdate, db: Session = Depends(get_db)):
    """Update company fields."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    if payload.name is not None:
        company.name = payload.name
    if payload.description is not None:
        company.description = payload.description
    if payload.frequency_hours is not None:
        company.frequency_hours = payload.frequency_hours
    if payload.status is not None:
        company.status = (
            CompanyStatusEnum.ACTIVE if payload.status == "active"
            else CompanyStatusEnum.PAUSED
        )
    company.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(company)
    return CompanyResponse(
        id=company.id, name=company.name, email=company.email,
        description=company.description,
        frequency_hours=company.frequency_hours,
        status=company.status.value,
        next_run_time=company.next_run_time,
        created_at=company.created_at,
    )


@router.post("/{company_id}/run", status_code=status.HTTP_202_ACCEPTED)
def trigger_run(company_id: int, db: Session = Depends(get_db)):
    """Manually trigger ideation run for a company by setting next_run_time to now."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    if company.status != CompanyStatusEnum.ACTIVE:
        raise HTTPException(status_code=400, detail="Company is paused")

    # A5 Fix: Mirror the Inbox Zero rule — don't trigger if ideas are pending
    pending_count = db.query(func.count(GeneratedIdea.id)).filter(
        GeneratedIdea.company_id == company_id,
        GeneratedIdea.status == 'pending'
    ).scalar() or 0
    if pending_count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot trigger run: {pending_count} ideas are pending review. Clear your inbox first."
        )

    company.next_run_time = datetime.utcnow()
    company.is_processing = False  # Break any stuck locks
    company.updated_at = datetime.utcnow()
    db.commit()
    return {"message": f"Run triggered for {company.name}", "company_id": company_id}


@router.get("/{company_id}/runs")
def get_company_runs(company_id: int, limit: int = 20, db: Session = Depends(get_db)):
    """Get recent execution traces (RunLogs) for a company."""
    from services.shared.models import RunLog, GeneratedIdea
    from sqlalchemy import func
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    runs = db.query(RunLog).filter(RunLog.company_id == company_id).order_by(RunLog.created_at.desc()).limit(limit).all()
    
    result = []
    for run in runs:
        trace = run.trace or {}
        if isinstance(trace, list):
            trace = {"nodes": trace}
            
        idea_count = db.query(func.count(GeneratedIdea.id)).filter(GeneratedIdea.run_log_id == run.id).scalar() or 0
        approved_count = db.query(func.count(GeneratedIdea.id)).filter(GeneratedIdea.run_log_id == run.id, GeneratedIdea.status == 'approved').scalar() or 0
        result.append({
            "id": run.id,
            "status": run.status,
            "nodes": trace.get("nodes", []),
            "search_query": trace.get("search_query", ""),
            "search_results": trace.get("search_results", []),
            "signal": trace.get("signal"),
            "signal_strength": trace.get("signal_strength"),
            "chosen_angle": trace.get("chosen_angle"),
            "evergreen": trace.get("evergreen", False),
            "ideas_generated": idea_count,
            "ideas_approved": approved_count,
            "created_at": run.created_at
        })
    return result


@router.get("/{company_id}/angles")
def get_company_angles(company_id: int, db: Session = Depends(get_db)):
    """
    Return the content angle memory for a company.
    Aggregates generated_ideas by (angle_category, angle_detail) and
    computes idea_count, approved_count and win-rate.
    """
    from services.shared.models import GeneratedIdea
    from sqlalchemy import func

    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    from sqlalchemy import case as sa_case

    rows = (
        db.query(
            GeneratedIdea.angle_category,
            GeneratedIdea.angle_detail,
            GeneratedIdea.is_wildcard,
            func.count(GeneratedIdea.id).label("idea_count"),
            func.sum(
                sa_case((GeneratedIdea.status == "approved", 1), else_=0)
            ).label("approved_count"),
        )
        .filter(GeneratedIdea.company_id == company_id)
        .group_by(
            GeneratedIdea.angle_category,
            GeneratedIdea.angle_detail,
            GeneratedIdea.is_wildcard,
        )
        .order_by(GeneratedIdea.angle_category)
        .all()
    )

    from services.worker.agent.tools import ANGLE_CATEGORIES

    used_map = { r.angle_category: r for r in rows if r.angle_category }

    result = []
    for cat in ANGLE_CATEGORIES:
        if cat in used_map:
            r = used_map[cat]
            result.append({
                "id": cat,
                "category": cat,
                "sub_angle": r.angle_detail or cat,
                "is_wildcard": False,
                "idea_count": r.idea_count or 0,
                "approved_count": int(r.approved_count or 0),
                "status": "used"
            })
        else:
            result.append({
                "id": cat,
                "category": cat,
                "sub_angle": cat,
                "is_wildcard": False,
                "idea_count": 0,
                "approved_count": 0,
                "status": "unused"
            })

    # Also add wildcards that have been used (is_wildcard=True rows)
    wildcard_rows = [r for r in rows if r.is_wildcard and r.angle_category]
    for r in wildcard_rows:
        result.append({
            "id": f"wc-{r.angle_category}",
            "category": r.angle_category,
            "sub_angle": r.angle_detail or r.angle_category,
            "is_wildcard": True,
            "idea_count": r.idea_count or 0,
            "approved_count": int(r.approved_count or 0),
            "status": "used"
        })

    return result


@router.get("/{company_id}/ideas")
def get_company_ideas(
    company_id: int,
    status: str = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """List ideas for a company, optionally filtered by status."""
    from services.shared.models import GeneratedIdea

    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    q = db.query(GeneratedIdea).filter(GeneratedIdea.company_id == company_id)
    if status:
        q = q.filter(GeneratedIdea.status == status)
    ideas = q.order_by(GeneratedIdea.created_at.desc()).limit(limit).all()

    return [
        {
            "id": idea.id,
            "hook": idea.hook,
            "body": idea.body,
            "cta": idea.cta,
            "platform": idea.platform,
            "implication_type": idea.implication_type,  # F3 Fix: was missing
            "angle_category": idea.angle_category,
            "angle_detail": idea.angle_detail,
            "is_wildcard": idea.is_wildcard,
            "signal_used": idea.signal_used,
            "status": idea.status,
            "admin_feedback": idea.admin_feedback,
            "evergreen": idea.evergreen,               # F3 Fix: was missing
            "run_log_id": idea.run_log_id,             # F3 Fix: was missing
            "created_at": idea.created_at,
        }
        for idea in ideas
    ]


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_company(company_id: int, db: Session = Depends(get_db)):
    """Delete a company."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    db.delete(company)
    db.commit()

