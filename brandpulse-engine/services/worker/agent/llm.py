"""
LLM Configuration & Factory
============================
Multi-provider Model Factory (NVIDIA NIM, Google Gemini, OpenAI, Groq)
equipped with rate-limit retries and socket timeouts for resilient agent execution.
"""

import os
import re
import time
import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)


def _extract_retry_delay(exc: Exception) -> float:
    """
    Parse the recommended retry delay in seconds from provider 429 rate-limit error messages.
    Defaults to 60.0 seconds if no explicit delay is specified in the exception.
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


def _build_llm_client(provider: str, model: str, temperature: float, max_tokens: int):
    """Factory to build the underlying LangChain client based on provider."""
    timeout = 180.0
    
    if provider == "google":
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY is required for provider 'google'")
        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=api_key,
            temperature=temperature,
            max_output_tokens=max_tokens,
            timeout=timeout,
            max_retries=0,
        )
        
    elif provider == "nvidia":
        api_key = os.getenv("NVIDIA_API_KEY")
        if not api_key:
            raise ValueError("NVIDIA_API_KEY is required for provider 'nvidia'")
        return ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url="https://integrate.api.nvidia.com/v1",
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            max_retries=0,
        )
        
    elif provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required for provider 'openai'")
        return ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url=base_url if base_url else None,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            max_retries=0,
        )
        
    elif provider == "groq":
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY is required for provider 'groq'")
        return ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            max_retries=0,
        )
        
    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: {provider}. Supported: nvidia, google, openai, groq")


def get_llm(model: str | None = None) -> RetryLLM:
    """
    Initialize the primary LLM for the ReAct agent based on environment variables.
    """
    # Resolve provider: default to 'nvidia' if NVIDIA_API_KEY is present, fallback to 'google'
    default_provider = "nvidia" if os.getenv("NVIDIA_API_KEY") else "google"
    provider = os.getenv("LLM_PROVIDER", default_provider).lower()
    
    default_models = {
        "nvidia": "nvidia/llama-3.1-nemotron-70b-instruct",
        "google": "gemini-2.5-flash",
        "openai": "gpt-4o-mini",
        "groq": "llama3-70b-8192"
    }
    
    resolved_model = model or os.getenv("LLM_MODEL") or default_models.get(provider, "gpt-4o-mini")
        
    logger.info(f"🤖 Using LLM ({provider}): {resolved_model}")
    
    # Load dynamic temperature and token budget from environment (defaults to 0.7 temp and 4096 tokens)
    temp_env = os.getenv("LLM_TEMPERATURE")
    temperature = float(temp_env) if temp_env is not None else 0.7
    
    tokens_env = os.getenv("LLM_MAX_TOKENS")
    max_tokens = int(tokens_env) if tokens_env is not None else 4096
    
    llm = _build_llm_client(provider, resolved_model, temperature=temperature, max_tokens=max_tokens)
    return RetryLLM(llm)


def get_llm_structured(model: str | None = None) -> RetryLLM:
    """
    LLM for structured extraction tasks (validation, signal, angle, query).
    Uses low temperature for deterministic, schema-compliant output.
    """
    default_provider = "nvidia" if os.getenv("NVIDIA_API_KEY") else "google"
    primary_provider = os.getenv("LLM_PROVIDER", default_provider).lower()
    
    # Allow dedicated provider override for structured extraction tasks
    provider = os.getenv("STRUCTURED_LLM_PROVIDER", primary_provider).lower()
    
    default_models = {
        "nvidia": "meta/llama-3.1-405b-instruct",
        "google": "gemini-2.5-flash",
        "openai": "gpt-4o",
        "groq": "llama3-70b-8192"
    }
    
    resolved_model = model or os.getenv("STRUCTURED_LLM_MODEL") or os.getenv("LLM_MODEL") or default_models.get(provider, "gpt-4o")
        
    logger.info(f"🤖 Using Structured LLM ({provider}): {resolved_model}")
    
    # Load dynamic config (defaults to low temperature 0.1 for strict schema adherence)
    temp_env = os.getenv("STRUCTURED_LLM_TEMPERATURE") or os.getenv("LLM_TEMPERATURE")
    temperature = float(temp_env) if temp_env is not None else 0.1
    
    tokens_env = os.getenv("STRUCTURED_LLM_MAX_TOKENS") or os.getenv("LLM_MAX_TOKENS")
    max_tokens = int(tokens_env) if tokens_env is not None else 4096
    
    llm = _build_llm_client(provider, resolved_model, temperature=temperature, max_tokens=max_tokens)
    return RetryLLM(llm)