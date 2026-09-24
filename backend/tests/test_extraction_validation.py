from types import SimpleNamespace
import asyncio
from unittest.mock import AsyncMock
import pytest

import fitz

from app.extraction_validation import validate_extraction
from app.smart_extractor import MistralOCRExtractor
from app.mistral_statement import extract_statement


extractor = object.__new__(MistralOCRExtractor)


def row(debit="10.00", credit="0.00", balance="90.00", date="20/09/2026"):
    return dict(date=date, description="Payment", debit=debit, credit=credit, balance=balance)


def check(rows, summary=None):
    return validate_extraction(rows, extractor._parse_date, summary)


def test_never_drop_or_invent_even_when_multiple_fields_invalid():
    original = [row(date="invalid"), row(debit="NaN"), row(balance=None), row(debit="0.00"), row()]
    original[4]["description"] = ""
    result = check(original)
    assert result["retained_count"] == 5 and result["dropped_count"] == 0
    assert result["status"] == "needs_review"
    assert result["transactions"][2]["balance"] is None
    assert original[0]["date"] == "invalid"


def test_never_flip_direction_to_make_a_closer_but_wrong_balance():
    result = check([row(balance="100.00"), row(debit="0", credit="25", balance="60")])
    assert result["transactions"][1]["credit"] == "25.00"
    assert {i["code"] for i in result["issues"]} == {"running_balance_mismatch"}


def test_decimal_zero_balance_and_duplicate_payments_are_preserved():
    result = check([row(debit="0.10", balance="0.20"), row(debit="0.10", balance="0.10"), row(debit="0.10", balance="0")],
                   {"opening_balance": "0.30", "closing_balance": "0", "total_debits": "0.30", "transaction_count": 3})
    assert result["status"] == "checks_passed"
    assert result["balance_matches"] == 2
    assert len(result["transactions"]) == 3


def test_missing_pair_can_balance_but_printed_count_detects_gap():
    result = check([row(balance="100"), row(balance="90")], {"transaction_count": 4})
    assert result["balance_matches"] == 1
    assert result["status"] == "needs_review"


def test_cr_dr_balance_suffixes_parse_without_rewriting_rows():
    result = check([row(balance="37,656.38 Cr"), row(debit="5000.00", balance="32,656.38 Cr")])
    assert result["status"] == "checks_passed"
    assert result["transactions"][0]["balance"] == "37656.38"
    assert result["balance_matches"] == 1


def test_header_date_lines_without_money_stay_silent():
    from app.ocr_tables import parse_ocr_tables
    pages = [{'index': 0, 'tables': [
        {'content': '<table><tr><td colspan="5">STATEMENT OF ACCOUNT FOR THE PERIOD FROM 01-08-2026 TO 31-08-2026</td></tr>'
                    '<tr><th>Date</th><th>Description</th><th>Debit</th><th>Credit</th><th>Balance</th></tr>'
                    '<tr><td>01-08-2026</td><td>Payment</td><td>10.00</td><td>0.00</td><td>90.00</td></tr></table>'}]}]
    parsed = parse_ocr_tables(pages)
    assert len(parsed['transactions']) == 1
    assert parsed['issues'] == []


def test_dated_row_with_money_but_no_column_map_stays_blocking():
    from app.ocr_tables import parse_ocr_tables
    pages = [{'index': 0, 'tables': [
        {'content': '<table><tr><th>Date</th><th>Description</th><th>Debit</th></tr>'
                    '<tr><td>01-08-2026</td><td>Payment</td><td>10.00</td><td>EXTRA</td></tr></table>'}]}]
    parsed = parse_ocr_tables(pages)
    assert parsed['transactions'] == []
    assert [i['code'] for i in parsed['issues']] == ['unmapped_transaction_columns']


def test_descending_order_reconciles_without_rewriting_rows():
    result = check([row(balance="80", date="21/09/26"), row(balance="90", date="20/09/26")])
    assert result["status"] == "checks_passed"
    assert result["transactions"][0]["balance"] == "80.00"


