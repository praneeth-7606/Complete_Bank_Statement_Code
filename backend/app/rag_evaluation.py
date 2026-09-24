"""Safe RAG evaluation helpers.

Online checks prove pipeline integrity and financial grounding where the
application has deterministic evidence. They deliberately do *not* claim
retrieval relevance or answer faithfulness without a human-verified benchmark.
Those offline metrics are exposed through ``evaluate_rag_benchmark`` so a
future benchmark runner can use the same score names and thresholds.
"""

from __future__ import annotations

import math
import re
from typing import Any, Iterable

from .observability import current_trace


RAG_EVALUATOR_VERSION = "rag-v1"
_PLAN_TYPES = {"simple", "analytical", "semantic", "comparison", "trend"}


def _score(name: str, value: float | None, passed: bool | None, **details: Any) -> dict[str, Any]:
    return {"name": name, "value": value, "passed": passed, "details": details}


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)


def _document_id(document: dict[str, Any]) -> str:
    return str(document.get("transaction_id") or document.get("id") or document.get("_id") or "")


def _contains_amount(answer: str, value: Any) -> bool:
    """Check a deterministic monetary value without relying on LLM judgement."""
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return False
    normalized_answer = answer.replace(",", "")
    # Accept INR formatting variants such as 1234, 1234.0 and 1234.00.
    pattern = rf"(?<![\d.]){re.escape(f'{amount:.2f}')}|(?<![\d.]){re.escape(str(int(amount)))}(?:\.0{{1,2}})?(?![\d.])"
    return re.search(pattern, normalized_answer) is not None


