import asyncio

from app.agentic_rag import HybridRetrievalLayer, QueryPlan


def test_hybrid_retrieval_preserves_legitimate_duplicate_ledger_rows(monkeypatch):
    layer = HybridRetrievalLayer(None)
    mongo_docs = [
        {
            "_id": "txn-1",
            "transaction_id": "txn-1",
            "user_id": "user-1",
            "date": "2026-08-01",
            "description": "same merchant",
            "amount": 5000.0,
            "debit": 5000.0,
            "credit": 0.0,
        },
        {
            "_id": "txn-2",
            "transaction_id": "txn-2",
            "user_id": "user-1",
            "date": "2026-08-01",
            "description": "same merchant",
            "amount": 5000.0,
            "debit": 5000.0,
            "credit": 0.0,
        },
    ]

    async def mongo_query(plan, user_id):
        return mongo_docs, None

    async def vector_query(plan, user_id):
        return [{"transaction_id": "None", **mongo_docs[0]}], None

    monkeypatch.setattr(layer, "_mongo_query", mongo_query)
    monkeypatch.setattr(layer, "_vector_query", vector_query)
    plan = QueryPlan(
        needs_mongo=True,
        needs_vector=True,
        needs_aggregation=False,
        query_type="semantic",
        vector_query="same merchant",
    )

    merged = asyncio.run(layer.retrieve(plan, "user-1"))

    assert len(merged) == 2
    assert {row["transaction_id"] for row in merged} == {"txn-1", "txn-2"}
