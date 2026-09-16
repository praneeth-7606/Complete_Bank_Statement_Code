"""Shared hosted LLM routing for production-safe provider failover.

Structured workloads use Gemini -> Groq -> Z.AI. Chat/RAG uses
Groq -> Gemini -> Z.AI. OCR routing remains separate in smart_extractor.
"""

from typing import Any, Type

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from .config import settings


def _configured_models(model_name: str, temperature: float, route: str = "structured") -> list[Any]:
    """Build configured providers in priority order without making API calls."""
    builders = {
        "gemini": lambda: ChatGoogleGenerativeAI(
            model=model_name,
            temperature=temperature,
            google_api_key=settings.GEMINI_API_KEY,
            max_retries=0,
        ),
        "groq": lambda: ChatOpenAI(
            model=settings.GROQ_MODEL,
            temperature=temperature,
            api_key=settings.GROQ_API_KEY,
            base_url=settings.GROQ_BASE_URL,
            max_retries=0,
        ),
        "zai": lambda: ChatOpenAI(
            model=settings.ZAI_MODEL,
            temperature=temperature,
            api_key=settings.ZAI_API_KEY,
            base_url=settings.ZAI_BASE_URL,
            max_retries=0,
        ),
    }
    keys = ["groq", "gemini", "zai"] if route == "chat" else ["gemini", "groq", "zai"]
    configured = {
        "gemini": bool(settings.GEMINI_API_KEY),
        "groq": bool(settings.GROQ_API_KEY),
        "zai": bool(settings.ZAI_API_KEY),
    }
    providers = [builders[key]() for key in keys if configured[key]]

    if not providers:
        raise RuntimeError(
            "No hosted LLM provider configured. Set GEMINI_API_KEY or GROQ_API_KEY."
        )
    return providers


def build_llm(model_name: str = "gemini-2.5-flash", temperature: float = 0.0, route: str = "structured") -> Any:
    """Return a routed runnable; structured defaults to Gemini-first."""
    providers = _configured_models(model_name, temperature, route=route)
    return providers[0].with_fallbacks(providers[1:]) if len(providers) > 1 else providers[0]


def build_chat_llm(model_name: str = "gemini-2.5-flash", temperature: float = 0.0) -> Any:
    """Return the chat/RAG route: Groq -> Gemini -> Z.AI."""
    return build_llm(model_name, temperature=temperature, route="chat")


def build_structured_llm(schema: Type[Any], model_name: str = "gemini-2.5-flash", temperature: float = 0.0) -> Any:
    """Apply the same provider order after structured-output binding.

    Binding before fallback is important: Groq must satisfy the same Pydantic
    contract when Gemini is unavailable.
    """
    structured = [provider.with_structured_output(schema) for provider in _configured_models(model_name, temperature, route="structured")]
    return structured[0].with_fallbacks(structured[1:]) if len(structured) > 1 else structured[0]
