import asyncio

from app.agent_categorization import CategorizationAgent
from app.data_masker import DataMasker


def test_extracts_allowlisted_merchant_before_upi_masking():
    masker = DataMasker()
    transaction = masker.mask_transaction({"description": "UPI/zomato.order@okaxis/123456789012"})

    assert transaction["merchant_label"] == "ZOMATO"
    assert "zomato.order" not in transaction["description"]
    assert "123456789012" not in transaction["description"]


def test_does_not_promote_personal_upi_id_to_merchant_label():
    masker = DataMasker()
    transaction = masker.mask_transaction({"description": "UPI/praneeth.friend@oksbi/123456789012"})

    assert "merchant_label" not in transaction
    assert "praneeth.friend" not in transaction["description"]


def test_masks_hdfc_style_upi_counterparty_name_outside_handle():
    masker = DataMasker()
    transaction = masker.mask_transaction(
        {"description": "UPI-ANITA KUMARI-anita.kumari@okaxis-123456789012"}
    )

    assert "ANITA KUMARI" not in transaction["description"]
    assert transaction["description"] == "UPI-<UPI_NARRATION_REDACTED>"
    assert "merchant_label" not in transaction


def test_safe_merchant_label_reaches_deterministic_categorization():
    agent = object.__new__(CategorizationAgent)
    agent._active_corrections = {}
    agent._active_user_id = None

    result = asyncio.run(
        agent.categorize_transactions(
            [{
                "description": "UPI/****@okaxis/100.00",
                "merchant_label": "BSNL",
                "amount": "100.00",
                "debit": "100.00",
                "credit": "0",
            }],
            corrections=[],
        )
    )

    assert result[0]["category"] == "Bills & Utilities"
    assert result[0]["source"] == "merchant"
