"""Authenticated API used by the in-app observability dashboard."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
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
    traces = await models.ObservabilityTrace.find(_user_filter(current_user)).to_list()
    def aware_started_at(trace):
        started_at = trace.started_at
        if started_at is None:
            return cutoff
        return started_at.replace(tzinfo=timezone.utc) if started_at.tzinfo is None else started_at

    traces = [trace for trace in traces if aware_started_at(trace) >= cutoff]
    traces.sort(key=aware_started_at, reverse=True)
    return traces[:limit]


@router.get("/summary")
async def observability_summary(
    hours: int = Query(24, ge=1, le=720),
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    traces = await _recent_traces(current_user, hours)
    llm_calls = [call for trace in traces for call in (trace.llm_calls or [])]
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
