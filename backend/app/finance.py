from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable, Mapping

CENT = Decimal("0.01")


def money(value: object) -> Decimal:
    """Convert monetary input without introducing binary floating-point error."""
    return Decimal(str(value or 0)).quantize(CENT, rounding=ROUND_HALF_UP)


def summarize_transactions(transactions: Iterable[Mapping[str, object]]) -> dict[str, Decimal]:
    income = sum((money(t.get("credit")) for t in transactions), Decimal("0.00"))
    expenses = sum((money(t.get("debit")) for t in transactions), Decimal("0.00"))
    return {"income": income, "expenses": expenses, "balance": income - expenses}
