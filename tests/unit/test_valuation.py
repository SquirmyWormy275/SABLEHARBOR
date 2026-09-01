from decimal import Decimal

from sable_harbor.valuation.model import calculate_valuation, load_valuation_config


def test_sotp_transaction_bridge_and_qoe_are_config_driven() -> None:
    result = calculate_valuation(load_valuation_config())
    assert result["fact_state"] == "MODEL_PROPOSED"
    assert result["enterprise_value_low_base_high"] == (
        Decimal("261650000.00"),
        Decimal("445500000.00"),
        Decimal("701300000.00"),
    )
    assert result["equity_purchase_price_base"] == Decimal("348000000.00")
    assert result["normalized_ebitda"] == Decimal("9200000")
