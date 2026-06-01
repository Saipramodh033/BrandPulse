"""
Time Utilities - Date/Time Calculations
=======================================
Helper functions for scheduling and expiration checks
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from services.shared.models import Company, GeneratedIdea

logger = logging.getLogger(__name__)


def calculate_next_run_time(current_time: datetime, frequency_hours: int) -> datetime:
    """
    Calculate next scheduled run time for a company.
    
    Args:
        current_time: Current timestamp (UTC)
        frequency_hours: Company's frequency setting
        
    Returns:
        Next run datetime (UTC)
        
    Example:
        >>> calculate_next_run_time(datetime(2025, 1, 1, 10, 0), 24)
        datetime(2025, 1, 2, 10, 0)  # 24 hours later
    """
    freq = max(1.0, float(frequency_hours))
    return current_time + timedelta(hours=freq)


def is_insight_expired(insight: GeneratedIdea, company: Company) -> bool:
    """
    Check if pending insight exceeded company's frequency window.
    
    An insight is expired if:
    - Status is PENDING
    - Age (now - created_at) > company.frequency_hours
    
    Args:
        insight: Insight to check
        company: Company owning the insight
        
    Returns:
        True if expired, False otherwise
        
    Example:
        Insight created at 10:00, frequency=24h, now=11:00 → False (not expired)
        Insight created at 10:00, frequency=24h, now=35:00 → True (expired)
    """
    now = datetime.utcnow()
    age = now - insight.created_at
    max_age = timedelta(hours=company.frequency_hours)
    
    is_expired = age > max_age
    
    if is_expired:
        hours_old = age.total_seconds() / 3600
        logger.debug(
            f"Insight #{insight.id} expired: "
            f"{hours_old:.1f}h old (max: {company.frequency_hours}h)"
        )
    
    return is_expired


def format_duration(seconds: float) -> str:
    """
    Format duration in human-readable format.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted string
        
    Examples:
        >>> format_duration(45.2)
        '45.2s'
        >>> format_duration(125)
        '2m 5s'
        >>> format_duration(3665)
        '1h 1m'
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    
    if minutes < 60:
        return f"{minutes}m {remaining_seconds:.0f}s"
    
    hours = int(minutes // 60)
    remaining_minutes = minutes % 60
    
    return f"{hours}h {remaining_minutes}m"


def get_time_until(target_time: datetime) -> str:
    """
    Get human-readable time until target datetime.
    
    Args:
        target_time: Future datetime (UTC)
        
    Returns:
        Formatted string (e.g., "in 2h 30m")
        
    Example:
        >>> get_time_until(datetime.utcnow() + timedelta(hours=2, minutes=30))
        'in 2h 30m'
    """
    now = datetime.utcnow()
    
    if target_time <= now:
        return "overdue"
    
    delta = target_time - now
    return f"in {format_duration(delta.total_seconds())}"