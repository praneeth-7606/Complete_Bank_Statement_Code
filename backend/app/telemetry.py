"""Content-free OpenTelemetry instrumentation; Langfuse receives traces only."""
from __future__ import annotations

import base64
import json
import logging
import time
from contextlib import contextmanager
from urllib.parse import urlparse

from opentelemetry import trace
from opentelemetry.context import Context
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Status, StatusCode

logger = logging.getLogger(__name__)
_provider = None
_tracer = None
_metrics_provider = None
_meter = None
_counters = {}
_score_config = None


def valid_url(value):
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("Telemetry URL must be an HTTP(S) base URL without credentials or query")
    return value.rstrip("/")


def export_config(settings):
    """Separate generic collector endpoints from Langfuse trace ingestion."""
    headers = dict(part.strip().split("=", 1) for part in settings.OTEL_EXPORTER_OTLP_HEADERS.split(",") if "=" in part)
    collector = settings.OTEL_EXPORTER_OTLP_ENDPOINT.strip()
    targets = []
    if collector:
        targets.append((valid_url(collector) + "/v1/traces", headers))
    score_config = None
    if settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY:
        base = valid_url(settings.LANGFUSE_BASE_URL)
        auth = base64.b64encode(f"{settings.LANGFUSE_PUBLIC_KEY}:{settings.LANGFUSE_SECRET_KEY}".encode()).decode()
        lf_headers = {"Authorization": f"Basic {auth}", "x-langfuse-ingestion-version": "4"}
        targets.append((base + "/api/public/otel/v1/traces", lf_headers))
        score_config = (base, lf_headers)
    return targets, score_config


def configure_telemetry(settings):
    global _provider, _tracer, _metrics_provider, _meter, _score_config
    if _provider:
        return True
    try:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        targets, _score_config = export_config(settings)
        resource = Resource.create({"service.name": settings.OTEL_SERVICE_NAME, "deployment.environment": settings.APP_ENV})
        _provider = TracerProvider(resource=resource)
        for endpoint, headers in targets:
            _provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, headers=headers, timeout=5)))
        # Own provider avoids replacing any framework's global provider.
        _tracer = _provider.get_tracer("bank-statement.part1")
        if settings.OTEL_EXPORTER_OTLP_METRICS_ENDPOINT:
            from opentelemetry.sdk.metrics import MeterProvider
            from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
            from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
            exporter = OTLPMetricExporter(endpoint=valid_url(settings.OTEL_EXPORTER_OTLP_METRICS_ENDPOINT), timeout=5)
            _metrics_provider = MeterProvider(resource=resource, metric_readers=[PeriodicExportingMetricReader(exporter)])
            _meter = _metrics_provider.get_meter("bank-statement.part1")
        return True
    except Exception:
        logger.warning("External telemetry disabled: configuration could not be initialized")
        return False


def shutdown_telemetry():
    global _provider, _tracer, _metrics_provider, _meter, _score_config
    for provider in (_provider, _metrics_provider):
        if provider:
            provider.shutdown()
    _provider = _tracer = _metrics_provider = _meter = _score_config = None
    _counters.clear()


def carrier():
    result = {}
    TraceContextTextMapPropagator().inject(result)
    return result


def current_id():
    ctx = trace.get_current_span().get_span_context()
    return format(ctx.trace_id, "032x") if ctx.is_valid else None


@contextmanager
def span(name, attributes=None, parent=None):
    if _tracer is None:
        yield None
        return
    context = TraceContextTextMapPropagator().extract(parent, context=Context()) if parent is not None else None
    # Exception messages and stack traces can contain financial data.
    with _tracer.start_as_current_span(name, context=context, attributes=attributes or {}, record_exception=False, set_status_on_exception=False) as active:
        try:
            yield active
        except BaseException as exc:
            active.set_attribute("error.type", type(exc).__name__)
            active.set_status(Status(StatusCode.ERROR))
            raise


def add_event(name, attributes=None):
    if _tracer:
        trace.get_current_span().add_event(name, attributes=attributes or {})


def record_generation(provider, model, duration_ms, input_tokens, output_tokens, status, kind):
    if not _tracer:
        return
    end = time.time_ns()
    with _tracer.start_as_current_span(
        "provider.call", start_time=end - int(max(duration_ms, 0) * 1_000_000),
        end_on_exit=False, record_exception=False, set_status_on_exception=False,
        attributes={"langfuse.observation.type": "embedding" if kind == "embedding" else "generation",
                    "langfuse.observation.model.name": model, "gen_ai.system": provider,
                    "langfuse.observation.usage_details": json.dumps({"input": input_tokens, "output": output_tokens})},
    ) as active:
        if status == "failed":
            active.set_status(Status(StatusCode.ERROR))
        active.end(end_time=end)


def record_counter(name, value=1, attributes=None):
    if _meter:
        if name not in _counters:
            _counters[name] = _meter.create_counter(name)
        counter = _counters[name]
        counter.add(value, attributes or {})


async def export_scores(document):
    """Idempotent, bounded score delivery. Failure leaves local scores intact."""
    if not _score_config or not document.get("otel_trace_id") or not document.get("evaluation_scores"):
        return "disabled"
    import httpx
    import uuid
    base, headers = _score_config
    batch = []
    for score in document["evaluation_scores"]:
        if score["value"] is None:
            continue
        identifier = str(uuid.uuid5(uuid.NAMESPACE_URL, document["trace_id"] + score["name"] + score["timestamp"]))
        batch.append({"id": identifier, "timestamp": score["timestamp"], "type": "score-create", "body": {
            "id": identifier, "traceId": document["otel_trace_id"], "name": score["name"],
            "value": score["value"], "dataType": "NUMERIC", "comment": "Part 1 evaluator v1",
        }})
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.post(base + "/api/public/ingestion", headers=headers, json={"batch": batch})
            response.raise_for_status()
            if response.json().get("errors"):
                return "failed"
        return "exported"
    except Exception:
        logger.warning("Langfuse score delivery failed; scores remain in MongoDB")
        return "failed"
