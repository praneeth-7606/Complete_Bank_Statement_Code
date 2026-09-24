import asyncio
import json
from copy import deepcopy
from types import SimpleNamespace

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from app import telemetry
from app.evaluation import benchmark, categorization_integrity, insight_checks, persistence_integrity
from app.observability import TraceContext, _usage_from_response


def rows():
    return [{"date": "2026-01-01", "debit": "0.10", "credit": "0.00", "balance": "1.20", "category": "Food"},
            {"date": "2026-01-02", "debit": "0.00", "credit": "0.20", "balance": "1.40", "category": "Income"}]


def values(scores):
    return {item["name"]: item for item in scores}


def test_benchmark_rejects_missing_duplicate_and_swapped_direction():
    expected = rows() + [rows()[0]]
    assert values(benchmark(expected, expected))["financial_exact_match"]["passed"]
    assert not values(benchmark(expected, rows()))["financial_exact_match"]["passed"]
    wrong = deepcopy(expected)
    wrong[0]["credit"], wrong[0]["debit"] = wrong[0]["debit"], wrong[0]["credit"]
    assert not values(benchmark(expected, wrong))["financial_exact_match"]["passed"]


def test_category_score_and_unlabelled_not_success():
    actual = rows()
    actual[0]["category"] = "Income"
    assert values(benchmark(rows(), actual))["category_macro_f1"]["value"] == pytest.approx(1 / 3)
    no_labels = [{k: v for k, v in row.items() if k != "category"} for row in rows()]
    assert values(benchmark(no_labels, actual))["category_macro_f1"]["passed"] is None
    assert insight_checks({"insights": []})[0]["passed"] is False
    assert insight_checks({"insights": ["An insight"]})[1]["passed"] is None


def test_categorization_does_not_change_money():
    actual = rows()
    actual[0]["debit"] = "0.11"
    assert not categorization_integrity(rows(), actual)[0]["passed"]


def test_mongo_same_count_wrong_amount_or_tenant_fails():
    expected = [dict(row, transaction_id=str(i), user_id="u", upload_id="s", amount="0.10") for i, row in enumerate(rows())]
    assert persistence_integrity(expected, deepcopy(expected))[0]["passed"]
    actual = deepcopy(expected)
    actual[0]["user_id"] = "other"
    assert not persistence_integrity(expected, actual)[0]["passed"]
    actual = deepcopy(expected)
    actual[0]["amount"] = "0.11"
    assert not persistence_integrity(expected, actual)[0]["passed"]


def test_export_config_separates_regions_and_metrics():
    settings = SimpleNamespace(OTEL_EXPORTER_OTLP_HEADERS="", OTEL_EXPORTER_OTLP_ENDPOINT="",
                               LANGFUSE_PUBLIC_KEY="pk-test", LANGFUSE_SECRET_KEY="sk-test",
                               LANGFUSE_BASE_URL="https://us.cloud.langfuse.com/")
    targets, config = telemetry.export_config(settings)
    assert targets[0][0] == "https://us.cloud.langfuse.com/api/public/otel/v1/traces"
    assert config[0] == "https://us.cloud.langfuse.com"
    settings.LANGFUSE_BASE_URL = "javascript:alert(1)"
    with pytest.raises(ValueError):
        telemetry.export_config(settings)


def test_worker_trace_propagation_and_exception_redaction(monkeypatch):
    provider = TracerProvider()
    exporter = InMemorySpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    monkeypatch.setattr(telemetry, "_tracer", provider.get_tracer("test"))
    with telemetry.span("upload", parent={}):
        carried = telemetry.carrier()
        parent_id = telemetry.current_id()
    with pytest.raises(ValueError):
        with telemetry.span("worker", parent=carried):
            assert telemetry.current_id() == parent_id
            raise ValueError("password=SECRET financial narration")
    spans = exporter.get_finished_spans()
    assert len(spans) == 2 and spans[1].parent.span_id == spans[0].context.span_id
    assert "SECRET" not in str([(s.attributes, s.events, s.status.description) for s in spans])
    provider.shutdown()


def test_local_telemetry_redacts_errors_and_does_not_count_unmeasured_as_failed():
    execution = TraceContext("/test")
    execution.record_llm("test", "test", 1, error="password=SECRET")
    execution.record_evaluation("unmeasured", None, None, {"password": "SECRET"})
    doc = execution._document()
    assert doc["metrics"]["evaluation_failures"] == 0
    assert "SECRET" not in json.dumps(doc, default=str)


def test_vector_readback_rejects_cross_tenant(monkeypatch):
    from app.vector_store_pinecone import PineconeVectorStore
    async def no_sleep(_):
        pass
    monkeypatch.setattr(asyncio, "sleep", no_sleep)
    store = object.__new__(PineconeVectorStore)
    item = dict(rows()[0], transaction_id="t", user_id="u", upload_id="s")
    store.index = SimpleNamespace(fetch=lambda **_: {"vectors": {"t": {"metadata": item}}})
    assert asyncio.run(store.verify_transactions([item]))
    store.index = SimpleNamespace(fetch=lambda **_: {"vectors": {"t": {"metadata": dict(item, user_id="other")}}})
    assert not asyncio.run(store.verify_transactions([item]))


def test_usage_skips_unrelated_metadata_and_reads_sdk_usage():
    response = SimpleNamespace(response_metadata={"model": "example"},
        usage=SimpleNamespace(model_dump=lambda: {"prompt_tokens": 20, "completion_tokens": 4}))
    assert _usage_from_response(response) == (20, 4, "provider")
