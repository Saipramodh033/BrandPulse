"""
Agent Tools
===========
LangChain tools available to the ReAct orchestrator.

Each tool is a self-contained capability the LLM can choose to call.
The orchestrator (core.py) decides WHICH tools to call, WHEN, and in what order.

Stateless tools (no DB):
  - search_web
  - extract_signal
  - generate_ideas
  - validate_and_critique_ideas

DB-aware tools (created via make_db_tools factory):
  - recall_company_memory   — reads past ideas / angles from DB
  - finish                  — submits final ideas, ends the agent loop
"""

import json
import logging
import os
import time
from typing import List

from langchain_core.messages import HumanMessage
from langchain_core.tools import tool

from services.worker.agent.llm import get_llm, get_llm_structured
from services.worker.agent.schemas import (
    IdeaBatch,
    Signal,
    ValidationBatch,
    CompanyProfileSchema,
    AngleSelection,
)

logger = logging.getLogger(__name__)

# Exported so the API router can import it without importing the full graph
ANGLE_CATEGORIES = [
    "build-in-public",
    "user-perception",
    "hiring-and-culture",
    "contrarian-take",
    "industry-trend",
    "competitive-positioning",
    "data-driven-insight",
    "founder-story",
    "product-update",
    "customer-success",
]


# ── Tool 1: Recall Company Memory ─────────────────────────────────────────
# (Created via factory — needs DB session)

def make_db_tools(company, session):
    """
    Factory: returns (recall_company_memory, finish) tools that close over
    the company ORM object and SQLAlchemy session.
    Called once per agent run in core.py.
    """

    @tool
    def recall_company_memory() -> str:
        """
        Retrieve this company's content history from the database.
        Returns past angles used, rejected angles, approved angles, and recent
        idea hooks so you can pick a fresh direction and avoid repetition.
        ALWAYS call this first before choosing an angle or generating ideas.
        """
        from services.shared.models import GeneratedIdea

        ideas = (
            session.query(GeneratedIdea)
            .filter(GeneratedIdea.company_id == company.id)
            .order_by(GeneratedIdea.created_at.desc())
            .limit(50)
            .all()
        )

        past_angles      = list({i.angle_category for i in ideas if i.angle_category})
        rejected_angles  = list({i.angle_category for i in ideas if i.status == "rejected" and i.angle_category})
        approved_angles  = list({i.angle_category for i in ideas if i.status == "approved" and i.angle_category})
        recent_hooks     = [i.hook for i in ideas[:10] if i.hook]

        return json.dumps({
            "past_angles": past_angles,
            "rejected_angles": rejected_angles,
            "approved_angles": approved_angles,
            "recent_hooks": recent_hooks,
            "available_angles": ANGLE_CATEGORIES,
            "total_ideas_generated": len(ideas),
        })

    @tool
    def finish(
        validated_ideas_json: str,
        angle_category: str,
        angle_detail: str,
        is_evergreen: bool,
        signal_description: str,
    ) -> str:
        """
        Submit your final validated ideas and end the agent loop.
        Call this ONLY when you are satisfied you have at least 3 high-quality,
        validated ideas. Do NOT call this prematurely — quality matters more than speed.

        Args:
            validated_ideas_json: JSON array of final idea dicts (hook/body/cta/platform/implication_type)
            angle_category: The content angle category you chose (e.g. 'build-in-public')
            angle_detail: Specific sub-angle description
            is_evergreen: True if you used evergreen mode (no fresh market signal found)
            signal_description: The market signal used, or 'evergreen' if is_evergreen=True
        """
        try:
            ideas = json.loads(validated_ideas_json)
        except Exception:
            ideas = []

        logger.info(f"🏁 Agent calling finish() with {len(ideas)} ideas")
        return json.dumps({
            "status": "done",
            "ideas": ideas,
            "angle_category": angle_category,
            "angle_detail": angle_detail,
            "is_evergreen": is_evergreen,
            "signal_description": signal_description,
        })

    return recall_company_memory, finish


# ── Tool 2: Profile Company ────────────────────────────────────────────────

@tool
def profile_company(company_name: str, company_description: str, pdf_text: str) -> str:
    """
    Extract a structured profile for the company: industry space, target audience,
    brand voice, and key differentiators. Call once at the start of each run.
    Returns JSON with keys: space, audience, brand_voice, key_differentiators, region.

    Args:
        company_name: Name of the company
        company_description: Short description of what the company does
        pdf_text: Full text from the company's PDF document (or description if no PDF)
    """
    logger.info(f"🏢 Profiling {company_name}...")
    llm = get_llm_structured().with_structured_output(CompanyProfileSchema)

    prompt = f"""Extract a structured company profile from the following document.

Company Name: {company_name}
Description: {company_description}

Document:
{pdf_text[:6000]}

Base your answers on the document. If a field cannot be determined, make a reasonable inference."""

    try:
        profile = llm.invoke(prompt)
        result = {
            "space": profile.space,
            "audience": profile.audience,
            "content_fit": profile.content_fit,
            "brand_voice": profile.brand_voice,
            "key_differentiators": profile.key_differentiators,
            "region": profile.region,
        }
        logger.info(f"✅ Profile extracted: space={profile.space}")
        return json.dumps(result)
    except Exception as e:
        logger.error(f"❌ Profile extraction failed: {e}")
        return json.dumps({
            "space": company_description or "Technology",
            "audience": "Business professionals",
            "content_fit": "industry news, company updates",
            "brand_voice": "professional",
            "key_differentiators": company_description or "",
            "region": "India",
        })


