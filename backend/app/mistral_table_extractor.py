"""Hosted OCR tables first; bounded page rendering retries for missing evidence."""
import base64
import logging
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import fitz
import httpx

from .extraction_validation import number, validate_extraction
from .observability import observe_external_llm
from .ocr_tables import parse_ocr_tables, parse_financial_evidence
from .ocr_render import render_page_context, render_financial_columns

logger = logging.getLogger(__name__)

# Global semaphore so concurrent statements cannot stampede Mistral and
# self-inflict 429 rate limits. Sized from OCR_MAX_CONCURRENCY at first use.
_ocr_semaphore: threading.Semaphore | None = None
_ocr_semaphore_lock = threading.Lock()


def _get_ocr_semaphore() -> threading.Semaphore:
    global _ocr_semaphore
    with _ocr_semaphore_lock:
        if _ocr_semaphore is None:
            try:
                from .config import settings
                size = max(1, int(settings.OCR_MAX_CONCURRENCY))
            except Exception:
                size = 1
            _ocr_semaphore = threading.Semaphore(size)
            logger.info("[OCR] Global Mistral concurrency semaphore size=%d", size)
        return _ocr_semaphore


def parse_date(value):
    for pattern in ('%d/%m/%Y', '%d/%m/%y', '%Y-%m-%d', '%d-%m-%Y', '%d-%m-%y', '%d.%m.%Y'):
        try:
            return datetime.strptime(value.strip(), pattern).date().isoformat()
        except ValueError:
            pass
    return None


def process_ocr(client, model, document, timeout_ms, max_retries):
    # 429 deserves more patience than generic transients; free/low tiers
    # recover after short windows. Cap total attempts at 5. Use a while-loop
    # so a 429 with max_allowed > base_attempts cannot fall off the end of a
    # for-range and return None (which crashed as NoneType.get downstream).
    base_attempts = max(0, min(max_retries, 3))
    attempt = 0
    while True:
        try:
            with _get_ocr_semaphore():
                with observe_external_llm('mistral', model, kind='ocr') as span:
                    result = client.ocr.process(model=model, document=document, table_format='html',
                        include_image_base64=False, timeout_ms=timeout_ms, retries=None)
                    span.response = result
            if result is None:
                raise RuntimeError("Mistral OCR returned an empty response object")
            return result.model_dump(mode='json')
        except Exception as exc:
            status = getattr(exc, 'status_code', None)
            message = str(exc).lower()
            is_429 = status == 429 or '429' in message or 'rate' in message
            transient = isinstance(exc, httpx.TransportError) or status in (408, 429, 500, 502, 503, 504)
            max_allowed = 4 if is_429 else base_attempts
            if not transient or attempt >= max_allowed:
                if is_429:
                    logger.error("[OCR] Mistral still rate-limited after %d attempts: %s", attempt + 1, exc)
                raise
            # Exponential backoff; longer for 429.
            delay = min(2 ** attempt, 8) + random.uniform(0, 0.25)
            if is_429:
                delay = min(2 ** (attempt + 1), 15) + random.uniform(0.5, 1.5)
            logger.warning(
                "[OCR] Mistral transient error (status=%s) attempt %d/%d - sleeping %.1fs",
                status, attempt + 1, max_allowed + 1, delay,
            )
            time.sleep(delay)
            attempt += 1


