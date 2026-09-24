"""Mistral-first structured extraction with bounded page groups and coverage checks."""
import base64
import json
import time
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy

import fitz

from .observability import observe_external_llm


class OCRTransactions(list):
    """Request-local extraction evidence; never stored on the shared extractor."""
    def __init__(self, rows, summary, coverage):
        super().__init__(rows)
        self.summary = summary
        self.coverage = coverage


def extract_statement(client, pdf_bytes, model, schema, prompt, group_pages=8, concurrency=2, timeout_ms=45000, max_retries=2):
    with fitz.open(stream=pdf_bytes, filetype="pdf") as document:
        total_pages = len(document)
    if total_pages < 1:
        raise ValueError("Empty document")
    group_pages = max(1, min(8, group_pages))
    groups = []
    start = 0
    while start < total_pages:
        end = min(start + group_pages, total_pages)
        groups.append((start, end))
        if end == total_pages:
            break
        # A one-page request is the strictest mode for irregular statements;
        # there is no overlap because reusing the only page would not advance.
        start = end if group_pages == 1 else end - 1
    schema = deepcopy(schema)
    fields = schema["properties"]["transactions"]["items"]
    for field in ("debit", "credit", "balance"):
        fields["properties"][field] = {"type": ["number", "null"], "description": (
            "Exact amount in currency units. KEEP the decimal point and fractional digits: 110.00 is 110.00, NEVER 11000. "
            "Remove thousands-grouping commas ONLY: 23,324.28 becomes 23324.28. Never multiply by 100. "
            "Null if unreadable or absent; zero only if known. "
            "For a clear debit set credit to 0.00, and conversely. Never invent or reconcile values."
        )}
    for field in ("source_page", "source_row"):
        fields["properties"][field] = {"type": "integer", "description": (
            "1-based original PDF page number" if field == "source_page" else
            "1-based transaction row number on its originating page; retain repeated identical payments"
        )}
        fields["required"].append(field)
    summary_fields = {key: {"type": ["number", "null"], "description": "Copy printed statement-wide amount in currency units with its decimal point. Null if absent. Never calculate; never use a page subtotal or carried-forward balance."}
                      for key in ("opening_balance", "closing_balance", "total_debits", "total_credits")}
    summary_fields["transaction_count"] = {"type": ["integer", "null"], "description": "Printed total transaction count only, null if absent. Never count it yourself."}
    schema["properties"]["printed_summary"] = {"type": "object", "properties": summary_fields,
        "required": list(summary_fields), "additionalProperties": False}
    schema["required"].append("printed_summary")
    uri = "data:application/pdf;base64," + base64.b64encode(pdf_bytes).decode("ascii")

    def request(group):
        first, end = group
        last_error = None
        best = None
        best_score = (-1, -1, -1)
        for attempt in range(max(0, max_retries) + 1):
            try:
                with observe_external_llm("mistral", model, kind="ocr") as span:
                    response = client.ocr.process(
                        model=model, document={"type": "document_url", "document_url": uri},
                        pages=list(range(first, end)), include_image_base64=False,
                        document_annotation_format={"type": "json_schema", "json_schema": {"name": "FinancialDocument", "schema": schema, "strict": True}},
                        document_annotation_prompt=prompt + (
                            f"\nProcessing original PDF pages {first + 1} through {end}. "
                            "Use original 1-based PDF page numbers in source_page. Retain every transaction, including repeated identical rows. "
                            "Join continuation text to its originating transaction. Exclude opening/carried-forward balance headers. "
                            "Missing balances must be null, never zero. Do not infer debit/credit from merchant names. "
                            "Read debit and credit ONLY from numbers visibly aligned under the Debit Amount and Credit Amount columns. "
                            "Never copy cheque/reference numbers, customer IDs, UPI IDs, phone numbers, dates, or description digits into amount fields. "
                            "If an amount column is visually blank, use 0.00 for the opposite populated column and do not invent a value. "
                            "If a later page continues the same table without repeating headers, inherit the exact debit/credit column order from the prior page. "
                            "Do not swap columns merely because a running-balance calculation is convenient; use the table layout and inherited header. "
                            "Never correct amounts to make balances match. Preserve decimal points: 110.00 must NEVER become 11000. "
                            "Extract printed_summary only from explicitly labelled STATEMENT-WIDE summary evidence. "
                            "Use null if a summary field is not visible in this page group; never substitute page opening/closing balances."
                        ), timeout_ms=timeout_ms,
                    )
                    span.response = response
                ann = response.document_annotation
                data = json.loads(ann, parse_float=Decimal) if isinstance(ann, str) else ann
                if not isinstance(data, dict) or not isinstance(data.get("transactions"), list):
                    raise ValueError("Invalid structured OCR output")
                pages = getattr(response, "pages", []) or []
                seen = {getattr(page, "index", None) for page in pages}
                candidate_coverage = []
                if seen != set(range(first, end)):
                    candidate_coverage.append({"code": "ocr_page_coverage_mismatch", "row": None})
                if end - first == 1:
                    selected_rows = [row for row in data["transactions"] if isinstance(row, dict)]
                    selected_pages = {first + 1} if selected_rows else set()
                else:
                    selected_rows = [row for row in data["transactions"]
                                     if isinstance(row, dict) and isinstance(row.get("source_page"), int)
                                     and first < row["source_page"] <= end]
                    selected_pages = {row["source_page"] for row in selected_rows}
                if selected_rows and selected_pages != set(range(first + 1, end + 1)):
                    candidate_coverage.append({"code": "ocr_page_without_transactions", "row": None,
                                               "page": sorted(set(range(first + 1, end + 1)) - selected_pages)})
                score = (len(selected_rows), len(selected_pages), -len(candidate_coverage))
                if score > best_score:
                    best = (data, candidate_coverage)
                    best_score = score
                if len(selected_pages) == end - first and selected_rows:
                    break
            except Exception as exc:
                last_error = exc
                if attempt >= max(0, max_retries):
                    if best is None:
                        raise
                    break
                time.sleep(min(2 ** attempt, 4))
        if best is None:
            if last_error is not None:
                raise last_error
            raise last_error
        return best

    with ThreadPoolExecutor(max_workers=max(1, min(concurrency, len(groups)))) as pool:
        results = list(pool.map(request, groups))
    rows, coverage, summary = [], [], {}
    previous_pages = {}
    for (first, end), (data, errors) in zip(groups, results):
        coverage.extend(errors)
        by_page = {}
        for local_index, row in enumerate(data["transactions"], 1):
            if end - first == 1:
                row = dict(row)
                row["source_page"] = first + 1
                row["source_row"] = local_index
            page, position = row.get("source_page"), row.get("source_row")
            if not isinstance(page, int) or not first < page <= end or not isinstance(position, int) or position < 1:
                coverage.append({"code": "invalid_source_location", "row": None})
                rows.append(row)  # preserve problematic rows; validation blocks publication
                continue
            by_page.setdefault(page, []).append(row)
        for page in range(first + 1, end + 1):
            page_rows = by_page.get(page, [])
            if not page_rows and any(by_page.values()):
                coverage.append({"code": "ocr_page_without_transactions", "row": None, "page": page})
            if len({r["source_row"] for r in page_rows}) != len(page_rows):
                coverage.append({"code": "duplicate_source_location", "row": None})
            if page in previous_pages:
                # Compare shared pages before discarding repeated context. No
                # amount/date-based dedupe: legitimate duplicate payments remain.
                keys = ("source_row", "date", "description", "debit", "credit", "balance")
                fingerprint = lambda rs: [tuple(r.get(k) for k in keys) for r in rs]
                if fingerprint(previous_pages[page]) != fingerprint(page_rows):
                    coverage.append({"code": "overlap_disagreement", "row": None})
                    rows.extend(page_rows)  # retain both interpretations for review
                continue
            rows.extend(page_rows)
            previous_pages[page] = page_rows
        for key, value in (data.get("printed_summary") or {}).items():
            if value is not None:
                if key in summary and str(summary[key]) != str(value):
                    coverage.append({"code": "printed_summary_disagreement", "row": None})
                summary[key] = value
    # Decimal strings serialize safely through the existing categorizer and
    # checkpoints while retaining the exact currency values from JSON parsing.
    for row in rows:
        for key in ("debit", "credit", "balance"):
            if isinstance(row.get(key), Decimal):
                row[key] = str(row[key])
    summary = {k: str(v) if isinstance(v, Decimal) else v for k, v in summary.items()}
    return results[0][0].get("document_type", "bank_statement"), OCRTransactions(rows, summary, coverage)
