"""
Agent Core - ReAct Orchestrator
================================
Autonomous Reason + Act (ReAct) agent loop.

The LLM orchestrates execution dynamically:
  - Chooses which tools to call based on live feedback
  - Re-evaluates search queries dynamically if market signals are weak
  - Applies self-critique editorial checks before finalizing ideas
  - Gracefully falls back to evergreen mode after repeated signal failures

Entry points:
  - run_ideation_v4(company, session) -> (ideas, final_state)
  - refine_generated_idea(idea, session) -> dict
"""

import json
import logging
import os
import time
from datetime import datetime
from typing import Tuple

from sqlalchemy import text
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from services.shared.models import Company
from services.worker.agent.llm import get_llm
from services.worker.agent.prompts import get_react_system_prompt
from services.worker.agent.tools import (
    make_db_tools,
    profile_company,
    search_web,
    extract_signal,
    generate_ideas,
    validate_and_critique_ideas,
    ANGLE_CATEGORIES,
)

logger = logging.getLogger(__name__)

# Maximum tool calls before forcing a stop (prevents infinite loops)
MAX_ITERATIONS = 20


def run_ideation_v4(company: Company, session) -> Tuple[list, dict]:
    """
    Run the ReAct agent for one company.

    The LLM autonomously sequences tool calls:
      recall_memory → profile → search → signal → generate → validate → finish

    Unlike the old LangGraph pipeline, the agent can:
      - Search multiple times with different queries
      - Skip steps it deems unnecessary
      - Choose which ideas to refine vs accept
      - Decide when the output is good enough to stop

    Returns:
        (validated_idea_dicts, final_state_dict)
        - validated_idea_dicts: list of idea dicts with hook/body/cta/platform/implication_type
          plus angle_category, angle_detail, is_wildcard, signal_used
        - final_state_dict: RunLog-compatible dict with trace_events key
    """
    logger.info(f"🤖 ReAct agent starting for {company.name}")
    start_time = time.time()

    # ── Build tool roster ───────────────────────────────────────────────────
    recall_memory, finish = make_db_tools(company, session)

    all_tools = [
        recall_memory,
        profile_company,
        search_web,
        extract_signal,
        generate_ideas,
        validate_and_critique_ideas,
        finish,
    ]
    tool_map = {t.name: t for t in all_tools}

    # ── Connect LLM to tools ────────────────────────────────────────────────
    llm = get_llm()
    agent = llm.bind_tools(all_tools)

    # ── Redis for live trace ────────────────────────────────────────────────
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis_client = None
    try:
        import redis as redis_lib
        redis_client = redis_lib.from_url(redis_url)
        redis_client.ping()  # test connection
    except Exception as e:
        logger.warning(f"⚠️ Redis unavailable — live trace disabled: {e}")
        redis_client = None

    # ── Initial messages: Prime agent with persona, instructions, and context ──
    company_context = company.pdf_text or f"{company.name}: {company.description or 'No details available.'}"

    messages = [
        SystemMessage(content=get_react_system_prompt(company)),
        HumanMessage(
            content=(
                f"Generate high-quality content ideas for {company.name}.\n\n"
                f"Company context (first 1500 chars):\n{company_context[:1500]}\n\n"
                f"Start by calling recall_company_memory, then profile_company."
            )
        ),
    ]

    trace_events = []
    final_result = None

    # ── Autonomous ReAct execution loop (Capped at MAX_ITERATIONS to prevent loops) ──
    for iteration in range(MAX_ITERATIONS):
        logger.info(f"🔄 Agent iteration {iteration + 1}/{MAX_ITERATIONS}")

        # Cooperative cancellation check: query database to verify if an admin clicked 'Force Reset' in the UI.
        # If is_processing was flipped to False, gracefully abort execution immediately.
        is_processing = session.execute(
            text("SELECT is_processing FROM companies WHERE id = :id"),
            {"id": company.id}
        ).scalar()
        
        if not is_processing:
            logger.warning(f"⚠️ Agent aborted by user reset on iteration {iteration + 1}")
            break

        # Query the LLM with current conversation history and bound tools
        try:
            response = agent.invoke(messages)
        except Exception as e:
            logger.error(f"❌ LLM call failed on iteration {iteration + 1}: {e}")
            if redis_client:
                try:
                    redis_client.publish(
                        f"trace:{company.id}",
                        json.dumps({
                            "node": "error",
                            "status": "error",
                            "timestamp": datetime.utcnow().isoformat(),
                            "message": f"AI model error on step {iteration + 1}"
                        })
                    )
                except Exception:
                    pass
            # Re-raise so Celery catches the failure, triggers a retry, and saves the Error RunLog
            raise

        # Append assistant response (which contains thoughts and tool calls) to message history
        messages.append(response)

        # Fallback guard: if the model produced text without invoking any tool, prompt it to continue
        if not response.tool_calls:
            logger.warning("⚠️ Agent produced text without tool call — prompting to continue")
            messages.append(
                HumanMessage(content="You must call a tool. If you have generated and validated ideas, call finish(). Do not stop by outputting plain text.")
            )
            continue

        # ── Execute each tool call requested by the LLM ──────────────────────
        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            tool_id   = tool_call["id"]

            logger.info(f"🔧 Agent → {tool_name}({list(tool_args.keys())})")

            # Broadcast execution trace event to Redis Pub/Sub for live frontend WebSocket streaming
            trace_event = {
                "node": tool_name,
                "timestamp": datetime.utcnow().isoformat(),
                "status": "success",
            }
            trace_events.append(trace_event)

            if redis_client:
                try:
                    redis_client.publish(
                        f"trace:{company.id}",
                        json.dumps(trace_event)
                    )
                except Exception as e:
                    logger.warning(f"Redis publish failed: {e}")

            # Execute tool safely; capture exceptions as tool error observations rather than crashing
            try:
                result_str = tool_map[tool_name].invoke(tool_args)
            except Exception as e:
                result_str = json.dumps({"error": str(e)})
                trace_events[-1]["status"] = "error"
                logger.error(f"Tool {tool_name} raised: {e}")

            # Return tool observation back to the LLM conversation scratchpad
            messages.append(
                ToolMessage(content=str(result_str), tool_call_id=tool_id, name=tool_name)
            )

            # Terminal tool check: when finish() is executed, extract the validated payload and terminate
            if tool_name == "finish":
                try:
                    final_result = json.loads(result_str)
                except Exception:
                    final_result = {
                        "ideas": [], "angle_category": "", "angle_detail": "",
                        "is_evergreen": False, "signal_description": "",
                    }
                break  # Exit tool calls loop

        if final_result is not None:
            break  # Exit ReAct iterations loop

    # ── Build output ────────────────────────────────────────────────────────
    elapsed = time.time() - start_time

    if not final_result:
        logger.error(f"❌ Agent did not call finish() after {MAX_ITERATIONS} iterations")
        # Publish error event so frontend knows what happened
        if redis_client:
            try:
                redis_client.publish(
                    f"trace:{company.id}",
                    json.dumps({
                        "node": "error",
                        "timestamp": datetime.utcnow().isoformat(),
                        "status": "error",
                        "message": "Agent used maximum iterations without completing"
                    })
                )
            except Exception:
                pass
        final_result = {
            "ideas": [], "angle_category": "", "angle_detail": "",
            "is_evergreen": False, "signal_description": "",
        }

    ideas = final_result.get("ideas", [])

    # Attach angle + signal metadata to each idea (consumed by ideation_task.py)
    for idea in ideas:
        idea["angle_category"] = final_result.get("angle_category", "")
        idea["angle_detail"]   = final_result.get("angle_detail", "")
        idea["is_wildcard"]    = final_result.get("angle_category") == "Wildcard"
        idea["signal_used"]    = (
            "evergreen"
            if final_result.get("is_evergreen")
            else final_result.get("signal_description", "")
        )

    # RunLog-compatible state dict
    final_state = {
        "trace_events":   trace_events,
        "search_query":   "",  # agent may have searched multiple times
        "search_results": [],
        "signal": {
            "signal_description": final_result.get("signal_description", "")
        },
        "signal_strength": "high" if ideas else "none",
        "chosen_angle": {
            "category":  final_result.get("angle_category", ""),
            "sub_angle": final_result.get("angle_detail", ""),
        },
        "evergreen":        final_result.get("is_evergreen", False),
        "validated_ideas":  ideas,
        "refinement_count": 0,
        "error": None if ideas else "Agent did not produce any ideas",
    }

    # Publish completion event to WebSocket
    if redis_client:
        try:
            redis_client.publish(
                f"trace:{company.id}",
                json.dumps({
                    "node": "complete",
                    "timestamp": datetime.utcnow().isoformat(),
                    "status": "success" if ideas else "empty",
                    "ideas_count": len(ideas),
                    "message": f"{len(ideas)} ideas generated" if ideas else "Run complete — no ideas produced"
                })
            )
        except Exception as e:
            logger.warning(f"Redis publish (complete) failed: {e}")

    logger.info(
        f"✅ ReAct agent complete: {len(ideas)} ideas in {elapsed:.1f}s "
        f"({iteration + 1} iteration(s), {len(trace_events)} tool calls)"
    )
    return ideas, final_state