def evaluate_rag_run(
    *,
    plan: Any,
    raw_documents: list[dict[str, Any]],
    reranked_documents: list[dict[str, Any]],
    context: Any,
    response: dict[str, Any] | None,
    source_errors: Iterable[str] = (),
    response_meta: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Evaluate one live RAG request using only safe, deterministic evidence."""
    source_errors = list(source_errors or [])
    response_meta = response_meta or {}
    plan_valid = (
        _get(plan, "query_type") in _PLAN_TYPES
        and isinstance(_get(plan, "needs_mongo"), bool)
        and isinstance(_get(plan, "needs_vector"), bool)
        and isinstance(_get(plan, "needs_aggregation"), bool)
        and isinstance(_get(plan, "limit"), int)
        and 1 <= _get(plan, "limit") <= 1000
    )

    raw_ids = {_document_id(doc) for doc in raw_documents if _document_id(doc)}
    ranked_ids = {_document_id(doc) for doc in reranked_documents if _document_id(doc)}
    rerank_integrity = None
    if raw_documents:
        rerank_integrity = len(reranked_documents) <= len(raw_documents) and ranked_ids.issubset(raw_ids)

    context_count = int(_get(context, "transaction_count", 0) or 0)
    context_integrity = None
    if reranked_documents:
        context_integrity = context_count == len(reranked_documents)

    response_valid = None
    aggregate_grounding = None
    if response is not None:
        response_valid = (
            isinstance(response.get("answer"), str)
            and bool(response.get("answer").strip())
            and isinstance(response.get("metrics"), list)
            and isinstance(response.get("transactions"), list)
        )
        if _get(plan, "needs_aggregation") and response_valid:
            answer = response["answer"]
            aggregate_grounding = all(
                _contains_amount(answer, _get(context, field, 0))
                for field in ("total_debit", "total_credit", "net_flow")
            )

    scores = [
        _score("rag_plan_schema_valid", float(plan_valid), plan_valid, evaluator_version=RAG_EVALUATOR_VERSION),
        _score("rag_retrieval_sources_healthy", float(not source_errors), not source_errors,
               source_error_count=len(source_errors), evaluator_version=RAG_EVALUATOR_VERSION),
        _score("rag_retrieval_result_available", 1.0 if raw_documents else None,
               True if raw_documents else None, raw_docs=len(raw_documents), evaluator_version=RAG_EVALUATOR_VERSION),
        _score("rag_rerank_integrity", float(rerank_integrity) if rerank_integrity is not None else None,
               rerank_integrity, raw_docs=len(raw_documents), reranked_docs=len(reranked_documents),
               evaluator_version=RAG_EVALUATOR_VERSION),
        _score("rag_context_integrity", float(context_integrity) if context_integrity is not None else None,
               context_integrity, context_transaction_count=context_count, evaluator_version=RAG_EVALUATOR_VERSION),
        _score("rag_response_schema", float(response_valid) if response_valid is not None else None,
               response_valid, response_json_valid=bool(response_meta.get("json_parse_success")),
               response_fallback=bool(response_meta.get("fallback_used")), evaluator_version=RAG_EVALUATOR_VERSION),
        _score("rag_aggregate_answer_grounded", float(aggregate_grounding) if aggregate_grounding is not None else None,
               aggregate_grounding, evaluator_version=RAG_EVALUATOR_VERSION),
    ]

    trace = current_trace()
    if trace:
        for item in scores:
            trace.record_evaluation(
                item["name"], item["value"], item["passed"], item["details"],
                evaluator_version=RAG_EVALUATOR_VERSION,
            )
        measured = [item for item in scores if item["passed"] is not None]
        trace.add_event(
            "rag.evaluation",
            kind="evaluation",
            status="failed" if any(item["passed"] is False for item in measured) else "success",
            metadata={
                "checks": len(measured),
                "failed_checks": sum(item["passed"] is False for item in measured),
                "not_evaluated_checks": len(scores) - len(measured),
                "evaluator_version": RAG_EVALUATOR_VERSION,
            },
        )
    return scores


def evaluate_rag_benchmark(expected: dict[str, Any], actual: dict[str, Any]) -> list[dict[str, Any]]:
    """Score an offline, human-verified RAG benchmark case.

    ``expected`` contains ``relevant_transaction_ids`` and optional
    ``expected_plan``. ``actual`` contains ``retrieved_transaction_ids`` and
    an optional ``plan``. This intentionally runs outside request telemetry so
    CI can fail a build without requiring provider credentials.
    """
    relevant = [str(value) for value in expected.get("relevant_transaction_ids", [])]
    retrieved = [str(value) for value in actual.get("retrieved_transaction_ids", [])]
    relevant_set = set(relevant)
    retrieved_set = set(retrieved)
    matches = [value for value in retrieved if value in relevant_set]
    precision = len(matches) / len(retrieved) if retrieved else 0.0
    recall = len(set(matches)) / len(relevant_set) if relevant_set else None
    first_rank = next((index + 1 for index, value in enumerate(retrieved) if value in relevant_set), None)
    reciprocal_rank = 1 / first_rank if first_rank else 0.0
    dcg = sum(1 / math.log2(index + 2) for index, value in enumerate(retrieved) if value in relevant_set)
    ideal = sum(1 / math.log2(index + 2) for index in range(min(len(relevant_set), len(retrieved))))
    ndcg = dcg / ideal if ideal else None

    expected_plan = expected.get("expected_plan")
    actual_plan = actual.get("plan")
    plan_exact = None
    if expected_plan is not None and actual_plan is not None:
        plan_exact = all(_get(actual_plan, key) == value for key, value in expected_plan.items())

    return [
        _score("rag_plan_exact_match", float(plan_exact) if plan_exact is not None else None, plan_exact),
        _score("rag_retrieval_precision_at_k", precision, precision >= 0.90),
        _score("rag_retrieval_recall_at_k", recall, recall >= 0.90 if recall is not None else None),
        _score("rag_retrieval_mrr", reciprocal_rank, reciprocal_rank >= 0.90),
        _score("rag_retrieval_ndcg", ndcg, ndcg >= 0.90 if ndcg is not None else None),
    ]
