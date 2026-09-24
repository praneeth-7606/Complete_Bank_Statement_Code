"""Authenticated API used by the in-app observability dashboard."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import math
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.encoders import jsonable_encoder

from . import auth_utils, models

router = APIRouter(prefix="/observability", tags=["Observability"])


def _user_filter(current_user: models.User) -> dict[str, Any]:
    return {"user_id": str(current_user.user_id)}


def _serialize(trace: models.ObservabilityTrace, detail: bool = False) -> dict[str, Any]:
    document = trace.model_dump(exclude={"id"})
    if not detail:
        document.pop("events", None)
        document.pop("llm_calls", None)
    return jsonable_encoder(document)


async def _recent_traces(current_user: models.User, hours: int, limit: int = 1000):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    return await models.ObservabilityTrace.find({**_user_filter(current_user), "started_at": {"$gte": cutoff}}).sort("-started_at").limit(limit).to_list()


def _is_rag_trace(trace: models.ObservabilityTrace) -> bool:
    """A trace is RAG-only when it came from the transaction chat pipeline."""
    return trace.operation == "transaction_rag_chat" or trace.route == "/chat"


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil(len(ordered) * percentile) - 1)
    return round(ordered[index], 2)


async def _recent_rag_traces(current_user: models.User, hours: int, limit: int = 1000):
    traces = await _recent_traces(current_user, hours, limit=limit)
    return [trace for trace in traces if _is_rag_trace(trace)]


@router.get("/configuration")
async def observability_configuration(current_user: models.User = Depends(auth_utils.get_current_user)):
    from .config import settings
    from .telemetry import valid_url
    dashboard = None
    if settings.LANGFUSE_DASHBOARD_URL:
        try:
            dashboard = valid_url(settings.LANGFUSE_DASHBOARD_URL)
        except ValueError:
            pass
    return {"langfuse_configured": bool(settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY),
            "langfuse_dashboard_url": dashboard,
            "note": "Configuration presence does not confirm delivery. Check each trace's export status."}


@router.get("/summary")
async def observability_summary(
    hours: int = Query(24, ge=1, le=720),
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    traces = await _recent_traces(current_user, hours)
    llm_calls = [call for trace in traces for call in (trace.llm_calls or [])]
    evaluation_scores = [score for trace in traces for score in (trace.evaluation_scores or [])]
    evaluated = [score for score in evaluation_scores if score.get("passed") is not None]
    by_provider: dict[str, dict[str, Any]] = {}
    by_route: dict[str, dict[str, Any]] = {}
    for call in llm_calls:
        provider = call.get("provider", "unknown")
        bucket = by_provider.setdefault(provider, {"provider": provider, "calls": 0, "failed": 0, "fallbacks": 0, "tokens": 0, "cost_usd": 0.0})
        bucket["calls"] += 1
        bucket["failed"] += int(call.get("status") == "failed")
        bucket["fallbacks"] += int(call.get("fallback"))
        bucket["tokens"] += int(call.get("total_tokens", 0) or 0)
        bucket["cost_usd"] += float(call.get("cost_usd", 0) or 0)

    for trace in traces:
        bucket = by_route.setdefault(trace.route, {"route": trace.route, "requests": 0, "failed": 0, "avg_latency_ms": 0.0})
        bucket["requests"] += 1
        bucket["failed"] += int(trace.status == "failed")
        bucket["avg_latency_ms"] += trace.duration_ms or 0

    for bucket in by_route.values():
        bucket["avg_latency_ms"] = round(bucket["avg_latency_ms"] / max(bucket["requests"], 1), 2)
    for bucket in by_provider.values():
        bucket["cost_usd"] = round(bucket["cost_usd"], 8)

    total_requests = len(traces)
    return {
        "window_hours": hours,
        "requests": total_requests,
        "successful_requests": sum(trace.status == "success" for trace in traces),
        "failed_requests": sum(trace.status == "failed" for trace in traces),
        "active_requests": sum(trace.status == "running" for trace in traces),
        "total_duration_ms": round(sum(trace.duration_ms or 0 for trace in traces), 2),
        "llm_calls": len(llm_calls),
        "failed_llm_calls": sum(call.get("status") == "failed" for call in llm_calls),
        "fallback_calls": sum(bool(call.get("fallback")) for call in llm_calls),
        "input_tokens": sum(int(call.get("input_tokens", 0) or 0) for call in llm_calls),
        "output_tokens": sum(int(call.get("output_tokens", 0) or 0) for call in llm_calls),
        "total_tokens": sum(int(call.get("total_tokens", 0) or 0) for call in llm_calls),
        "estimated_cost_usd": round(sum(float(call.get("cost_usd", 0) or 0) for call in llm_calls), 8),
        "evaluation_count": len(evaluation_scores),
        "evaluation_not_measured": len(evaluation_scores) - len(evaluated),
        "sample_limit": 1000,
        "sample_limit_reached": len(traces) == 1000,
        "evaluation_failures": sum(1 for score in evaluated if score.get("passed") is False),
        "evaluation_pass_rate": round(
            sum(1 for score in evaluated if score.get("passed")) / len(evaluated), 4
        ) if evaluated else None,
        "by_provider": sorted(by_provider.values(), key=lambda item: item["calls"], reverse=True),
        "by_route": sorted(by_route.values(), key=lambda item: item["requests"], reverse=True),
        "recent_errors": [
            {
                "trace_id": trace.trace_id,
                "route": trace.route,
                "started_at": trace.started_at,
                "events": [event for event in trace.events if event.get("status") == "failed"][-3:],
            }
            for trace in traces
            if trace.status == "failed" or any(event.get("status") == "failed" for event in trace.events)
        ][:10],
    }


@router.get("/rag/summary")
async def rag_observability_summary(
    hours: int = Query(24, ge=1, le=720),
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    """Aggregate RAG-only telemetry for the dedicated in-app screen."""
    traces = await _recent_rag_traces(current_user, hours)
    durations = [float(trace.duration_ms or 0) for trace in traces]
    llm_calls = [call for trace in traces for call in (trace.llm_calls or [])]
    scores = [score for trace in traces for score in (trace.evaluation_scores or []) if score.get("name", "").startswith("rag_")]
    measured = [score for score in scores if score.get("passed") is not None]
    stage_buckets: dict[str, dict[str, Any]] = {}
    retrieval_available = 0
    source_errors = 0

    for trace in traces:
        for event in trace.events or []:
            if not event.get("name", "").startswith("rag."):
                continue
            name = event["name"]
            bucket = stage_buckets.setdefault(name, {"stage": name, "runs": 0, "failed": 0, "duration_total_ms": 0.0, "p95_latency_ms": []})
            bucket["runs"] += 1
            bucket["failed"] += int(event.get("status") == "failed")
            bucket["duration_total_ms"] += float(event.get("duration_ms") or 0)
            bucket["p95_latency_ms"].append(float(event.get("duration_ms") or 0))
            metadata = event.get("metadata") or {}
            if name == "rag.retrieval":
                retrieval_available += int(bool(metadata.get("result_available")))
                source_errors += int(metadata.get("source_error_count") or 0)

    stage_rows = []
    for bucket in stage_buckets.values():
        runs = max(bucket["runs"], 1)
        stage_rows.append({
            "stage": bucket["stage"],
            "runs": bucket["runs"],
            "failed": bucket["failed"],
            "avg_latency_ms": round(bucket["duration_total_ms"] / runs, 2),
            "p95_latency_ms": _percentile(bucket["p95_latency_ms"], 0.95),
        })

    return {
        "window_hours": hours,
        "requests": len(traces),
        "successful_requests": sum(trace.status == "success" for trace in traces),
        "failed_requests": sum(trace.status == "failed" for trace in traces),
        "avg_latency_ms": round(sum(durations) / len(durations), 2) if durations else 0.0,
        "p95_latency_ms": _percentile(durations, 0.95),
        "llm_calls": len(llm_calls),
        "failed_llm_calls": sum(call.get("status") == "failed" for call in llm_calls),
        "fallback_calls": sum(bool(call.get("fallback")) for call in llm_calls),
        "total_tokens": sum(int(call.get("total_tokens", 0) or 0) for call in llm_calls),
        "estimated_cost_usd": round(sum(float(call.get("cost_usd", 0) or 0) for call in llm_calls), 8),
        "retrieval_available_rate": round(retrieval_available / len(traces), 4) if traces else None,
        "source_error_count": source_errors,
        "evaluation_count": len(scores),
        "evaluation_failures": sum(score.get("passed") is False for score in measured),
        "evaluation_pass_rate": round(sum(score.get("passed") is True for score in measured) / len(measured), 4) if measured else None,
        "stage_metrics": sorted(stage_rows, key=lambda item: item["stage"]),
        "offline_benchmark_status": "not_configured",
        "offline_benchmark_note": "Live checks prove pipeline integrity. Retrieval relevance and answer faithfulness require verified benchmark cases.",
        "sample_limit": 1000,
        "sample_limit_reached": len(traces) == 1000,
    }


@router.get("/rag/traces")
async def rag_observability_traces(
    hours: int = Query(24, ge=1, le=720),
    limit: int = Query(50, ge=1, le=200),
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    traces = await _recent_rag_traces(current_user, hours, limit=1000)
    return {"traces": [_serialize(trace) for trace in traces[:limit]], "count": len(traces[:limit])}


@router.get("/rag/traces/{trace_id}")
async def rag_observability_trace(
    trace_id: str,
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    trace = await models.ObservabilityTrace.find_one(
        models.ObservabilityTrace.trace_id == trace_id,
        models.ObservabilityTrace.user_id == str(current_user.user_id),
    )
    if not trace or not _is_rag_trace(trace):
        raise HTTPException(status_code=404, detail="RAG trace not found")
    return _serialize(trace, detail=True)


@router.get("/traces")
async def observability_traces(
    hours: int = Query(24, ge=1, le=720),
    limit: int = Query(50, ge=1, le=200),
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    traces = await _recent_traces(current_user, hours, limit)
    return {"traces": [_serialize(trace) for trace in traces], "count": len(traces)}


@router.get("/traces/{trace_id}")
async def observability_trace(
    trace_id: str,
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    trace = await models.ObservabilityTrace.find_one(
        models.ObservabilityTrace.trace_id == trace_id,
        models.ObservabilityTrace.user_id == str(current_user.user_id),
    )
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    return _serialize(trace, detail=True)
