from decimal import Decimal

from bson.decimal128 import Decimal128

from app.main import _decimal_number
from app.models import Transaction


def test_transaction_normalizes_mongodb_decimal128_values():
    assert Transaction.normalize_decimal_values(Decimal128("125.50")) == Decimal("125.50")
    assert Transaction.normalize_decimal_values(Decimal128("0.00")) == Decimal("0.00")
    assert _decimal_number(Decimal128("125.50")) == 125.5
