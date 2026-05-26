"""
Idea API Schemas
================
Pydantic models for generated idea request/response serialization.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class IdeaResponse(BaseModel):
    """Response model for a generated idea."""
    id: int
    company_id: int
    idea_summary: Optional[str]
    hook: Optional[str]
    body: Optional[str]
    cta: Optional[str]
    full_content: str
    platform: Optional[str]
    implication_type: Optional[str]
    angle_category: Optional[str]
    angle_detail: Optional[str]
    is_wildcard: bool
    signal_used: Optional[str]
    evergreen: bool = False
    run_log_id: Optional[int] = None
    status: str
    admin_feedback: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class IdeaFeedback(BaseModel):
    """Request body for providing feedback on an idea."""
    feedback: Optional[str] = None
