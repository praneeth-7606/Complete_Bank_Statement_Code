"""Shared hosted LLM routing for production-safe provider failover.

The application intentionally keeps OCR routing separate (Mistral OCR -> Gemini
Vision). This module routes text and tool-calling workloads (Gemini -> Groq).
"""

from typing import Any, Type

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from .config import settings


def _configured_models(model_name: str, temperature: float) -> list[Any]:
    """Build configured providers in priority order without making API calls."""
    providers: list[Any] = []

    if settings.GEMINI_API_KEY:
        providers.append(
            ChatGoogleGenerativeAI(
                model=model_name,
                temperature=temperature,
                google_api_key=settings.GEMINI_API_KEY,
                max_retries=0,
            )
        )

    if settings.GROQ_API_KEY:
        providers.append(
            ChatOpenAI(
                model=settings.GROQ_MODEL,
                temperature=temperature,
                api_key=settings.GROQ_API_KEY,
                base_url=settings.GROQ_BASE_URL,
                max_retries=0,
            )
        )

    if not providers:
        raise RuntimeError(
            "No hosted LLM provider configured. Set GEMINI_API_KEY or GROQ_API_KEY."
        )
    return providers


def build_llm(model_name: str = "gemini-2.5-flash", temperature: float = 0.0) -> Any:
    """Return a Gemini-first runnable with Groq fallback when configured."""
    providers = _configured_models(model_name, temperature)
    return providers[0].with_fallbacks(providers[1:]) if len(providers) > 1 else providers[0]


def build_structured_llm(schema: Type[Any], model_name: str = "gemini-2.5-flash", temperature: float = 0.0) -> Any:
    """Apply the same provider order after structured-output binding.

    Binding before fallback is important: Groq must satisfy the same Pydantic
    contract when Gemini is unavailable.
    """
    structured = [provider.with_structured_output(schema) for provider in _configured_models(model_name, temperature)]
    return structured[0].with_fallbacks(structured[1:]) if len(structured) > 1 else structured[0]
