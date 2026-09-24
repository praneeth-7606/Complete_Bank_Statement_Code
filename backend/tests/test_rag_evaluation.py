import asyncio
import json
from types import SimpleNamespace

from app.rag_evaluation import evaluate_rag_benchmark, evaluate_rag_run
from app.rag_logger import RAGLogger


def _score_map(scores):
    return {score["name"]: score for score in scores}


def test_online_rag_evaluation_checks_deterministic_aggregation_grounding():
    plan = SimpleNamespace(
        query_type="analytical", needs_mongo=True, needs_vector=False,
        needs_aggregation=True, limit=100,
    )
    docs = [{"transaction_id": "txn-1"}, {"transaction_id": "txn-2"}]
    context = SimpleNamespace(transaction_count=2, total_debit=1250.0, total_credit=200.0, net_flow=-1050.0)
    response = {
        "answer": "Across two transactions, total spent was Rs 1,250.00, total received was Rs 200.00, and net cash flow was Rs -1,050.00.",
        "metrics": [],
        "transactions": docs,
    }

    scores = _score_map(evaluate_rag_run(
        plan=plan, raw_documents=docs, reranked_documents=docs,
        context=context, response=response,
    ))

    assert scores["rag_plan_schema_valid"]["passed"] is True
    assert scores["rag_rerank_integrity"]["passed"] is True
    assert scores["rag_context_integrity"]["passed"] is True
    assert scores["rag_response_schema"]["passed"] is True
    assert scores["rag_aggregate_answer_grounded"]["passed"] is True


def test_offline_benchmark_reports_ranked_retrieval_metrics():
    scores = _score_map(evaluate_rag_benchmark(
        {"relevant_transaction_ids": ["txn-1", "txn-2"], "expected_plan": {"query_type": "semantic"}},
        {"retrieved_transaction_ids": ["txn-1", "txn-3", "txn-2"], "plan": {"query_type": "semantic"}},
    ))

    assert scores["rag_plan_exact_match"]["passed"] is True
    assert scores["rag_retrieval_precision_at_k"]["value"] == 2 / 3
    assert scores["rag_retrieval_recall_at_k"]["value"] == 1.0
    assert scores["rag_retrieval_mrr"]["value"] == 1.0


def test_rag_logger_keeps_parallel_request_contexts_isolated(tmp_path):
    log_file = tmp_path / "logs" / "rag.jsonl"
    rag_log = RAGLogger(str(log_file))

    async def write_entry(user_id, delay):
        rag_log.new_request(user_id)
        await asyncio.sleep(delay)
        rag_log.log_step("TEST", {"user": user_id})

    async def scenario():
        await asyncio.gather(write_entry("user-a", 0.01), write_entry("user-b", 0))

    asyncio.run(scenario())
    entries = [json.loads(line) for line in log_file.read_text(encoding="utf-8").splitlines()]
    assert {entry["user_id"] for entry in entries} == {"user-a", "user-b"}
    assert len({entry["request_id"] for entry in entries}) == 2
