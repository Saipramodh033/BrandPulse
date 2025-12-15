"""
Agent Nodes - LangGraph Node Implementations
============================================
Individual processing steps in the agent workflow
"""

import logging
import time
import os
from datetime import datetime
from typing import Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from duckduckgo_search import DDGS

from services.shared.models import Company
from services.worker.agent.llm import get_llm  # ← Import from llm.py instead
from services.worker.agent.prompts import get_system_prompt, get_user_prompt

logger = logging.getLogger(__name__)


class AgentState(Dict):
    """Agent state definition"""
    company: Company
    company_context: str
    search_query: str
    search_results: List[str]
    messages: List
    iteration: int
    final_insight: str
    should_continue: bool
    admin_feedback: Optional[str]


def retrieve_company_context(state: AgentState) -> AgentState:
    """Node: Retrieve company PDF context"""
    logger.info(f"📄 Retrieving context for {state['company'].name}")
    
    company = state['company']
    context = company.pdf_text or f"Company: {company.name}\nDescription: {company.description or 'N/A'}"
    
    # Truncate if too long
    max_length = 15000
    if len(context) > max_length:
        context = context[:max_length] + "\n\n[Truncated]"
    
    state['company_context'] = context
    logger.info(f"✅ Retrieved {len(context)} characters")
    
    return state


def search_market_news(state: AgentState) -> AgentState:
    """Node: Search for market news using Tavily or DuckDuckGo"""
    company = state['company']
    
    # Check if web search is enabled
    enable_search = os.getenv('ENABLE_WEB_SEARCH', 'true').lower() == 'true'
    
    if not enable_search:
        logger.info(f"⏭️ Web search disabled for {company.name}")
        state['search_query'] = f"{company.name} news (search disabled)"
        state['search_results'] = ["Web search is disabled. Generating insight from company context only."]
        return state
    
    logger.info(f"🔍 Searching news for {company.name}")
    
    search_query = f"{company.name} {company.description or ''} news trends"
    state['search_query'] = search_query
    
    # Try Tavily first (if API key provided)
    tavily_key = os.getenv('TAVILY_API_KEY')
    
    logger.info(f"🔑 Tavily API key present: {bool(tavily_key and tavily_key != 'your_tavily_api_key_here')}")
    
    if tavily_key and tavily_key != 'your_tavily_api_key_here':
        try:
            logger.info("🚀 Attempting Tavily search...")
            results = search_with_tavily(search_query, tavily_key)
            if results:
                state['search_results'] = results
                logger.info(f"✅ Tavily: Found {len(results)} results")
                return state
        except Exception as e:
            logger.error(f"❌ Tavily failed: {e}, falling back to DuckDuckGo")
    else:
        logger.warning("⚠️ Tavily API key not configured, using DuckDuckGo")
    
    # Fallback to DuckDuckGo
    try:
        time.sleep(2)  # Rate limit protection
        
        with DDGS() as ddgs:
            results = list(ddgs.text(
                keywords=search_query,
                max_results=5,
                region='wt-wt',
                safesearch='moderate',
                timelimit='m'
            ))
        
        if not results:
            logger.warning("⚠️ No recent news found. Using company context only.")
            state['search_results'] = ["No recent news found. Analysis based on company context."]
            return state
        
        formatted = []
        for i, result in enumerate(results[:5], 1):
            formatted.append(f"{i}. **{result['title']}**\n   {result['body']}\n   {result['href']}")
        
        state['search_results'] = formatted
        logger.info(f"✅ DuckDuckGo: Found {len(results)} results")
        
    except Exception as e:
        logger.warning(f"⚠️ Search failed: {e}")
        state['search_results'] = ["Search temporarily unavailable. Generating insight from company context only."]
    
    return state


def search_with_tavily(query: str, api_key: str) -> List[str]:
    """Search using Tavily API"""
    try:
        from tavily import TavilyClient
        
        client = TavilyClient(api_key=api_key)
        
        response = client.search(
            query=query,
            search_depth="basic",
            max_results=5,
            include_answer=False,
            include_raw_content=False
        )
        
        # Format results
        formatted = []
        for i, item in enumerate(response.get('results', []), 1):
            title = item.get('title', 'Article')
            content = item.get('content', '')[:500]
            url = item.get('url', '')
            formatted.append(f"{i}. **{title}**\n   {content}\n   {url}")
        
        return formatted
        
    except Exception as e:
        logger.error(f"❌ Tavily search failed: {e}")
        raise


def generate_strategic_insight(state: AgentState) -> AgentState:
    """Node: Generate insight using LLM"""
    logger.info("🧠 Generating insight...")
    
    llm = get_llm()
    company = state['company']
    
    # Build prompt
    system_prompt = get_system_prompt()
    user_prompt = get_user_prompt(
        company=company,
        company_context=state['company_context'],
        search_results=state['search_results'],
        admin_feedback=state.get('admin_feedback')
    )
    
    # Generate
    try:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = llm.invoke(messages)
        insight_content = response.content
        
        # Add timestamp
        if "*Generated by BrandPulse" not in insight_content:
            timestamp = datetime.utcnow().strftime('%B %d, %Y at %H:%M UTC')
            insight_content += f"\n\n---\n*Generated by BrandPulse AI | {timestamp}*"
        
        state['final_insight'] = insight_content
        state['should_continue'] = False
        
        logger.info(f"✅ Generated {len(insight_content)} characters")
        
    except Exception as e:
        logger.error(f"❌ Generation failed: {e}")
        state['final_insight'] = f"# Error\n\nFailed to generate insight: {e}"
        state['should_continue'] = False
    
    return state