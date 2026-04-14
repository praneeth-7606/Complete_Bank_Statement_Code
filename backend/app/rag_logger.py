"""
Enhanced RAGLogger — structured JSON Lines with per-step typed payloads.
Drop-in replacement for the RAGLogger in rag_pipeline.py.

Every log entry is a single JSON line:
  {"session": "...", "request_id": "...", "user_id": "...",
   "timestamp": "...", "step": "...", "level": "...",
   "elapsed_ms": 123, "data": {...}}

Grep examples:
  grep '"step":"PLAN"'              logs/rag_workflow.log | jq .data.filters
  grep '"level":"ERROR"'            logs/rag_workflow.log | jq .
  grep '"user_id":"usr_xyz"'        logs/rag_workflow.log | jq .
  grep '"hit_max_iterations":true'  logs/rag_workflow.log | jq .
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import re
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# PII masking helpers
# ──────────────────────────────────────────────────────────────

_ACCOUNT_RE = re.compile(r"\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b")
_UPI_RE     = re.compile(r"\b[\w.\-]+@[\w]+\b")

def _mask_pii(value: str) -> str:
    """Redact account numbers and UPI IDs from log strings."""
    value = _ACCOUNT_RE.sub("****-****-****-****", value)
    value = _UPI_RE.sub("***@***", value)
    return value

def _sanitize(obj: Any, depth: int = 0) -> Any:
    """Recursively sanitize dict/list values to remove PII."""
    if depth > 6:
        return obj
    if isinstance(obj, str):
        return _mask_pii(obj)
    if isinstance(obj, dict):
        return {k: _sanitize(v, depth + 1) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(i, depth + 1) for i in obj[:20]]  # cap list length in logs
    return obj


# ──────────────────────────────────────────────────────────────
# Step-specific payload builders
# ──────────────────────────────────────────────────────────────

def _payload_pipeline_start(query: str, user_id: str) -> Dict:
    return {"query": query, "query_length": len(query), "user_id": user_id}

def _payload_validation(is_valid: bool, error: Optional[str], query_length: int) -> Dict:
    return {"is_valid": is_valid, "query_length": query_length, "error": error}

def _payload_plan(plan: Any) -> Dict:
    d = plan.model_dump()
    return {
        "needs_mongo":       d.get("needs_mongo"),
        "needs_vector":      d.get("needs_vector"),
        "needs_aggregation": d.get("needs_aggregation"),
        "query_type":        d.get("query_type"),
        "intent":            d.get("intent", ""),
        "limit":             d.get("limit"),
        "filters_keys":      list(d.get("filters", {}).keys()),  # log keys, not values (amounts/dates)
        "vector_query":      d.get("vector_query", ""),
        "sort":              d.get("sort"),
        "date_range_desc":   d.get("date_range_description", ""),
    }

def _payload_retrieval(
    mongo_enabled: bool,
    vector_enabled: bool,
    mongo_count: int,
    vector_count: int,
    merged_count: int,
    source_errors: List[str],
) -> Dict:
    return {
        "mongo_enabled":       mongo_enabled,
        "vector_enabled":      vector_enabled,
        "mongo_docs":          mongo_count,
        "vector_docs":         vector_count,
        "merged_after_dedup":  merged_count,
        "duplicate_dropped":   mongo_count + vector_count - merged_count,
        "source_errors":       source_errors,
    }

def _payload_rerank(
    input_docs: int,
    output_docs: int,
    top_score: Optional[float],
    skipped_reason: Optional[str],
) -> Dict:
    return {
        "input_docs":     input_docs,
        "output_docs":    output_docs,
        "top_score":      round(top_score, 3) if top_score is not None else None,
        "skipped_reason": skipped_reason,
    }

def _payload_context(ctx: Any, anomalies_count: int) -> Dict:
    return {
        "txn_count":           ctx.transaction_count,
        "total_debit":         round(ctx.total_debit, 2),
        "total_credit":        round(ctx.total_credit, 2),
        "net_flow":            round(ctx.net_flow, 2),
        "avg_txn_value":       round(ctx.avg_transaction_value, 2),
        "category_count":      len(ctx.category_breakdown),
        "top_category":        ctx.most_frequent_category,
        "anomaly_count":       anomalies_count,
        "date_range":          ctx.date_range,
        "monthly_trend_count": len(ctx.monthly_trends),
    }

def _payload_context_validation(is_valid: bool, error: Optional[str]) -> Dict:
    return {"is_valid": is_valid, "error": error}

def _payload_agent(
    tool_calls: List[str],
    output_length: int,
    hit_max_iterations: bool,
    output_preview: str,
) -> Dict:
    return {
        "tool_calls":          tool_calls,
        "tool_call_count":     len(tool_calls),
        "output_length":       output_length,
        "hit_max_iterations":  hit_max_iterations,
        "output_preview":      output_preview[:200],
    }

def _payload_response_gen(
    json_parse_success: bool,
    fallback_used: bool,
    answer_length: int,
    metrics_count: int,
    insights_count: int,
    txn_in_response: int,
) -> Dict:
    return {
        "json_parse_success": json_parse_success,
        "fallback_used":      fallback_used,
        "answer_length":      answer_length,
        "metrics_count":      metrics_count,
        "insights_count":     insights_count,
        "txn_in_response":    txn_in_response,
    }

def _payload_pipeline_complete(
    elapsed_ms: float,
    txn_count: int,
    answer_length: int,
    steps_completed: int,
) -> Dict:
    return {
        "elapsed_ms":      round(elapsed_ms),
        "txn_count":       txn_count,
        "answer_length":   answer_length,
        "steps_completed": steps_completed,
    }


# ──────────────────────────────────────────────────────────────
# RAGLogger class
# ──────────────────────────────────────────────────────────────

class RAGLogger:
    """
    Structured JSON Lines logger for the Agentic RAG pipeline.

    Usage:
        logger = RAGLogger()
        logger.new_request(user_id="usr_abc")

        logger.log_pipeline_start(query, user_id)
        logger.log_plan(plan)
        logger.log_retrieval(mongo_enabled, vector_enabled, ...)
        ...
        logger.log_pipeline_complete(elapsed_ms, txn_count, answer_length, steps_completed)

    Or use the low-level log_step() if you need a custom step:
        logger.log_step("CUSTOM_STEP", {"key": "value"})
    """

    def __init__(self, log_file: str = "logs/rag_workflow.log"):
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        self.log_file = log_file
        self._session_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self._request_id: str = ""
        self._user_id: str = ""
        self._pipeline_start: Optional[datetime.datetime] = None

    def new_request(self, user_id: str) -> str:
        """Call at the start of each run() call. Returns the request_id."""
        self._request_id = f"req_{uuid.uuid4().hex[:8]}"
        self._user_id = user_id
        self._pipeline_start = datetime.datetime.now()
        return self._request_id

    def _elapsed_ms(self) -> float:
        if not self._pipeline_start:
            return 0.0
        return (datetime.datetime.now() - self._pipeline_start).total_seconds() * 1000

    def log_step(self, step: str, data: Any, level: str = "INFO") -> None:
        """
        Low-level: write one JSON line to the log file.
        Use the typed helpers below (log_plan, log_context, etc.) when possible.
        """
        entry = {
            "session":    self._session_id,
            "request_id": self._request_id,
            "user_id":    self._user_id,
            "timestamp":  datetime.datetime.now().isoformat(timespec="milliseconds"),
            "step":       step,
            "level":      level,
            "elapsed_ms": round(self._elapsed_ms()),
            "data":       _sanitize(data),
        }
        line = json.dumps(entry, default=str, ensure_ascii=False)
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(line + "\n")

        log_fn = getattr(logger, level.lower(), logger.info)
        log_fn("[%s] %s", step, line[:300])

    # ── Typed log helpers ──────────────────────────────────────

    def log_pipeline_start(self, query: str, user_id: str) -> None:
        self.log_step("PIPELINE_START", _payload_pipeline_start(query, user_id))

    def log_validation(self, is_valid: bool, error: Optional[str], query_length: int) -> None:
        level = "INFO" if is_valid else "WARNING"
        self.log_step("VALIDATION", _payload_validation(is_valid, error, query_length), level)

    def log_plan(self, plan: Any, safety_corrections: Optional[List[str]] = None) -> None:
        payload = _payload_plan(plan)
        if safety_corrections:
            payload["safety_corrections"] = safety_corrections
        self.log_step("PLAN", payload)

    def log_retrieval(
        self,
        mongo_enabled: bool,
        vector_enabled: bool,
        mongo_count: int = 0,
        vector_count: int = 0,
        merged_count: int = 0,
        source_errors: Optional[List[str]] = None,
    ) -> None:
        level = "WARNING" if source_errors else "INFO"
        payload = _payload_retrieval(
            mongo_enabled, vector_enabled,
            mongo_count, vector_count, merged_count,
            source_errors or []
        )
        if merged_count == 0:
            level = "WARNING"
            payload["warning"] = "Zero documents retrieved — check filters and DB connectivity"
        self.log_step("RETRIEVAL", payload, level)

    def log_rerank(
        self,
        input_docs: int,
        output_docs: int,
        top_score: Optional[float] = None,
        skipped_reason: Optional[str] = None,
    ) -> None:
        self.log_step("RERANK", _payload_rerank(input_docs, output_docs, top_score, skipped_reason))

    def log_context(self, ctx: Any) -> None:
        payload = _payload_context(ctx, len(ctx.anomalies))
        if ctx.transaction_count == 0:
            self.log_step("CONTEXT", payload, "WARNING")
        else:
            self.log_step("CONTEXT", payload)

    def log_context_validation(self, is_valid: bool, error: Optional[str]) -> None:
        level = "INFO" if is_valid else "WARNING"
        self.log_step("CONTEXT_VALIDATION", _payload_context_validation(is_valid, error), level)

    def log_agent(
        self,
        tool_calls: List[str],
        output: str,
        hit_max_iterations: bool = False,
    ) -> None:
        level = "WARNING" if hit_max_iterations else "INFO"
        payload = _payload_agent(tool_calls, len(output), hit_max_iterations, output)
        if hit_max_iterations:
            payload["warning"] = "Agent hit max_iterations — response may be incomplete"
        self.log_step("AGENT_OUTPUT", payload, level)

    def log_response_gen(
        self,
        json_parse_success: bool,
        fallback_used: bool,
        answer: str,
        metrics: list,
        insights: list,
        transactions: list,
    ) -> None:
        level = "WARNING" if (not json_parse_success or fallback_used) else "INFO"
        self.log_step(
            "RESPONSE_GENERATOR",
            _payload_response_gen(
                json_parse_success, fallback_used,
                len(answer), len(metrics), len(insights), len(transactions)
            ),
            level
        )

    def log_pipeline_complete(
        self,
        txn_count: int,
        answer_length: int,
        steps_completed: int,
    ) -> None:
        self.log_step(
            "PIPELINE_COMPLETE",
            _payload_pipeline_complete(
                self._elapsed_ms(), txn_count, answer_length, steps_completed
            )
        )

    def log_error(self, step: str, error: Exception, context: Optional[Dict] = None) -> None:
        payload = {
            "error_type":    type(error).__name__,
            "error_message": str(error),
            "context":       context or {},
        }
        self.log_step(step, payload, "ERROR")


# ──────────────────────────────────────────────────────────────
# Global singleton (mirrors original usage pattern)
# ──────────────────────────────────────────────────────────────
rag_logger = RAGLogger()