def test_statement_totals_and_first_transaction_are_verified():
    result = check([row(balance="90")], {"opening_balance": "101", "total_debits": "11"})
    assert {i["code"] for i in result["issues"]} == {"opening_balance_mismatch", "total_debits_mismatch"}


def test_mistral_groups_cover_all_pages_and_preserve_duplicate_payments():
    doc = fitz.open()
    for _ in range(9):
        doc.new_page()
    pdf = doc.tobytes()
    doc.close()
    seen = []
    def process(**kwargs):
        pages = kwargs["pages"]
        seen.append(pages)
        rows = [row() | {"source_page": p + 1, "source_row": r} for p in pages for r in (1, 2)]
        return SimpleNamespace(document_annotation={"document_type": "bank_statement", "transactions": rows,
                              "printed_summary": {}}, pages=[SimpleNamespace(index=p) for p in pages])
    client = SimpleNamespace(ocr=SimpleNamespace(process=process))
    _, rows = extract_statement(client, pdf, "test", extractor.TRANSACTION_SCHEMA, "test", concurrency=1)
    assert seen == [list(range(8)), [7, 8]]
    assert len(rows) == 18
    assert rows.coverage == []


def test_missing_ocr_pages_are_not_accepted_as_covered():
    doc = fitz.open()
    doc.new_page()
    pdf = doc.tobytes()
    doc.close()
    client = SimpleNamespace(ocr=SimpleNamespace(process=lambda **kw: SimpleNamespace(
        document_annotation={"transactions": [row() | {"source_page": 1, "source_row": 1}]}, pages=[])))
    _, rows = extract_statement(client, pdf, "test", extractor.TRANSACTION_SCHEMA, "test")
    assert rows.coverage[0]["code"] == "ocr_page_coverage_mismatch"


def test_pipeline_blocks_categorization_and_storage_on_bad_financial_evidence(monkeypatch):
    from app import agents, post_processing
    from app.extraction_validation import ExtractionNeedsReview
    test_extractor = object.__new__(MistralOCRExtractor)
    monkeypatch.setattr(test_extractor, "_ocr_pdf_with_mistral", lambda *a: (
        "bank_statement", [row(balance="100"), row(credit="25", debit="0", balance="60")]))
    def forbidden(*args, **kwargs):
        raise AssertionError("Invalid extraction must not reach categorization")
    monkeypatch.setattr(agents, "CategorizationAgent", forbidden)
    persist = AsyncMock()
    monkeypatch.setattr(post_processing, "persist_statement_and_enqueue", persist)
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), "Bank statement")
    pdf = doc.tobytes()
    doc.close()
    with pytest.raises(ExtractionNeedsReview) as caught:
        asyncio.run(test_extractor.process_statement(pdf, "", "test.pdf", user_id="test", corrections=[]))
    assert caught.value.report["retained_count"] == 2
    persist.assert_not_awaited()


def test_pipeline_preserves_decimal_strings_into_persistence(monkeypatch):
    from app import agents, post_processing
    test_extractor = object.__new__(MistralOCRExtractor)
    monkeypatch.setattr(test_extractor, "_ocr_pdf_with_mistral", lambda *a: (
        "bank_statement", [row(debit="0.10", balance="0.20"), row(debit="0.10", balance="0.10")]))
    async def categorize(rows, **kwargs):
        return [r | {"category": "Other"} for r in rows]
    monkeypatch.setattr(agents, "CategorizationAgent", lambda: SimpleNamespace(categorize_transactions=categorize))
    persist = AsyncMock()
    monkeypatch.setattr(post_processing, "persist_statement_and_enqueue", persist)
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), "Bank statement")
    pdf = doc.tobytes()
    doc.close()
    result = asyncio.run(test_extractor.process_statement(pdf, "", "test.pdf", user_id="test", corrections=[]))
    assert result["validation_report"]["status"] == "checks_passed"
    assert result["transactions"][0]["debit"] == "0.10"
    persist.assert_awaited_once()
