"""
Configuration Models for BrandPulse Settings
============================================
Stores configurable settings like LLM prompts
"""

from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime


# Import Base from models.py to ensure same metadata
def get_base():
    from services.shared.models import Base
    return Base

Base = get_base()


class PromptConfig(Base):
    """LLM Prompt Configuration Table"""
    __tablename__ = 'prompt_configs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)  # e.g., "system_prompt", "user_prompt_template"
    prompt_text = Column(Text, nullable=False)
    description = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<PromptConfig(name='{self.name}')>"
