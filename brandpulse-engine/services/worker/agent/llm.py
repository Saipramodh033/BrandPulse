"""
LLM Configuration
================
Google Gemini LLM initialization with rate-limit-aware retries.
"""

import os
import re
import time
import logging
from langchain_google_genai import ChatGoogleGenerativeAI

logger = logging.getLogger(__name__)


def _extract_retry_delay(exc: Exception) -> float:
    """
    Parse the retry delay from a Google 429 ResourceExhausted error message.
    Falls back to 60 seconds if not found.
    """
    try:
        match = re.search(r"retry in (\d+(?:\.\d+)?)s", str(exc), re.IGNORECASE)
        if match:
            delay = float(match.group(1))
            logger.warning(f"⏳ Rate limited. Waiting {delay:.0f}s as requested by API...")
            return delay
    except Exception:
        pass
    return 60.0


class RetryLLM:
    """Wrapper around LLM that respects Google API rate-limit retry delays."""

    def __init__(self, llm, max_retries: int = 5):
        self.llm = llm
        self.max_retries = max_retries

    def _invoke_with_retry(self, fn, *args, **kwargs):
        last_exc = None
        for attempt in range(1, self.max_retries + 1):
            try:
                res = fn(*args, **kwargs)
                if res is None:
                    raise ValueError("Structured LLM returned None (parsing failure)")
                return res
            except Exception as e:
                last_exc = e
                err_str = str(e)
                # Retry on rate limit errors or parsing failures
                if "429" in err_str or "ResourceExhausted" in err_str or "quota" in err_str.lower() or "parsing failure" in err_str.lower():
                    delay = _extract_retry_delay(e) if "parsing failure" not in err_str.lower() else 2.0
                    logger.warning(
                        f"⚠️  Retryable error hit (attempt {attempt}/{self.max_retries}). "
                        f"Sleeping {delay:.0f}s..."
                    )
                    time.sleep(delay)
                else:
                    raise  # Non-quota/non-parsing errors bubble up immediately
        raise last_exc

    def invoke(self, *args, **kwargs):
        return self._invoke_with_retry(self.llm.invoke, *args, **kwargs)

    def with_structured_output(self, *args, **kwargs):
        structured = self.llm.with_structured_output(*args, **kwargs)
        return RetryLLM(structured, max_retries=self.max_retries)

    def bind_tools(self, *args, **kwargs):
        bound_llm = self.llm.bind_tools(*args, **kwargs)
        return RetryLLM(bound_llm, max_retries=self.max_retries)


def get_llm(model: str | None = None) -> RetryLLM:
    """
    Initialize Google Gemini LLM with rate-limit-aware retries.

    Model priority:
      1. `model` argument (explicit override)
      2. GEMINI_MODEL env var
      3. Default: gemini-2.5-flash-lite
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not configured")

    resolved_model = model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    logger.info(f"🤖 Using LLM: {resolved_model}")

    llm = ChatGoogleGenerativeAI(
        model=resolved_model,
        google_api_key=api_key,
        temperature=0.7,
        max_output_tokens=2048,
    )
    return RetryLLM(llm)


def get_llm_structured(model: str | None = None) -> RetryLLM:
    """
    LLM for structured extraction tasks (validation, signal, angle, query).
    Uses low temperature for deterministic, schema-compliant output.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not configured")

    resolved_model = model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    logger.info(f"🤖 Using LLM (structured): {resolved_model}")

    llm = ChatGoogleGenerativeAI(
        model=resolved_model,
        google_api_key=api_key,
        temperature=0.1,  # Low temp for deterministic structured output
        max_output_tokens=2048,
    )
    return RetryLLM(llm)