"""
Agent Package
=============
Autonomous ReAct content strategy agent.

The LLM orchestrates tool calls (search, signal extraction, idea generation,
validation) and decides autonomously when to stop and submit results.

Public API:
  run_ideation_v4()       — ReAct agent loop (schedule-triggered)
  refine_generated_idea() — HITL idea rewrite (Celery task-triggered)
"""

from services.worker.agent.core import run_ideation_v4, refine_generated_idea
from services.worker.agent.llm import get_llm

__all__ = ["run_ideation_v4", "refine_generated_idea", "get_llm"]