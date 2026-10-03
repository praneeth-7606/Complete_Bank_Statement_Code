"""Exercise actual LangChain/OpenAI request serialization without external APIs."""

import asyncio
import json

import httpx
import pytest
from langchain_openai import ChatOpenAI

from app import llm_provider
from app.agentic_rag import QueryPlan
from app.config import settings
from app.observability import instrument_model


PLAN = {
    "needs_mongo": True,
    "needs_vector": False,
    "needs_aggregation": False,
    "filters": {"amount": {"$gt": 50000}},
    "sort": {"amount": -1},
    "limit": 50,
}


def _response():
    return httpx.Response(200, json={
        "id": "chatcmpl-test", "object": "chat.completion", "created": 1,
        "model": "test-model",
        "choices": [{"index": 0, "finish_reason": "tool_calls", "message": {
            "role": "assistant", "content": None,
            "tool_calls": [{"id": "call-plan", "type": "function", "function": {
                "name": "QueryPlan", "arguments": json.dumps(PLAN),
            }}],
        }}],
    })


def _model(client, provider, retries=0):
    model = ChatOpenAI(
        model="test-model", api_key="test-key", max_retries=retries,
        base_url=f"https://{provider}.example/v1", http_async_client=client,
    )
    return instrument_model(model, provider, "test-model")


@pytest.mark.parametrize("provider", ["groq", "zai"])
def test_query_plan_uses_non_strict_tools_and_preserves_dynamic_maps(monkeypatch, provider):
    def handle(request):
        body = json.loads(request.content)
        assert "response_format" not in body, "QueryPlan maps cannot use strict JSON schema"
        tool = body["tools"][0]["function"]
        assert tool["strict"] is False
        assert tool["parameters"]["properties"]["filters"].get("additionalProperties") is not False
        return _response()

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            model = _model(client, provider)
            monkeypatch.setattr(llm_provider, "_configured_models", lambda *a, **kw: [model])
            result = await llm_provider.build_structured_llm(QueryPlan).ainvoke("Plan a query")
            assert isinstance(result, QueryPlan)
            assert result.filters == PLAN["filters"]
            assert result.sort == {"amount": -1}
    asyncio.run(run())


@pytest.mark.parametrize("recover", [True, False])
def test_zai_rate_limit_has_bounded_retry(monkeypatch, recover):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    monkeypatch.setattr(settings, "GROQ_API_KEY", "")
    monkeypatch.setattr(settings, "ZAI_API_KEY", "test-key")
    configured = llm_provider._configured_models(settings.GEMINI_MODEL, 0)[0]
    retries = configured.bound.max_retries
    assert retries == 1
    calls = []

    def handle(request):
        calls.append(request)
        if len(calls) == 1 or not recover:
            return httpx.Response(429, headers={"retry-after-ms": "1"}, json={
                "error": {"message": "Too many requests", "type": "rate_limit_error"},
            })
        return _response()

    async def run():
        from openai import RateLimitError
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            model = _model(client, "zai", retries=retries)
            monkeypatch.setattr(llm_provider, "_configured_models", lambda *a, **kw: [model])
            runnable = llm_provider.build_structured_llm(QueryPlan)
            if recover:
                result = await runnable.ainvoke("Plan a query")
                assert result.sort == {"amount": -1}
            else:
                with pytest.raises(RateLimitError):
                    await runnable.ainvoke("Plan a query")
        assert len(calls) == 2
    asyncio.run(run())


def test_structured_fallback_still_returns_validated_plan(monkeypatch):
    calls = []

    def handle(request):
        calls.append(request.url.host)
        if request.url.host == "groq.example":
            return httpx.Response(429, json={"error": {"message": "Quota exhausted"}})
        return _response()

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            providers = [_model(client, name) for name in ("groq", "zai")]
            monkeypatch.setattr(llm_provider, "_configured_models", lambda *a, **kw: providers)
            result = await llm_provider.build_structured_llm(QueryPlan, route="chat").ainvoke("Plan a query")
            assert isinstance(result, QueryPlan)
            assert result.filters == PLAN["filters"]
        assert calls == ["groq.example", "zai.example"]
    asyncio.run(run())
