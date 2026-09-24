"""Durable persistence and enrichment for extracted statements.

The HTTP request stores verified transactions before returning. Slow, retryable
work (insights and vector indexing) is represented by a MongoDB job and claimed
with a lease, so a deploy or process crash cannot silently lose the work.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import socket
import uuid
from datetime import date, datetime, timedelta
from typing import Any, Dict, Optional

from pymongo import ReturnDocument

from . import agents, models
from .config import settings
from .finance import money
from .observability import current_trace, new_trace, bind_trace, reset_trace, observed_stage, observe_stage
from .telemetry import carrier, span, current_id
from .evaluation import persistence_integrity, insight_checks, publish, score

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.utcnow()


def _date_value(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    for pattern in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d %b %Y"):
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            continue
    raise ValueError(f"Unsupported transaction date: {text!r}")


def build_transaction_records(state: Dict[str, Any]) -> list[Dict[str, Any]]:
    """Create idempotent Decimal-based records without requiring a database."""
    upload_id = str(state["streaming_id"])
    user_id = str(state["user_id"])
    records: list[Dict[str, Any]] = []
    for index, transaction in enumerate(state.get("categorized_transactions") or []):
        debit = money(transaction.get("debit"))
        credit = money(transaction.get("credit"))
        amount = money(transaction.get("amount") or debit or credit)
        records.append({
            "transaction_id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"{user_id}:{upload_id}:{index}")),
            "date": _date_value(transaction.get("date")),
            "description": transaction.get("description") or "No description",
            "amount": amount,
            "debit": debit,
            "credit": credit,
            "category": transaction.get("category") or "Other",
            "upload_id": upload_id,
            "user_id": user_id,
        })
    return records


def build_transaction_documents(state: Dict[str, Any]) -> list[models.Transaction]:
    """Create Beanie documents from validated, testable transaction records."""
    return [models.Transaction(**record) for record in build_transaction_records(state)]


@observed_stage("mongo_persistence")
async def persist_statement_and_enqueue(state: Dict[str, Any]) -> models.Upload:
    """Persist transactions first, verify the write, then enqueue enrichment."""
    upload_id = str(state["streaming_id"])
    user_id = str(state["user_id"])
    transaction_documents = build_transaction_documents(state)
    if not transaction_documents:
        raise ValueError("No verified transactions are available to persist")

    upload = await models.Upload.find_one(
        models.Upload.upload_id == upload_id,
        models.Upload.user_id == user_id,
    )
    if upload is None:
        upload = models.Upload(
            upload_id=upload_id,
            file_hash=hashlib.sha256(state["file_bytes"]).hexdigest(),
            filename=state.get("file_path") or "statement.pdf",
            file_size_bytes=len(state["file_bytes"]),
            user_id=user_id,
        )

    # One lookup plus one bulk insert replaces the previous transaction-by-
    # transaction persistence pattern. Deterministic IDs make retries safe.
    existing = await models.Transaction.find(
        models.Transaction.user_id == user_id,
        models.Transaction.upload_id == upload_id,
    ).to_list()
    existing_ids = {transaction.transaction_id for transaction in existing}
    missing = [
        transaction
        for transaction in transaction_documents
        if transaction.transaction_id not in existing_ids
    ]
    if missing:
        await models.Transaction.insert_many(missing)

    stored = await models.Transaction.find(
        models.Transaction.user_id == user_id,
        models.Transaction.upload_id == upload_id,
    ).to_list()
    stored_count = len(stored)
    checks = persistence_integrity(
        [item.model_dump(mode="python") for item in transaction_documents],
        [item.model_dump(mode="python") for item in stored],
    )
    publish(checks)
    if not checks[0]["passed"]:
        raise RuntimeError("MongoDB read-back differs from validated transactions")
    if stored_count != len(transaction_documents):
        raise RuntimeError(
            f"Transaction persistence verification failed: expected "
            f"{len(transaction_documents)}, stored {stored_count}"
        )

    upload.filename = state.get("file_path") or upload.filename
    upload.file_size_bytes = len(state["file_bytes"])
    upload.bank_name = state.get("document_type") or "Statement"
    upload.extraction_method = state.get("extraction_method")
    upload.total_transactions = stored_count
    upload.db_save_completed = True
    upload.vector_index_completed = False
    upload.insights_completed = False
    upload.enrichment_error = None
    upload.extraction_review = state.get("validation_report")
    upload.status = "enriching"
    upload.processed_at = _utcnow()
    await upload.save()

    job = await models.ProcessingJob.find_one(
        models.ProcessingJob.upload_id == upload_id,
        models.ProcessingJob.user_id == user_id,
    )
    if job is None:
        await models.ProcessingJob(
            job_id=f"post:{upload_id}",
            upload_id=upload_id,
            user_id=user_id,
            status="queued",
            parent_trace_id=current_trace().trace_id if current_trace() else None,
            trace_context=carrier(),
            stage="insights",
            max_attempts=settings.JOB_MAX_ATTEMPTS,
        ).insert()
    elif job.status != "completed":
        job.parent_trace_id = current_trace().trace_id if current_trace() else None
        job.trace_context = carrier()
        job.status = "queued"
        job.stage = "insights" if not upload.insights_completed else "vector_index"
        job.error_message = None
        job.locked_by = None
        job.lease_expires_at = None
        job.next_attempt_at = None
        job.updated_at = _utcnow()
        await job.save()

    return upload


async def claim_next_job(worker_id: str) -> Optional[models.ProcessingJob]:
    """Atomically claim one queued job or recover one whose lease expired."""
    now = _utcnow()
    collection = models.ProcessingJob.get_pymongo_collection()
    claimed = await collection.find_one_and_update(
        {
            "$and": [
                {"$or": [
                    {"status": "queued", "next_attempt_at": None},
                    {"status": "queued", "next_attempt_at": {"$lte": now}},
                    {"status": "running", "lease_expires_at": {"$lte": now}},
                ]},
                {"$or": [
                    {"max_attempts": {"$exists": False}, "attempts": {"$lt": settings.JOB_MAX_ATTEMPTS}},
                    {"$expr": {"$lt": ["$attempts", "$max_attempts"]}},
                ]},
            ]
        },
        {
            "$set": {
                "status": "running",
                "locked_by": worker_id,
                "lease_expires_at": now + timedelta(seconds=settings.JOB_LEASE_SECONDS),
                "started_at": now,
                "updated_at": now,
                "error_message": None,
            },
            "$inc": {"attempts": 1},
        },
        sort=[("created_at", 1)],
        return_document=ReturnDocument.AFTER,
    )
    if claimed is None:
        return None
    return models.ProcessingJob.model_validate(claimed)


async def _checkpoint(job: models.ProcessingJob, stage: str) -> None:
    job.stage = stage
    job.updated_at = _utcnow()
    job.lease_expires_at = _utcnow() + timedelta(seconds=settings.JOB_LEASE_SECONDS)
    await job.save()


async def process_claimed_job(job: models.ProcessingJob) -> None:
    """Run an idempotent enrichment job and only then mark it complete."""
    upload = await models.Upload.find_one(
        models.Upload.upload_id == job.upload_id,
        models.Upload.user_id == job.user_id,
    )
    if upload is None or not upload.db_save_completed:
        raise RuntimeError("Verified MongoDB transactions were not persisted before enrichment")

    stored_transactions = await models.Transaction.find(
        models.Transaction.user_id == job.user_id,
        models.Transaction.upload_id == job.upload_id,
    ).to_list()
    if not stored_transactions or len(stored_transactions) != upload.total_transactions:
        raise RuntimeError("Stored transaction count does not match upload metadata")

    transaction_dicts = []
    for transaction in stored_transactions:
        item = transaction.model_dump(mode="python")
        item["date"] = transaction.date.isoformat()
        item["transaction_id"] = transaction.transaction_id
        item["upload_id"] = job.upload_id
        item["user_id"] = job.user_id
        transaction_dicts.append(item)

    if not upload.insights_completed:
        await _checkpoint(job, "insights")
        analyst = agents.FinancialAnalystAgent()
        with observe_stage("insights"):
            insights = await analyst.generate_financial_insights(transaction_dicts)
            checks = insight_checks(insights)
            publish(checks)
            if not checks[0]["passed"]:
                raise RuntimeError("Insight output failed schema validation")
        upload.insights = insights.get("insights", []) if isinstance(insights, dict) else []
        upload.insights_completed = True
        await upload.save()

    if not upload.vector_index_completed:
        await _checkpoint(job, "vector_index")
        if not settings.PINECONE_API_KEY:
            raise RuntimeError("PINECONE_API_KEY is required for vector indexing")
        from .vector_store_pinecone import PineconeVectorStore

        vector_store = await asyncio.to_thread(
            PineconeVectorStore,
            api_key=settings.PINECONE_API_KEY,
            environment=settings.PINECONE_ENVIRONMENT,
            index_name=settings.PINECONE_INDEX_NAME,
        )
        with observe_stage("vector_index"):
            await vector_store.add_transactions(transaction_dicts)
            valid = await vector_store.verify_transactions(transaction_dicts)
            publish([score("vector_readback_integrity", float(valid), valid)])
            if not valid:
                raise RuntimeError("Vector read-back incomplete or metadata mismatch; retry scheduled")
        upload.vector_index_completed = True
        await upload.save()

    if not (upload.db_save_completed and upload.insights_completed and upload.vector_index_completed):
        raise RuntimeError("Required post-processing stages did not complete")
    publish([score("required_stages_completed", 1.0, True)])

    upload.status = "completed"
    upload.enrichment_error = None
    upload.processed_at = _utcnow()
    await upload.save()

    job.status = "completed"
    job.stage = "complete"
    job.completed_at = _utcnow()
    job.updated_at = _utcnow()
    job.locked_by = None
    job.lease_expires_at = None
    await job.save()


async def fail_or_retry_job(job: models.ProcessingJob, error: Exception) -> None:
    """Release a failed lease with bounded exponential retry."""
    safe_error = f"{type(error).__name__}: {str(error)[:500]}"
    terminal = job.attempts >= job.max_attempts
    job.status = "failed" if terminal else "queued"
    job.stage = "failed" if terminal else "retry_wait"
    job.error_message = safe_error
    job.locked_by = None
    job.lease_expires_at = None
    job.updated_at = _utcnow()
    if not terminal:
        delay = settings.JOB_RETRY_BASE_SECONDS * (2 ** max(job.attempts - 1, 0))
        job.next_attempt_at = _utcnow() + timedelta(seconds=delay)
    await job.save()

    upload = await models.Upload.find_one(
        models.Upload.upload_id == job.upload_id,
        models.Upload.user_id == job.user_id,
    )
    if upload:
        upload.status = "failed" if terminal else "retrying"
        upload.enrichment_error = safe_error
        await upload.save()


async def worker_loop(stop_event: asyncio.Event, worker_id: Optional[str] = None) -> None:
    """Poll MongoDB until shutdown, finishing the in-flight job gracefully."""
    worker_id = worker_id or f"{socket.gethostname()}:{uuid.uuid4().hex[:8]}"
    logger.info("Durable post-processing worker started: %s", worker_id)
    while not stop_event.is_set():
        job = await claim_next_job(worker_id)
        if job is None:
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=settings.JOB_POLL_INTERVAL_SECONDS)
            except asyncio.TimeoutError:
                pass
            continue
        with span("part1.enrichment", {"job.attempt": job.attempts}, parent=job.trace_context):
            execution = new_trace("/worker/statement-enrichment")
            execution.parent_trace_id = job.parent_trace_id
            execution.otel_trace_id = current_id()
            execution.set_user(job.user_id, "statement_enrichment")
            token = bind_trace(execution)
            try:
                await process_claimed_job(job)
                execution.finish("success")
            except Exception as error:
                execution.add_event("enrichment", status="failed", error_type=type(error).__name__)
                execution.finish("failed")
                await fail_or_retry_job(job, error)
            finally:
                await execution.flush()
                reset_trace(token)
    logger.info("Durable post-processing worker stopped: %s", worker_id)
