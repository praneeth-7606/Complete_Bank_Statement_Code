"""Mistral extraction normalization and non-destructive validation."""
from copy import deepcopy
from decimal import Decimal, InvalidOperation


class ExtractionNeedsReview(ValueError):
    def __init__(self, report):
        self.report = report
        super().__init__(f"Statement needs review: {len(report['issues'])} extraction issue(s); no transactions published.")


def number(value):
    if value is None or str(value).strip() == "":
        return None
    text = str(value).replace(",", "").strip()
    # Indian statements suffix balances with Cr (credit, positive) or
    # Dr (debit/overdrawn, negative), e.g. "37,656.38 Cr".
    sign = Decimal(1)
    lowered = text.lower()
    if lowered.endswith("cr"):
        text = text[:-2].strip()
    elif lowered.endswith("dr"):
        text = text[:-2].strip()
        sign = Decimal(-1)
    result = sign * Decimal(text)
    if not result.is_finite():
        raise InvalidOperation("Non-finite amount")
    if result != result.quantize(Decimal("0.01")):
        raise InvalidOperation("Unexpected monetary precision")
    return result.quantize(Decimal("0.01"))


def normalize_ocr_rows(transactions):
    """Copy evidence without inferring or repairing financial values."""
    return deepcopy(list(transactions)), []


def validate_extraction(transactions, parse_date, summary=None):
    """Keep one output per input; expose financial evidence without modifying it.

    Returned decimal strings preserve cents through JSON and existing consumers.
    A successful check is arithmetic consistency, not independently measured OCR
    accuracy. Source PDF comparison is still required in evaluation datasets.
    """
    rows, issues, values = [], [], []
    def issue(code, row=None):
        issues.append({"code": code, "row": row})
    for index, original in enumerate(transactions, 1):
        row = deepcopy(original) if isinstance(original, dict) else {"unparsed_row": str(original)}
        original_financial = row.pop("_original_financial_fields", None)
        row["source_financial_fields"] = original_financial or {
            key: row.get(key) for key in ("date", "debit", "credit", "balance", "amount")
        }
        row["source_index"] = index
        row["date"] = parse_date(str(row.get("date") or "").strip())
        if not row["date"]:
            issue("invalid_date", index)
        if not str(row.get("description") or "").strip():
            issue("missing_description", index)
        parsed = {}
        for field in ("debit", "credit", "balance"):
            try:
                parsed[field] = number(row.get(field))
            except (InvalidOperation, ValueError, TypeError):
                parsed[field] = None
                issue(f"invalid_{field}", index)
            row[field] = str(parsed[field]) if parsed[field] is not None else None
        debit, credit = parsed["debit"], parsed["credit"]
        if debit is None or credit is None:
            issue("unknown_direction_or_amount", index)
        elif debit < 0 or credit < 0 or (debit > 0 and credit > 0):
            issue("ambiguous_debit_credit", index)
        elif debit == credit == 0:
            issue("zero_value_row", index)
        row["amount"] = str(max(debit, credit)) if debit is not None and credit is not None else None
        row.setdefault("category", "Uncategorized")
        row["extraction_method"] = "MISTRAL_OCR"
        rows.append(row)
        values.append(parsed)

    if not rows:
        issue("no_transactions")
    dates = [row["date"] for row in rows if row["date"]]
    if dates and dates != sorted(dates) and dates != sorted(dates, reverse=True):
        issue("unordered_dates")
    # Same-day groups can also be printed newest-first. Compare both arithmetic
    # orders, without ever reordering the returned rows or changing amounts.
    def edges(reverse):
        ordered = list(reversed(list(enumerate(values, 1)))) if reverse else list(enumerate(values, 1))
        result = []
        for (_, prev), (index, current) in zip(ordered, ordered[1:]):
            if all(v is not None for v in (prev["balance"], current["balance"], current["debit"], current["credit"])):
                result.append((index, prev["balance"] - current["debit"] + current["credit"] == current["balance"]))
        return result
    reverse = bool(len(set(dates)) > 1 and dates == sorted(dates, reverse=True))
    if len(set(dates)) <= 1:
        reverse = sum(not ok for _, ok in edges(True)) < sum(not ok for _, ok in edges(False))
    checks = edges(reverse)
    for index, ok in checks:
        if not ok:
            issue("running_balance_mismatch", index)
    if len(checks) < max(0, len(rows) - 1):
        issue("incomplete_running_balance_evidence")
    checked_summary = []
    summary = summary or {}
    for field, column in (("total_debits", "debit"), ("total_credits", "credit")):
        try:
            expected = number(summary.get(field))
            if expected is not None and all(v[column] is not None for v in values):
                checked_summary.append(field)
                if sum((v[column] for v in values), Decimal(0)) != expected:
                    issue(f"{field}_mismatch")
        except (InvalidOperation, TypeError, ValueError):
            issue(f"invalid_{field}")
        inclusive = field + '_including_opening'
        if inclusive in summary:
            try:
                expected = number(summary[inclusive])
                opening_component = number(summary.get(column + '_opening_component'))
                checked_summary.append(inclusive)
                if expected is None or opening_component is None or any(v[column] is None for v in values):
                    issue('invalid_' + inclusive)
                elif sum((v[column] for v in values), Decimal(0)) + opening_component != expected:
                    issue(inclusive + '_mismatch')
            except (InvalidOperation, TypeError, ValueError):
                issue('invalid_' + inclusive)
    count = summary.get("transaction_count")
    if count is not None:
        checked_summary.append("transaction_count")
        if count != len(rows):
            issue("printed_transaction_count_mismatch")
    chronological = list(reversed(values)) if reverse else values
    for field in ("opening_balance", "closing_balance"):
        try:
            expected = number(summary.get(field))
            if expected is not None and chronological:
                row = chronological[0] if field == "opening_balance" else chronological[-1]
                actual = row["balance"]
                if field == "opening_balance" and all(row[k] is not None for k in ("balance", "debit", "credit")):
                    actual = row["balance"] + row["debit"] - row["credit"]
                elif field == "opening_balance":
                    actual = None
                checked_summary.append(field)
                if actual is None or actual != expected:
                    issue(f"{field}_mismatch")
        except (InvalidOperation, TypeError, ValueError):
            issue(f"invalid_{field}")
    if not checks and not checked_summary:
        issue("insufficient_reconciliation_evidence")
    return {
        "status": "needs_review" if issues else "checks_passed",
        "raw_count": len(transactions), "retained_count": len(rows),
        "dropped_count": 0, "balance_checks": len(checks),
        "balance_matches": sum(ok for _, ok in checks),
        "printed_summary_checks": checked_summary, "issues": issues, "transactions": rows,
        "accuracy_claim": "Consistency checks only; completeness requires independent source comparison.",
    }