# ── Tool 3: Search Web ─────────────────────────────────────────────────────

@tool
def search_web(query: str) -> str:
    """
    Search the web for recent news, trends, and market intelligence.
    Use specific, focused queries — NOT generic ones like '{company} news'.
    Returns formatted search results as text.
    Call this to gather raw market context. You may call it multiple times
    with different queries if the first search returns weak results.

    Args:
        query: A focused search query (max 150 chars)
    """
    query = " ".join(query.split())[:150]
    logger.info(f"🔍 Searching: {query}")

    tavily_key = os.getenv("TAVILY_API_KEY", "")
    if tavily_key and tavily_key not in ("your_tavily_api_key_here", ""):
        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=tavily_key)
            resp = client.search(query=query, search_depth="basic", max_results=5)
            results = [
                f"{i}. **{item.get('title', 'Article')}**\n   {item.get('content', '')[:500]}\n   {item.get('url', '')}"
                for i, item in enumerate(resp.get("results", []), 1)
            ]
            if results:
                logger.info(f"✅ Tavily: {len(results)} results")
                return "\n\n".join(results)
        except Exception as e:
            logger.warning(f"Tavily failed: {e}, falling back to DuckDuckGo")

    # DuckDuckGo fallback
    try:
        time.sleep(2)
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            raw = list(ddgs.text(keywords=query, max_results=5, timelimit="m"))
        if raw:
            formatted = [
                f"{i}. **{r['title']}**\n   {r['body']}\n   {r['href']}"
                for i, r in enumerate(raw[:5], 1)
            ]
            logger.info(f"✅ DuckDuckGo: {len(formatted)} results")
            return "\n\n".join(formatted)
        return "No recent results found."
    except Exception as e:
        logger.warning(f"Search failed: {e}")
        return "Search temporarily unavailable."


# ── Tool 4: Extract Signal ─────────────────────────────────────────────────

@tool
def extract_signal(
    search_results: str,
    company_name: str,
    company_space: str,
) -> str:
    """
    Analyze search results and extract the single strongest market signal.
    A strong signal is SPECIFIC (references a concrete event/number/report),
    RECENT (last 30-90 days), and VERIFIABLE (traceable to a source in the results).
    Returns JSON with: signal_description, strength ('strong'/'weak'), why_relevant, source.
    If strength is 'weak', call search_web again with a different query (up to 3 times total).

    Args:
        search_results: Raw search results text from search_web
        company_name: Company name for relevance filtering
        company_space: Industry/space the company operates in
    """
    logger.info(f"📡 Extracting signal for {company_name}")
    llm = get_llm_structured().with_structured_output(Signal)

    prompt = f"""You are evaluating search results for a usable market signal for {company_name} in the {company_space} space.

Search Results:
{search_results}

Apply these 3 tests:
1. SPECIFIC: Does it reference a concrete event, number, company, or report? (not generic trend talk)
2. RECENT: Is it from the last 30-90 days?
3. VERIFIABLE: Can it be traced to a real source mentioned in the results?

If ALL 3 pass → strength = "strong"
If ANY fail → strength = "weak"

Extract the single strongest signal."""

    try:
        signal = llm.invoke(prompt)
        logger.info(f"✅ Signal extracted: strength={signal.strength}")
        return json.dumps({
            "signal_description": signal.signal_description,
            "strength": signal.strength,
            "why_relevant": signal.why_it_matters,
            "source": signal.source,
            "specificity_proof": signal.specificity_proof,
        })
    except Exception as e:
        logger.error(f"Signal extraction failed: {e}")
        return json.dumps({"signal_description": "", "strength": "weak", "why_relevant": "", "source": ""})


# ── Tool 5: Generate Ideas ─────────────────────────────────────────────────

