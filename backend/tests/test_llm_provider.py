import pytest

from app.config import settings
from app.llm_provider import _configured_models


def _set_provider_keys(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "gemini-test")
    monkeypatch.setattr(settings, "GROQ_API_KEY", "groq-test")
    monkeypatch.setattr(settings, "ZAI_API_KEY", "zai-test")


def test_structured_route_is_gemini_groq_zai(monkeypatch):
    _set_provider_keys(monkeypatch)
    providers = _configured_models("gemini-2.5-flash", 0, route="structured")
    assert providers[0].__class__.__name__ == "ChatGoogleGenerativeAI"
    assert [provider.model_name for provider in providers[1:]] == [
        settings.GROQ_MODEL,
        settings.ZAI_MODEL,
    ]


def test_chat_route_is_groq_gemini_zai(monkeypatch):
    _set_provider_keys(monkeypatch)
    providers = _configured_models("gemini-2.5-flash", 0, route="chat")
    assert providers[0].__class__.__name__ == "ChatOpenAI"
    assert providers[0].model_name == settings.GROQ_MODEL
    assert providers[1].__class__.__name__ == "ChatGoogleGenerativeAI"
    assert providers[1].model == "models/gemini-2.5-flash"
    assert providers[2].model_name == settings.ZAI_MODEL


def test_no_provider_is_explicit(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    monkeypatch.setattr(settings, "GROQ_API_KEY", "")
    monkeypatch.setattr(settings, "ZAI_API_KEY", "")
    with pytest.raises(RuntimeError, match="No hosted LLM provider"):
        _configured_models("gemini-2.5-flash", 0)
