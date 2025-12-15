"""
Agent Core - Public API
=======================
Main functions for insight generation and refinement
"""

import logging
import time
from typing import Tuple
from sqlalchemy.orm import Session

from langgraph.graph import StateGraph, END

from services.shared.models import Company
from services.worker.agent.llm import get_llm  # ← Import from llm.py instead
from services.worker.agent.nodes import (
    AgentState,
    retrieve_company_context,
    search_market_news,
    generate_strategic_insight
)

logger = logging.getLogger(__name__)


def build_agent_graph() -> StateGraph:
    """Build LangGraph workflow"""
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("retrieve_context", retrieve_company_context)
    workflow.add_node("search_news", search_market_news)
    workflow.add_node("generate_insight", generate_strategic_insight)
    
    # Define flow
    workflow.set_entry_point("retrieve_context")
    workflow.add_edge("retrieve_context", "search_news")
    workflow.add_edge("search_news", "generate_insight")
    workflow.add_edge("generate_insight", END)
    
    return workflow.compile()


def generate_insight(company: Company, session: Session) -> Tuple[str, float, int]:
    """
    Generate new market intelligence insight.
    
    Returns:
        (content, processing_time, token_count)
    """
    logger.info(f"🚀 Generating insight for {company.name}")
    
    start_time = time.time()
    
    # Initialize state
    initial_state = AgentState(
        company=company,
        company_context="",
        search_query="",
        search_results=[],
        messages=[],
        iteration=0,
        final_insight="",
        should_continue=True,
        admin_feedback=None
    )
    
    # Run agent
    agent = build_agent_graph()
    final_state = agent.invoke(initial_state)
    
    processing_time = time.time() - start_time
    token_count = len(final_state['final_insight']) // 4
    
    logger.info(f"✅ Insight generated ({processing_time:.2f}s)")
    
    return final_state['final_insight'], processing_time, token_count


def refine_insight(
    company: Company,
    previous_content: str,
    admin_feedback: str,
    session: Session
) -> Tuple[str, float, int]:
    """
    Refine insight with admin feedback.
    
    Returns:
        (refined_content, processing_time, token_count)
    """
    logger.info(f"🔧 Refining insight for {company.name}")
    
    start_time = time.time()
    
    # Initialize state with feedback
    initial_state = AgentState(
        company=company,
        company_context="",
        search_query="",
        search_results=[],
        messages=[],
        iteration=0,
        final_insight="",
        should_continue=True,
        admin_feedback=admin_feedback
    )
    
    # Run agent
    agent = build_agent_graph()
    final_state = agent.invoke(initial_state)
    
    processing_time = time.time() - start_time
    token_count = len(final_state['final_insight']) // 4
    
    logger.info(f"✅ Insight refined ({processing_time:.2f}s)")
    
    return final_state['final_insight'], processing_time, token_count