@tool
def generate_ideas(
    company_name: str,
    company_description: str,
    company_space: str,
    brand_voice: str,
    signal_description: str,
    signal_strength: str,
    angle_category: str,
    angle_detail: str,
    is_evergreen: bool,
    avoid_hooks: str = "",
) -> str:
    """
    Generate 4 platform-ready content ideas grounded in the market signal and chosen angle.
    Returns a JSON array of idea dicts: hook, body, cta, platform, implication_type.
    Call validate_and_critique_ideas on the result before deciding to finish.

    Args:
        company_name: Company name
        company_description: Short company description
        company_space: Industry the company operates in
        brand_voice: Tone/voice (e.g. 'conversational, bold')
        signal_description: The market signal to ground ideas in (or 'evergreen' if is_evergreen=True)
        signal_strength: 'strong' or 'weak'
        angle_category: Chosen angle category (e.g. 'build-in-public')
        angle_detail: Specific sub-angle (e.g. 'sharing raw metrics publicly')
        is_evergreen: If True, don't reference specific current events
        avoid_hooks: Comma-separated recent hooks to avoid repeating
    """
    logger.info(f"💡 Generating ideas: angle={angle_category}, evergreen={is_evergreen}")
    llm = get_llm().with_structured_output(IdeaBatch)

    avoid_section = f"\nAvoid repeating these recent hooks:\n{avoid_hooks}\n" if avoid_hooks else ""

    if is_evergreen:
        signal_section = "No strong market signal was found. Generate TIMELESS ideas that don't depend on current news. Focus on foundational truths, positioning stories, and educational content."
    else:
        signal_section = f"""Ground at least one idea in this market signal:
Signal: {signal_description}
Signal strength: {signal_strength}"""

    prompt = f"""You are a content strategist for {company_name}.

Company: {company_name}
Description: {company_description}
Space: {company_space}
Brand Voice: {brand_voice}

Content Angle: {angle_category} — {angle_detail}

{signal_section}
{avoid_section}

Generate 4 distinct, platform-ready content ideas. Each idea MUST:
- Have a punchy, SPECIFIC hook (not generic — reference {company_name}'s actual context)
- Have a substantive 2-4 sentence body
- Have a clear, non-generic CTA
- Target linkedin, twitter, or instagram
- Feel human — avoid corporate speak
- Explore a DIFFERENT implication type: product / audience / hiring / industry

Do NOT write ideas that could apply to any company. Ground them in {company_name}'s specific situation."""

    try:
        batch = llm.invoke(prompt)
        ideas = [idea.model_dump() for idea in (batch.ideas or [])]
        logger.info(f"✅ Generated {len(ideas)} ideas")
        return json.dumps(ideas)
    except Exception as e:
        logger.error(f"Idea generation failed: {e}")
        return json.dumps([])


# ── Tool 6: Validate and Critique Ideas ───────────────────────────────────

@tool
def validate_and_critique_ideas(
    ideas_json: str,
    company_name: str,
    company_space: str,
    brand_voice: str,
) -> str:
    """
    Critically evaluate generated ideas against 4 quality criteria.
    Returns JSON with:
      - passing_ideas: list of idea dicts that passed
      - weak_count: number of ideas that failed
      - feedback: list of {idea_index, reason} for weak ideas
    If weak_count > 0, you may choose to call generate_ideas again with a better
    signal/angle, or call finish() with just the passing ideas if >= 3 pass.

    Args:
        ideas_json: JSON array of idea dicts from generate_ideas
        company_name: Company name
        company_space: Industry space
        brand_voice: Brand voice for tone evaluation
    """
    logger.info(f"⚖️ Validating ideas for {company_name}")

    try:
        ideas = json.loads(ideas_json)
    except Exception:
        return json.dumps({"passing_ideas": [], "weak_count": 0, "feedback": []})

    if not ideas:
        return json.dumps({"passing_ideas": [], "weak_count": 0, "feedback": []})

    llm = get_llm_structured().with_structured_output(ValidationBatch)

    ideas_text = "\n\n".join(
        f"Idea {i}:\nHook: {idea.get('hook', '')}\nBody: {idea.get('body', '')}\nCTA: {idea.get('cta', '')}"
        for i, idea in enumerate(ideas)
    )

    prompt = f"""You are the Managing Editor for {company_name} ({company_space}).
Brand Voice: {brand_voice}

Review these content ideas against 4 criteria:
1. Relevance: Highly relevant to {company_name}'s space and audience?
2. Actionability: Clear, non-generic takeaway?
3. Uniqueness: Interesting perspective, or boring corporate speak?
4. Signal-Grounding: Uses specific facts/signal (or strong evergreen value)?

{ideas_text}

Return a batch evaluation. Mark passed=True only if ALL 4 criteria are met.
action should be 'pass', 'tweak', or 'fail'."""

    try:
        batch = llm.invoke(prompt)

        # Fix 1-based indexing if LLM uses it
        evals = sorted(batch.evaluations, key=lambda e: e.idea_index)
        if evals and all(e.idea_index >= 1 for e in evals):
            for e in evals:
                e.idea_index -= 1

        passing = []
        feedback = []
        for e in evals:
            if 0 <= e.idea_index < len(ideas):
                if e.passed or e.action == "pass":
                    passing.append(ideas[e.idea_index])
                else:
                    feedback.append({
                        "idea_index": e.idea_index,
                        "reason": e.reason,
                        "action": e.action,
                    })

        # Safety: if everything failed, pass all through rather than zero output
        if not passing:
            logger.warning("⚠️ All ideas failed validation — passing all through as fallback")
            passing = ideas
            feedback = []

        logger.info(f"✅ Validation: {len(passing)} passing, {len(feedback)} weak")
        return json.dumps({
            "passing_ideas": passing,
            "weak_count": len(feedback),
            "feedback": feedback,
        })

    except Exception as e:
        logger.error(f"Validation failed: {e}")
        return json.dumps({"passing_ideas": ideas, "weak_count": 0, "feedback": []})
