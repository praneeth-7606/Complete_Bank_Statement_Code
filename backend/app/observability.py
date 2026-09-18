"""Application observability for the bank-statement analyser.

This module deliberately stores metrics and safe metadata only.  Prompts,
PDF passwords, statement contents, API keys, and transaction descriptions are
never written to the observability collection.
"""

from __future__ import annotations

import hashlib
import logging
import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Iterator, Optional

from langchain_core.callbacks import BaseCallbackHandler

logger = logging.getLogger("financial_statement_analyser.observability")

_current_trace: ContextVar["TraceContext | None"] = ContextVar("observability_trace", default=None)

# USD per one million tokens.  These are estimates used only when a provider
# reports usage; unknown models are shown as $0 with their usage source marked.
MODEL_PRICING = {
    "gemini-3.8-flash": {"input": 0.10, "output": 0.40},
    "gemini-2.5-flash": {"input": 0.15, "output": 0.60},
    "gemini-embedding": {"input": 0.15, "output": 0.0},
    "gpt-oss-20b": {"input": 0.075, "output": 0.30},
    "llama-3.3-70b": {"input": 0.59, "output": 0.79},
    "glm-4.7-flash": {"input": 0.20, "output": 0.40},
    "glm-4.6v-flash": {"input": 0.20, "output": 0.40},
    "mistral-ocr": {"input": 0.0, "output": 0.0},
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _model_price(model: str) -> dict[str, float] | None:
    model_lower = (model or "").lower()
    for name, price in MODEL_PRICING.items():
        if name in model_lower:
            return price
    return None


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    price = _model_price(model)
    if not price:
        return 0.0
    return round(
        (input_tokens * price["input"] + output_tokens * price["output"]) / 1_000_000,
        8,
    )


def _usage_from_response(response: Any) -> tuple[int, int, str]:
    """Normalize LangChain/OpenAI/Google usage metadata."""
    message = None
    try:
        message = response.generations[0][0].message
    except Exception:
        pass

    candidates = [
        getattr(response, "usage_metadata", None),
        getattr(response, "response_metadata", None),
        getattr(message, "usage_metadata", None),
        getattr(message, "response_metadata", None),
        getattr(response, "llm_output", None),
        response if isinstance(response, dict) else None,
    ]
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        usage = candidate.get("token_usage") or candidate.get("usage") or candidate
        if not isinstance(usage, dict):
            continue
        input_tokens = usage.get("input_tokens", usage.get("prompt_tokens", 0))
        output_tokens = usage.get("output_tokens", usage.get("completion_tokens", 0))
        try:
            return int(input_tokens or 0), int(output_tokens or 0), "provider"
        except (TypeError, ValueError):
            continue
    return 0, 0, "unavailable"


def current_trace() -> "TraceContext | None":
    return _current_trace.get()


def bind_trace(trace: "TraceContext"):
    return _current_trace.set(trace)


def reset_trace(token) -> None:
    _current_trace.reset(token)


def set_trace_user(user_id: Any, operation: str | None = None) -> None:
    trace = current_trace()
    if trace:
        trace.set_user(user_id, operation)


class TraceContext:
    """Request-scoped trace that can be updated by background tasks."""

    def __init__(self, route: str, request_id: str | None = None):
        self.trace_id = str(uuid.uuid4())
        self.request_id = request_id or str(uuid.uuid4())
        self.route = route
        self.operation = route
        self.user_id: Optional[str] = None
        self.started_at = _now()
        self.ended_at: Optional[datetime] = None
        self.status = "running"
        self.events: list[dict[str, Any]] = []
        self.llm_calls: list[dict[str, Any]] = []
        self._persist_task = None

    def set_user(self, user_id: Any, operation: str | None = None) -> None:
        self.user_id = str(user_id) if user_id is not None else None
        if operation:
            self.operation = operation

    def add_event(
        self,
        name: str,
        kind: str = "workflow",
        status: str = "success",
        duration_ms: float = 0.0,
        metadata: Optional[dict[str, Any]] = None,
        error_type: Optional[str] = None,
    ) -> None:
        self.events.append({
            "event_id": str(uuid.uuid4()),
            "name": name,
            "kind": kind,
            "status": status,
            "duration_ms": round(duration_ms, 2),
            "metadata": metadata or {},
            "error_type": error_type,
            "timestamp": _now().isoformat(),
        })
        self.schedule_persist()

    def record_llm(
        self,
        provider: str,
        model: str,
        duration_ms: float,
        input_tokens: int = 0,
        output_tokens: int = 0,
        status: str = "success",
        fallback: bool = False,
        error: Optional[str] = None,
        kind: str = "llm",
    ) -> None:
        token_source = "provider" if input_tokens or output_tokens else "unavailable"
        self.llm_calls.append({
            "call_id": str(uuid.uuid4()),
            "kind": kind,
            "provider": provider,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "token_source": token_source,
            "cost_usd": estimate_cost(model, input_tokens, output_tokens),
            "duration_ms": round(duration_ms, 2),
            "status": status,
            "fallback": fallback,
            "error": str(error)[:500] if error else None,
            "timestamp": _now().isoformat(),
        })
        self.add_event(
            name=f"{provider}/{model}",
            kind=kind,
            status=status,
            duration_ms=duration_ms,
            metadata={
                "provider": provider,
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "cost_usd": estimate_cost(model, input_tokens, output_tokens),
                "fallback": fallback,
                "token_source": token_source,
            },
            error_type=type(error).__name__ if isinstance(error, Exception) else None,
        )

    def finish(self, status: str = "success") -> None:
        self.status = status
        self.ended_at = _now()
        self.schedule_persist()

    def _document(self) -> dict[str, Any]:
        ended = self.ended_at or _now()
        duration_ms = round((ended - self.started_at).total_seconds() * 1000, 2)
        total_input = sum(item["input_tokens"] for item in self.llm_calls)
        total_output = sum(item["output_tokens"] for item in self.llm_calls)
        return {
            "trace_id": self.trace_id,
            "request_id": self.request_id,
            "user_id": self.user_id,
            "route": self.route,
            "operation": self.operation,
            "status": self.status,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_ms": duration_ms,
            "events": self.events[-500:],
            "llm_calls": self.llm_calls[-200:],
            "metrics": {
                "llm_calls": len(self.llm_calls),
                "successful_llm_calls": sum(1 for item in self.llm_calls if item["status"] == "success"),
                "failed_llm_calls": sum(1 for item in self.llm_calls if item["status"] == "failed"),
                "fallback_calls": sum(1 for item in self.llm_calls if item["fallback"]),
                "input_tokens": total_input,
                "output_tokens": total_output,
                "total_tokens": total_input + total_output,
                "estimated_cost_usd": round(sum(item["cost_usd"] for item in self.llm_calls), 8),
                "event_count": len(self.events),
                "error_count": sum(1 for item in self.events if item["status"] == "failed"),
            },
            "created_at": self.started_at,
        }

    def schedule_persist(self) -> None:
        try:
            import asyncio
            loop = asyncio.get_running_loop()
            if self._persist_task is None or self._persist_task.done():
                self._persist_task = loop.create_task(self.persist())
        except RuntimeError:
            pass

    async def persist(self) -> None:
        try:
            from . import models
            payload = self._document()
            existing = await models.ObservabilityTrace.find_one(
                models.ObservabilityTrace.trace_id == self.trace_id
            )
            if existing:
                for key, value in payload.items():
                    setattr(existing, key, value)
                await existing.save()
            else:
                await models.ObservabilityTrace(**payload).insert()
        except Exception:
            # Telemetry must never break statement processing or chat.
            logger.exception("Unable to persist observability trace", extra={"trace_id": self.trace_id})

    async def flush(self) -> None:
        if self._persist_task and not self._persist_task.done():
            try:
                await self._persist_task
            except Exception:
                logger.exception("Unable to flush observability trace")
        await self.persist()


def new_trace(route: str, request_id: str | None = None) -> TraceContext:
    return TraceContext(route=route, request_id=request_id)


class ObservabilityCallbackHandler(BaseCallbackHandler):
    """Captures actual provider calls made through LangChain runnables."""

    def __init__(self, provider: str, model: str, fallback: bool = False, kind: str = "llm"):
        self.provider = provider
        self.model = model
        self.fallback = fallback
        self.kind = kind
        self._starts: dict[str, float] = {}

    def on_llm_start(self, serialized: dict[str, Any], prompts: list[str], *, run_id, **kwargs: Any) -> None:
        self._starts[str(run_id)] = time.perf_counter()

    def on_chat_model_start(self, serialized: dict[str, Any], messages: list[Any], *, run_id, **kwargs: Any) -> None:
        """Chat models use a separate callback lifecycle in LangChain."""
        self._starts[str(run_id)] = time.perf_counter()

    def on_llm_end(self, response: Any, *, run_id, **kwargs: Any) -> None:
        started = self._starts.pop(str(run_id), time.perf_counter())
        input_tokens, output_tokens, _ = _usage_from_response(response)
        trace = current_trace()
        if trace:
            trace.record_llm(
                provider=self.provider,
                model=self.model,
                duration_ms=(time.perf_counter() - started) * 1000,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                fallback=self.fallback,
                kind=self.kind,
            )

    def on_chat_model_end(self, response: Any, *, run_id, **kwargs: Any) -> None:
        self.on_llm_end(response, run_id=run_id, **kwargs)

    def on_llm_error(self, error: BaseException, *, run_id, **kwargs: Any) -> None:
        started = self._starts.pop(str(run_id), time.perf_counter())
        trace = current_trace()
        if trace:
            trace.record_llm(
                provider=self.provider,
                model=self.model,
                duration_ms=(time.perf_counter() - started) * 1000,
                status="failed",
                fallback=self.fallback,
                error=str(error),
                kind=self.kind,
            )

    def on_chat_model_error(self, error: BaseException, *, run_id, **kwargs: Any) -> None:
        self.on_llm_error(error, run_id=run_id, **kwargs)


def instrument_model(model: Any, provider: str, model_name: str, fallback: bool = False, kind: str = "llm") -> Any:
    """Attach a provider-specific callback without changing caller APIs."""
    handler = ObservabilityCallbackHandler(provider, model_name, fallback=fallback, kind=kind)
    try:
        return model.with_config(callbacks=[handler])
    except Exception:
        logger.warning("Unable to attach LLM observability callback", exc_info=True)
        return model


class _ExternalCall:
    def __init__(self):
        self.response: Any = None


@contextmanager
def observe_external_llm(provider: str, model: str, kind: str = "llm") -> Iterator[_ExternalCall]:
    """Instrument SDK calls that do not go through LangChain."""
    span = _ExternalCall()
    started = time.perf_counter()
    try:
        yield span
    except Exception as exc:
        trace = current_trace()
        if trace:
            trace.record_llm(provider, model, (time.perf_counter() - started) * 1000, status="failed", error=str(exc), kind=kind)
        raise
    else:
        input_tokens, output_tokens, _ = _usage_from_response(span.response)
        trace = current_trace()
        if trace:
            trace.record_llm(provider, model, (time.perf_counter() - started) * 1000, input_tokens, output_tokens, kind=kind)
