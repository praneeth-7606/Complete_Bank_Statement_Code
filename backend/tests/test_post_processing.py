import asyncio
from decimal import Decimal

import fitz
import pytest

from app import models
from app.config import settings
from app.post_processing import build_transaction_records
from app.smart_extractor import MistralOCRExtractor


def _state():
    return {
        "streaming_id": "upload-123",
        "user_id": "user-123",
        "categorized_transactions": [
            {
                "date": "2026-09-19",
                "description": "Test merchant",
                "debit": "0.10",
                "credit": "0.00",
                "amount": "0.10",
                "category": "Shopping",
            },
            {
                "date": "19/09/2026",
                "description": "Salary",
                "debit": 0,
                "credit": "1000.25",
                "amount": "1000.25",
                "category": "Salary",
            },
        ],
    }


def test_transaction_documents_use_decimal_and_deterministic_ids():
    first = build_transaction_records(_state())
    second = build_transaction_records(_state())

    assert [item["transaction_id"] for item in first] == [item["transaction_id"] for item in second]
    assert first[0]["amount"] == Decimal("0.10")
    assert first[0]["debit"] == Decimal("0.10")
    assert first[1]["credit"] == Decimal("1000.25")
    assert first[1]["upload_id"] == "upload-123"


def test_pdf_masking_redacts_pii_before_hosted_ocr(monkeypatch):
    monkeypatch.setattr(settings, "ALLOW_UNREDACTED_OCR", False)
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Account 123456789012 Phone 9876543210 merchant AMAZON")
    source = document.tobytes()
    document.close()

    extractor = object.__new__(MistralOCRExtractor)
    masked = extractor._mask_pdf_bytes(source)
    masked_document = fitz.open(stream=masked, filetype="pdf")
    text = "".join(page.get_text() for page in masked_document)
    masked_document.close()

    assert "123456789012" not in text
    assert "9876543210" not in text
    assert "AMAZON" in text


def test_image_only_pdf_fails_closed_without_explicit_opt_in(monkeypatch):
    monkeypatch.setattr(settings, "ALLOW_UNREDACTED_OCR", False)
    document = fitz.open()
    document.new_page()
    source = document.tobytes()
    document.close()

    extractor = object.__new__(MistralOCRExtractor)
    with pytest.raises(RuntimeError, match="safely redacted"):
        extractor._mask_pdf_bytes(source)


def test_prefetched_corrections_do_not_query_per_transaction(monkeypatch):
    from app.agent_categorization import CategorizationAgent

    class ForbiddenQuery:
        def __call__(self, *args, **kwargs):
            raise AssertionError("Correction database should not be queried when corrections are prefetched")

    monkeypatch.setattr(models.Correction, "find", ForbiddenQuery())
    agent = object.__new__(CategorizationAgent)
    agent._active_corrections = {}
    agent._active_user_id = None

    transactions = [
        {"description": "UPI/foo/Local Shop", "amount": "25.00", "debit": "25.00", "credit": "0"},
        {"description": "UPI/foo/Local Shop", "amount": "30.00", "debit": "30.00", "credit": "0"},
    ]
    result = asyncio.run(
        agent.categorize_transactions(
            transactions,
            user_id="user-123",
            corrections=[
                {
                    "transaction_description_keyword": "Local Shop",
                    "correct_category": "Groceries",
                }
            ],
        )
    )

    assert [item["category"] for item in result] == ["Groceries", "Groceries"]
    assert all(item["source"] == "local_history" for item in result)
