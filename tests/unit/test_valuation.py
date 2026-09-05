import json
from copy import deepcopy
from decimal import Decimal

import pytest
from typer.testing import CliRunner

from sable_harbor.cli import app
from sable_harbor.valuation.model import calculate_valuation, load_valuation_config


def test_sotp_transaction_bridge_and_qoe_are_config_driven() -> None:
    result = calculate_valuation(load_valuation_config())
    assert result["fact_state"] == "MODEL_PROPOSED"
    assert result["classification"] == (
        "INTERNAL_SYNTHETIC_ANALYTICAL_PREVIEW_NOT_RELEASE_ARTIFACT"
    )
    assert result["scope_status"] == "INCOMPLETE_MODEL_PROPOSAL"
    assert result["epistemic_mode"] == "RETROSPECTIVE_CURRENT_CANON"
    assert result["as_of_date"] == "2026-08-31"
    assert result["as_of_date_basis"] == "RETROSPECTIVE_SYNTHETIC_VALUATION_DATE"
    assert result["canon_effective_through"] == "2026-09-03"
    assert result["canon_reconciled_at"] == "2026-09-05"
    assert result["source_snapshot_ids"]["current_canon"]
    assert result["source_snapshot_digests"]["current_canon_content_sha256"]
    assert result["enterprise_value_low_base_high"] == (
        Decimal("261650000.00"),
        Decimal("445500000.00"),
        Decimal("701300000.00"),
    )
    assert result["equity_purchase_price_base"] == Decimal("348000000.00")
    assert result["normalized_ebitda"] == Decimal("9200000")


def test_cli_valuation_emits_the_same_governed_non_release_envelope() -> None:
    invocation = CliRunner().invoke(app, ["valuation"])
    assert invocation.exit_code == 0, invocation.output
    result = json.loads(invocation.stdout)
    assert result["classification"].endswith("NOT_RELEASE_ARTIFACT")
    assert result["epistemic_mode"] == "RETROSPECTIVE_CURRENT_CANON"
    assert result["as_of_date_basis"] == "RETROSPECTIVE_SYNTHETIC_VALUATION_DATE"


@pytest.mark.parametrize(
    ("field", "promoted_value"),
    [
        ("classification", "PUBLIC_SAFE_SYNTHETIC"),
        ("scope_status", "COMPLETE"),
        ("fact_state", "LOCKED_CANON"),
        ("epistemic_mode", "CONTEMPORANEOUS"),
    ],
)
def test_valuation_rejects_unsupported_promotion(field: str, promoted_value: str) -> None:
    config = deepcopy(load_valuation_config())
    config[field] = promoted_value
    with pytest.raises(ValueError):
        calculate_valuation(config)