def extract_tables(client, pdf_bytes, model, *, concurrency=2, timeout_ms=90000, max_retries=2, page_limit=20):
    from .mistral_statement import OCRTransactions
    with fitz.open(stream=pdf_bytes, filetype='pdf') as document:
        page_count = len(document)
        nonempty = {i for i, p in enumerate(document) if p.get_text().strip() or p.get_images() or p.get_drawings()}
    if not page_count:
        raise ValueError('Empty document')
    chunks = [(i, min(page_count, i + max(1, min(page_limit, 100))))
              for i in range(0, page_count, max(1, min(page_limit, 100)))]
    def request_chunk(chunk):
        first, end = chunk
        if first == 0 and end == page_count:
            payload = pdf_bytes
        else:
            with fitz.open(stream=pdf_bytes, filetype='pdf') as source, fitz.open() as part:
                part.insert_pdf(source, from_page=first, to_page=end-1)
                payload = part.tobytes()
        result = process_ocr(client, model, {'type':'document_url',
            'document_url':'data:application/pdf;base64,' + base64.b64encode(payload).decode()}, timeout_ms, max_retries)
        if not isinstance(result, dict):
            raise RuntimeError(f"Mistral OCR returned non-dict payload: {type(result).__name__}")
        actual = result.get('pages') or []
        indices = [page.get('index') for page in actual]
        if sorted(indices) != list(range(end-first)):
            raise ValueError('OCR page coverage mismatch')
        for page in actual:
            page['index'] += first
        return actual
    with ThreadPoolExecutor(max_workers=max(1, min(concurrency, len(chunks)))) as pool:
        pages = sorted([p for chunk in pool.map(request_chunk, chunks) for p in chunk], key=lambda p:p['index'])
    parsed = parse_ocr_tables(pages)
    validation = validate_extraction(parsed['transactions'], parse_date, parsed['summary'])
    suspect = {p['index'] for p in pages if p['index'] in nonempty and not p.get('tables') and not p.get('markdown', '').strip()}
    suspect.update(issue['page'] - 1 for issue in parsed['issues'] if isinstance(issue.get('page'), int))
    for issue in validation['issues']:
        index = issue.get('row')
        if index and index <= len(parsed['transactions']):
            suspect.add(parsed['transactions'][index - 1]['source_page'] - 1)
            if issue['code'] == 'running_balance_mismatch' and index > 1:
                suspect.add(parsed['transactions'][index - 2]['source_page'] - 1)
    # A totals/count-only failure has no reliable single-page location.
    if not suspect and validation['status'] != 'checks_passed':
        suspect.update(range(page_count))
    retries = []
    retry_errors = []
    def retry_page(index):
        try:
            image = render_page_context(pdf_bytes, index)
            response = process_ocr(client, model, {'type':'image_url',
                'image_url':'data:image/png;base64,' + base64.b64encode(image).decode()}, timeout_ms, max_retries)
            if not isinstance(response, dict):
                raise RuntimeError(f"Mistral OCR returned non-dict payload: {type(response).__name__}")
            recovered = response.get('pages') or []
            if len(recovered) != 1:
                raise ValueError('Unexpected rendered-page OCR coverage')
            page = recovered[0]
            page['index'] = index
            return index, page, None
        except Exception as exc:
            return index, None, type(exc).__name__
    if suspect:
        # One semantic retry per affected page; never select a candidate by row count.
        with ThreadPoolExecutor(max_workers=max(1, min(concurrency, len(suspect)))) as pool:
            for index, replacement, error in pool.map(retry_page, sorted(suspect)):
                if replacement is None:
                    retry_errors.append({'code': 'ocr_retry_failed', 'row': None, 'page': index + 1,
                                         'error_type': error})
                else:
                    pages[index] = replacement
                    retries.append(index + 1)
        parsed = parse_ocr_tables(pages)
    validation = validate_extraction(parsed['transactions'], parse_date, parsed['summary'])
    financial_suspect = set()
    for issue in validation['issues']:
        row = issue.get('row')
        if row and issue['code'] in ('invalid_debit', 'invalid_credit', 'ambiguous_debit_credit', 'running_balance_mismatch'):
            financial_suspect.add(parsed['transactions'][row - 1]['source_page'] - 1)
    financial_retries = []
    def reread_financial(index):
        try:
            image = render_financial_columns(pdf_bytes, index)
            if image is None:
                return index, [], 'unavailable'
            response = process_ocr(client, model, {'type':'image_url',
                'image_url':'data:image/png;base64,' + base64.b64encode(image).decode()}, timeout_ms, max_retries)
            if not isinstance(response, dict):
                raise RuntimeError(f"Mistral OCR returned non-dict payload: {type(response).__name__}")
            return index, parse_financial_evidence(response.get('pages') or []), None
        except Exception as exc:
            return index, [], type(exc).__name__
    if financial_suspect:
        with ThreadPoolExecutor(max_workers=max(1, min(concurrency, len(financial_suspect)))) as pool:
            for index, financial_rows, error in pool.map(reread_financial, sorted(financial_suspect)):
                if error:
                    retry_errors.append({'code': 'financial_ocr_retry_failed', 'row': None,
                                         'page': index + 1, 'error_type': error})
                    continue
                originals = sorted([r for r in parsed['transactions'] + parsed['opening_rows'] if r['source_page'] == index + 1],
                                   key=lambda r:r['source_row'])
                # Exact sequence/date/balance agreement is required to align the
                # independent source view. A mismatch remains a review issue.
                if not financial_rows or len(originals) != len(financial_rows):
                    continue
                if any(parse_date(a['date']) != parse_date(b['date']) or number(a['balance']) != number(b['balance'])
                       for a,b in zip(originals, financial_rows)):
                    continue
                if any(a in parsed['opening_rows'] and any(a[k] != b[k] for k in ('debit','credit'))
                       for a,b in zip(originals,financial_rows)):
                    continue
                for original, verified in zip(originals, financial_rows):
                    if any(original[k] != verified[k] for k in ('debit', 'credit')):
                        original['_original_financial_fields'] = {k:original[k] for k in ('date','debit','credit','balance')}
                        original['debit'], original['credit'] = verified['debit'], verified['credit']
                        original['financial_evidence'] = 'independent_ocr_of_printed_columns'
                financial_retries.append(index + 1)
                parsed['issues'] = [i for i in parsed['issues'] if not (i['code']=='invalid_financial_cell' and i.get('page')==index+1)]
    coverage = list(parsed['issues']) + retry_errors
    for page in pages:
        if page['index'] in nonempty and not page.get('tables') and not page.get('markdown', '').strip():
            coverage.append({'code':'empty_ocr_page', 'row':None, 'page':page['index'] + 1})
    rows = OCRTransactions(parsed['transactions'], parsed['summary'], coverage)
    rows.evidence = {'method':'mistral_html_tables', 'page_count':page_count,
                     'transaction_rows_by_page':parsed['page_counts'],
                     'rendered_retry_pages':retries, 'opening_rows_excluded':len(parsed['opening_rows']),
                     'financial_reextraction_pages':financial_retries,
                     'ocr_calls_minimum':len(chunks) + len(retries) + len(financial_suspect)}
    return 'bank_statement', rows
