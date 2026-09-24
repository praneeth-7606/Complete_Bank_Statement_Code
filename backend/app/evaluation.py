"""Part 1 deterministic evaluators. Missing evidence is never a pass."""
from collections import Counter
from datetime import date

from .extraction_validation import number
from .observability import current_trace


def score(name, value, passed):
    return {"name": name, "value": value, "passed": passed}


def publish(scores):
    active = current_trace()
    if active:
        for item in scores:
            active.record_evaluation(**item)


def financial_key(row):
    day = row.get("date")
    day = day.isoformat() if isinstance(day, date) else str(day)
    # Evaluation fixtures use ISO dates. Invalid/missing money is a mismatch.
    date.fromisoformat(day)
    amounts = tuple(number(row.get(field)) for field in ("debit", "credit"))
    if any(value is None for value in amounts):
        raise ValueError("Missing debit or credit")
    balance = number(row.get("balance"))
    return (day, *amounts, balance)


def benchmark(expected, actual):
    """Multiset alignment preserves legitimate repeated transactions.

    Fields compared: ISO date, debit, credit, balance when labelled. Narration
    is excluded because production masking changes it. Category labels are
    matched only on unique financial keys; ambiguous duplicates are unscored.
    """
    if not expected:
        raise ValueError("Gold fixture must contain verified transactions")
    wanted = [financial_key(row) for row in expected]
    actual_keys = []
    for i, row in enumerate(actual):
        try:
            actual_keys.append(financial_key(row))
        except Exception:
            actual_keys.append(("invalid", i))
    expected_counts, actual_counts = Counter(wanted), Counter(actual_keys)
    matches = sum((expected_counts & actual_counts).values())
    precision = matches / len(actual) if actual else 0.0
    recall = matches / len(expected)
    scores = [score("transaction_precision", precision, precision == 1),
              score("transaction_recall", recall, recall == 1),
              score("financial_exact_match", float(expected_counts == actual_counts), expected_counts == actual_counts)]
    aligned = {key: row for key, row in zip(actual_keys, actual) if actual_counts[key] == 1}
    pairs = [(row["category"], aligned[key].get("category", "__missing__"))
             for key, row in zip(wanted, expected)
             if row.get("category") and expected_counts[key] == 1 and key in aligned]
    labelled = sum(bool(row.get("category")) for row in expected)
    if pairs:
        labels = {label for pair in pairs for label in pair}
        f1 = []
        for label in labels:
            tp = sum(gold == pred == label for gold, pred in pairs)
            fp = sum(gold != label and pred == label for gold, pred in pairs)
            fn = sum(gold == label and pred != label for gold, pred in pairs)
            f1.append(2 * tp / (2 * tp + fp + fn))
        macro = sum(f1) / len(f1)
        scores.append(score("category_macro_f1", macro, macro >= .90))
    else:
        scores.append(score("category_macro_f1", None, None))
    scores.append(score("category_label_coverage", len(pairs) / labelled if labelled else None,
                        len(pairs) == labelled if labelled else None))
    return scores


def categorization_integrity(before, after):
    # Categorization must preserve every financial field; it may reorder rows.
    try:
        intact = Counter(financial_key(row) for row in before) == Counter(financial_key(row) for row in after)
    except Exception:
        intact = False
    return [score("categorization_preserves_finances", float(intact), intact),
            score("category_accuracy", None, None)]


def persistence_integrity(expected, stored):
    def key(row):
        return tuple(str(row.get(field)) for field in ("transaction_id", "user_id", "upload_id", "date", "category")) + tuple(
            number(row.get(field)) for field in ("amount", "debit", "credit"))
    valid = Counter(key(row) for row in expected) == Counter(key(row) for row in stored)
    return [score("mongo_readback_exact_match", float(valid), valid)]


def insight_checks(output):
    items = output.get("insights") if isinstance(output, dict) else None
    valid = isinstance(items, list) and bool(items) and all(isinstance(item, str) and item.strip() for item in items)
    # The current free-text contract has no source-linked claims. Be explicit.
    return [score("insights_schema", float(valid), valid), score("insights_factual_accuracy", None, None)]
