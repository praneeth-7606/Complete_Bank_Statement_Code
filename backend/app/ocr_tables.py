"""Convert Mistral's HTML table cells to financial rows without another LLM.

PDF content is read by hosted OCR. This module only reads the returned tables;
it never infers an amount/direction from a balance or transaction description.
"""
import re
from decimal import Decimal
from html.parser import HTMLParser

from .extraction_validation import number


class TableReader(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.row = None
        self.cell = None
        self.span = 1
        self.unsupported = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'tr':
            self.row = []
        elif tag in ('td', 'th'):
            self.cell = []
            self.span = int(attrs.get('colspan', '1'))
            if int(attrs.get('rowspan', '1')) > 1 or not 1 <= self.span <= 32:
                self.unsupported = True
        elif tag == 'br' and self.cell is not None:
            self.cell.append(' ')

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in ('td', 'th') and self.row is not None and self.cell is not None:
            self.row.extend([' '.join(''.join(self.cell).split())] + [''] * (min(self.span, 32) - 1))
            self.cell = None
        elif tag == 'tr' and self.row is not None:
            self.rows.append(self.row)
            self.row = None


DATE = re.compile(r'^\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}$|^\d{4}-\d{2}-\d{2}$')
OPENING = re.compile(r'^(?:b\s*[/i]?\s*f\b|brought\s+forward|opening\s+balance|balance\s+brought)', re.I)
# A cell containing a decimal amount. Used to tell header/footer noise
# (dated lines with no money, e.g. "STATEMENT ... FROM 01-08-2026 TO ...")
# apart from possibly-missed transaction rows.
MONEY_HINT = re.compile(r'\d[\d,]*\.\d{2}')


def header_map(cells, financial_only=False):
    mapping = {}
    for i, cell in enumerate(cells):
        label = re.sub(r'[^a-z ]', '', cell.lower()).strip()
        if label in ('date', 'txn date', 'transaction date', 'tran date'):
            mapping['date'] = i
        elif label in ('description', 'narration', 'particulars', 'transaction details'):
            mapping['description'] = i
        elif re.fullmatch(r'(?:withdrawal|withdrawals|debit|dr)(?: amount)?', label):
            mapping['debit'] = i
        elif re.fullmatch(r'(?:deposit|deposits|credit|cr)(?: amount)?', label):
            mapping['credit'] = i
        elif label in ('balance', 'closing balance', 'running balance'):
            mapping['balance'] = i
    required = {'date', 'debit', 'credit', 'balance'}
    if not financial_only:
        required.add('description')
    return mapping if required <= mapping.keys() else None


def cell_money(value, blank_zero=False):
    value = value.strip()
    if value in ('', '-', '--'):
        return '0.00' if blank_zero else None
    # Indian statements suffix balances with Cr/Dr (e.g. "37,656.38 Cr").
    # Accept the suffix here; number() applies the sign semantics.
    core = re.sub(r'\s*(?:cr|dr)\.?$', '', value, flags=re.I)
    if not re.fullmatch(r'-?\d[\d,]*(?:\.\d{1,2})?', core):
        raise ValueError('Unrecognized financial cell')
    return str(number(value))


def parse_ocr_tables(pages):
    rows, issues, summary, opening_rows = [], [], {}, []
    mapping, width = None, None
    page_counts = {}
    page_positions = {}
    def issue(code, page):
        issues.append({'code': code, 'row': None, 'page': page})
    def record_summary(key, value, page):
        if value is None:
            return
        if key in summary and summary[key] != value:
            issue('printed_summary_disagreement', page)
        summary[key] = value
    for page in pages:
        page_number = page['index'] + 1
        page_counts[page_number] = 0
        page_positions[page_number] = 0
        for table in page.get('tables', []):
            parser = TableReader()
            parser.feed(table.get('content', ''))
            table_has_dated = any(
                row and DATE.fullmatch((row[0] or '').strip()) for row in parser.rows
            )
            # A spanned header/notes table with no dated rows cannot hide
            # transactions; only flag spans that overlap dated content.
            if parser.unsupported and table_has_dated:
                issue('unsupported_table_span', page_number)
            for cells in parser.rows:
                detected = header_map(cells)
                if detected:
                    mapping, width = detected, len(cells)
                    continue
                dated = bool(cells and DATE.fullmatch(cells[0].strip()))
                # OCR occasionally splits a multiline narration into extra cells.
                # Keep the three financial columns anchored to their printed
                # right-hand positions, only when all three are valid amounts.
                if mapping and dated and len(cells) > width and [mapping[k] for k in ('debit', 'credit', 'balance')] == list(range(width - 3, width)):
                    try:
                        for value in cells[-3:]:
                            cell_money(value)
                        extra = len(cells) - width
                        at = mapping['description']
                        cells = cells[:at] + [' '.join(cells[at:at + extra + 1])] + cells[at + extra + 1:]
                    except ValueError:
                        pass
                if not mapping or len(cells) != width:
                    if dated and any(MONEY_HINT.search(c or '') for c in cells):
                        # Dated + money that fits no column map: a transaction
                        # row may have been lost. Header/footer date lines
                        # without amounts stay silent.
                        issue('unmapped_transaction_columns', page_number)
                    continue
                label = ' '.join(cells[:mapping['debit']]).strip()
                if re.fullmatch(r'total(?:s)?', label, re.I):
                    try:
                        for field in ('debit', 'credit'):
                            record_summary('total_' + field + 's', cell_money(cells[mapping[field]]), page_number)
                    except ValueError:
                        issue('invalid_printed_totals', page_number)
                    continue
                if not DATE.fullmatch(cells[mapping['date']].strip()):
                    # Financial cells without a transaction date cannot disappear.
                    if any(cells[mapping[k]].strip() for k in ('debit', 'credit', 'balance')) and cells[mapping['description']].strip():
                        if not any(word in label.lower() for word in ('account', 'summary', 'balance', 'total')):
                            issue('unparsed_table_row', page_number)
                    continue
                item = {key: cells[position] for key, position in mapping.items()}
                try:
                    for field in ('debit', 'credit', 'balance'):
                        item[field] = cell_money(item[field], blank_zero=field != 'balance')
                except ValueError:
                    issue('invalid_financial_cell', page_number)
                item['source_page'] = page_number
                page_positions[page_number] += 1
                item['source_row'] = page_positions[page_number]
                if OPENING.search(item['description']):
                    opening_rows.append(item)
                    record_summary('opening_balance', item['balance'], page_number)
                    continue
                page_counts[page_number] += 1
                rows.append(item)
        markdown = page.get('markdown', '')
        # Explicit labelled statement summary, not page subtotals or computed values.
        if 'STATEMENT SUMMARY' in markdown.upper():
            segment = re.split('STATEMENT SUMMARY', markdown, flags=re.I)[-1]
            for label, key in (('Opening Balance', 'opening_balance'), ('Closing Balance', 'closing_balance'),
                               ('Debits', 'total_debits'), ('Credits', 'total_credits')):
                match = re.search(r'\b' + label + r'\s*[:|*-]*\s*([\d,]+\.\d{2})', segment, re.I)
                if match:
                    record_summary(key, cell_money(match[1]), page_number)
            counts = [re.search(label + r'\s*[:|*-]*\s*(\d+)', segment, re.I) for label in ('Dr Count', 'Cr Count')]
            if all(counts):
                record_summary('transaction_count', sum(int(m[1]) for m in counts), page_number)
    # Some tables include their explicit B/F row in the printed credit total.
    # Keep that source total separately; never present B/F as a new payment.
    if len(opening_rows) == 1:
        opening = opening_rows[0]
        for field in ('debit', 'credit'):
            key = 'total_' + field + 's'
            try:
                carried = number(opening[field])
                if carried and key in summary:
                    summary[key + '_including_opening'] = summary.pop(key)
                    summary[field + '_opening_component'] = str(carried)
            except Exception:
                issue('invalid_opening_balance_row', opening['source_page'])
    return {'transactions': rows, 'summary': summary, 'issues': issues,
            'opening_rows': opening_rows, 'page_counts': page_counts}


def parse_financial_evidence(pages):
    """Read a separate OCR view with explicit date/debit/credit/balance headers."""
    rows = []
    for page in pages:
        for table in page.get('tables', []):
            parser = TableReader()
            parser.feed(table.get('content', ''))
            if parser.unsupported:
                raise ValueError('Ambiguous cropped financial table')
            mapping = None
            width = 0
            for cells in parser.rows:
                header = header_map(cells, financial_only=True)
                if header:
                    mapping, width = header, len(cells)
                    continue
                if cells and DATE.fullmatch(cells[0]):
                    if mapping is None or len(cells) != width:
                        raise ValueError('Cropped table columns are ambiguous')
                    rows.append({'date':cells[mapping['date']], **{k:cell_money(cells[mapping[k]], k != 'balance')
                                for k in ('debit', 'credit', 'balance')}})
    return rows
