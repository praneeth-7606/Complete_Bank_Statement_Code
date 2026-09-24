"""Part 1 lifecycle tests use in-memory Mongo and deterministic provider doubles."""
import asyncio
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI

from app import models, post_processing, telemetry
from app.config import settings
from app.database import init_db
from app.observability import TraceContext, bind_trace, reset_trace
from app.observability_router import router
from app.auth_utils import get_current_user


@pytest.mark.parametrize("vector_valid", [True, False])
def test_persistence_worker_and_tenant_isolated_dashboard(monkeypatch, vector_valid):
    monkeypatch.setattr(settings, "MONGO_MOCK", True)
    monkeypatch.setattr(settings, "PINECONE_API_KEY", "test-only")
    monkeypatch.setattr(telemetry, "_score_config", None)

    async def scenario():
        await init_db()
        execution = TraceContext("/process-statement/")
        execution.set_user("owner", "statement_upload")
        token = bind_trace(execution)
        state = {"streaming_id": "upload-test", "user_id": "owner", "file_bytes": b"fake-pdf",
                 "file_path": "synthetic.pdf", "categorized_transactions": [
                     {"date": "2026-01-01", "description": "Synthetic merchant", "debit": "0.10", "credit": "0.00", "amount": "0.10", "category": "Food"}]}
        upload = await post_processing.persist_statement_and_enqueue(state)
        # Replay must not add a duplicate transaction.
        await post_processing.persist_statement_and_enqueue(state)
        assert await models.Transaction.find({"upload_id": "upload-test"}).count() == 1
        execution.finish()
        await execution.flush()
        reset_trace(token)
        job = await models.ProcessingJob.find_one({"upload_id": "upload-test"})
        assert job.parent_trace_id == execution.trace_id

        stop = asyncio.Event()
        class Analyst:
            async def generate_financial_insights(self, transactions):
                stop.set()
                return {"insights": ["Synthetic insight"]}
        class Vectors:
            def __init__(self, **kwargs):
                pass
            async def add_transactions(self, transactions):
                assert len(transactions) == 1
            async def verify_transactions(self, transactions):
                return vector_valid
        from app import vector_store_pinecone
        monkeypatch.setattr(vector_store_pinecone, "PineconeVectorStore", Vectors)
        monkeypatch.setattr(post_processing.agents, "FinancialAnalystAgent", Analyst)
        await post_processing.worker_loop(stop, "test-worker")
        upload = await models.Upload.find_one({"upload_id": "upload-test"})
        assert upload.status == ("completed" if vector_valid else "retrying")
        child = await models.ObservabilityTrace.find_one({"parent_trace_id": execution.trace_id})
        assert child and child.user_id == "owner"
        scores = {item["name"]: item for item in child.evaluation_scores}
        assert scores["vector_readback_integrity"]["passed"] == vector_valid
        assert child.status == ("success" if vector_valid else "failed")
        assert scores["insights_factual_accuracy"]["passed"] is None

        api = FastAPI()
        api.include_router(router)
        api.dependency_overrides[get_current_user] = lambda: SimpleNamespace(user_id="owner")
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api), base_url="http://test") as client:
            detail = await client.get(f"/observability/traces/{child.trace_id}")
            assert detail.status_code == 200
            summary = (await client.get("/observability/summary")).json()
            assert (summary["evaluation_pass_rate"] == 1) == vector_valid
            assert summary["evaluation_not_measured"] == 1
            api.dependency_overrides[get_current_user] = lambda: SimpleNamespace(user_id="other")
            assert (await client.get(f"/observability/traces/{child.trace_id}")).status_code == 404
            assert (await client.get("/observability/traces")).json()["count"] == 0
    asyncio.run(scenario())


def test_score_export_handles_rejection_and_redacts_payload(monkeypatch):
    captured = []
    monkeypatch.setattr(telemetry, "_score_config", ("https://example.test", {"Authorization": "secret"}))
    class Client:
        def __init__(self, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def post(self, url, **kwargs):
            captured.append(kwargs["json"])
            return SimpleNamespace(raise_for_status=lambda: None, json=lambda: {"errors": [{"message": "rejected"}]})
    monkeypatch.setattr(httpx, "AsyncClient", Client)
    execution = TraceContext("/test")
    execution.otel_trace_id = "a" * 32
    execution.record_evaluation("consistency", 1, True, {"description": "SECRET"})
    assert asyncio.run(telemetry.export_scores(execution._document())) == "failed"
    first = captured[0]["batch"][0]["body"]["id"]
    asyncio.run(telemetry.export_scores(execution._document()))
    assert captured[1]["batch"][0]["body"]["id"] == first
    assert "SECRET" not in str(captured)
