from decimal import Decimal

from app.finance import money, summarize_transactions


def test_money_avoids_float_rounding():
    assert money(0.1) + money(0.2) == Decimal("0.30")


def test_summary_separates_income_and_expenses():
    result = summarize_transactions([
        {"credit": "1000.00", "debit": "0"},
        {"credit": "0", "debit": "125.55"},
    ])
    assert result == {
        "income": Decimal("1000.00"),
        "expenses": Decimal("125.55"),
        "balance": Decimal("874.45"),
    }
