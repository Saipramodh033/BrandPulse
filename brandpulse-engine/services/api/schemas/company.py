"""
Company API Schemas
===================
Pydantic models for company request/response serialization.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class CompanyCreate(BaseModel):
    """Request body for creating a company."""
    name: str
    email: str
    description: Optional[str] = None
    frequency_hours: float = 24.0


class CompanyUpdate(BaseModel):
    """Request body for updating a company (all fields optional)."""
    name: Optional[str] = None
    description: Optional[str] = None
    frequency_hours: Optional[float] = None
    status: Optional[str] = None  # "active" or "paused"


class CompanyResponse(BaseModel):
    """Response model for a company."""
    id: int
    name: str
    email: str
    description: Optional[str]
    frequency_hours: float
    status: str
    next_run_time: Optional[datetime]
    created_at: datetime
    is_processing: bool = False
    pending_ideas_count: Optional[int] = None

    model_config = {"from_attributes": True}