def refine_generated_idea(idea, session) -> dict:
    """
    Rewrite a single GeneratedIdea using admin feedback (HITL refinement).

    This is a direct single LLM call — NOT part of the agent loop.
    Called by process_idea_refinement Celery task in ideation_task.py.

    Returns:
        Dict with keys: hook, body, cta, platform, implication_type
    """
    from langchain_core.messages import HumanMessage, SystemMessage
    from services.worker.agent.schemas import ContentIdea

    logger.info(f"🔧 Refining GeneratedIdea #{idea.id}")
    llm = get_llm().with_structured_output(ContentIdea)

    system_prompt = (
        "You are a senior content editor. Your job is to rewrite a social media post "
        "according to the manager's feedback. Output a structured ContentIdea with the "
        "same fields: hook, body, cta, platform, implication_type. "
        "Ensure all feedback is completely addressed."
    )

    user_prompt = (
        f"Original Post:\n"
        f"Hook: {idea.hook}\n"
        f"Body: {idea.body}\n"
        f"CTA: {idea.cta}\n"
        f"Platform: {idea.platform}\n\n"
        f"Manager Feedback:\n{idea.admin_feedback}\n\n"
        f"Rewrite the post to completely satisfy the feedback."
    )

    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])
        return {
            "hook":             response.hook,
            "body":             response.body,
            "cta":              response.cta,
            "platform":         response.platform,
            "implication_type": response.implication_type,
        }
    except Exception as e:
        logger.error(f"❌ LLM failed during refinement: {e}")
        raise