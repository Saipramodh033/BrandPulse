"""
Validation Utilities - Input Validation
=======================================
Validate companies, insights, and configuration
"""

import logging
from typing import Optional
import re

from services.shared.models import Company, Insight

logger = logging.getLogger(__name__)


def validate_company_for_processing(company: Company) -> Optional[str]:
    """
    Validate if company is ready for insight generation.
    
    Args:
        company: Company to validate
        
    Returns:
        Error message if invalid, None if valid
    """
    if not company.pdf_text or not company.pdf_text.strip():
        return "Company has no PDF context uploaded"
    
    if not company.email or not company.email.strip():
        return "Company has no email configured"
    
    if not is_valid_email(company.email):
        return f"Invalid email format: {company.email}"
    
    if company.frequency_hours < 1:
        return f"Invalid frequency: {company.frequency_hours} hours (minimum: 1)"
    
    if company.frequency_hours > 720:  # 30 days
        return f"Invalid frequency: {company.frequency_hours} hours (maximum: 720)"
    
    if not company.name or not company.name.strip():
        return "Company has no name"
    
    return None


def is_valid_email(email: str) -> bool:
    """
    Validate email format using regex.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if valid format
        
    Examples:
        >>> is_valid_email("test@example.com")
        True
        >>> is_valid_email("invalid.email")
        False
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_insight_content(content: str) -> Optional[str]:
    """
    Validate generated insight content.
    
    Args:
        content: Insight content (Markdown)
        
    Returns:
        Error message if invalid, None if valid
    """
    if not content or not content.strip():
        return "Insight content is empty"
    
    # Check minimum length (at least 100 characters for meaningful insight)
    if len(content.strip()) < 100:
        return f"Insight too short ({len(content)} chars, minimum: 100)"
    
    # Check for required Markdown structure (at least one heading)
    if not any(marker in content for marker in ['#', '##', '###']):
        return "Insight missing Markdown structure (no headings found)"
    
    return None


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate text to maximum length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length (including suffix)
        suffix: String to append if truncated
        
    Returns:
        Truncated text
        
    Example:
        >>> truncate_text("Hello world", 8)
        'Hello...'
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def sanitize_filename(filename: str) -> str:
    """
    Remove unsafe characters from filename.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename safe for file system
        
    Example:
        >>> sanitize_filename("Company/Name <2025>.pdf")
        'Company_Name_2025.pdf'
    """
    # Replace unsafe characters with underscore
    safe_name = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove leading/trailing spaces and dots
    safe_name = safe_name.strip('. ')
    
    return safe_name