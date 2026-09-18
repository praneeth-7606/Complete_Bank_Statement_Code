from types import SimpleNamespace

from app.observability import TraceContext, _usage_from_response, estimate_cost


def test_estimate_cost_is_zero_for_unknown_models():
    assert estimate_cost("provider/unknown", 1000, 500) == 0.0


def test_estimate_cost_uses_input_and_output_rates():
    cost = estimate_cost("gemini-2.5-flash", 1_000_000, 500_000)
    assert cost == 0.45


def test_usage_normalizes_direct_langchain_message_metadata():
    response = SimpleNamespace(
        usage_metadata={"input_tokens": 12, "output_tokens": 7, "total_tokens": 19}
    )
    assert _usage_from_response(response) == (12, 7, "provider")


def test_trace_document_contains_aggregated_metrics_without_sensitive_payloads():
    trace = TraceContext("/chat")
    trace.set_user("user-1", "transaction_rag_chat")
    trace.record_llm(
        provider="gemini",
        model="gemini-2.5-flash",
        duration_ms=42.5,
        input_tokens=12,
        output_tokens=7,
    )
    document = trace._document()

    assert document["route"] == "/chat"
    assert document["metrics"]["total_tokens"] == 19
    assert document["metrics"]["estimated_cost_usd"] == 0.000006
    assert "prompt" not in document
    assert "password" not in document
