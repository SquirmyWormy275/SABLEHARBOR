from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import yaml

from sable_harbor.exports.metadata import EPISTEMIC_MODE, source_snapshot_metadata

D = Decimal
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def load_valuation_config(
    path: Path = REPOSITORY_ROOT / "config/finance/scenarios/valuation.yml",
) -> dict[str, Any]:
    return cast(dict[str, Any], yaml.safe_load(path.read_text()))


def _component_values(component: dict[str, str]) -> tuple[D, D, D]:
    if component["method"] == "revenue_multiple":
        driver = D(component["driver"])
        return (
            driver * D(component["low_multiple"]),
            driver * D(component["base_multiple"]),
            driver * D(component["high_multiple"]),
        )
    return (
        D(component["low_value"]),
        D(component["base_value"]),
        D(component["high_value"]),
    )


def calculate_valuation(config: dict[str, Any]) -> dict[str, Any]:
    if config.get("schema_version") != "finance-valuation-preview/v1":
        raise ValueError("Valuation preview requires schema_version finance-valuation-preview/v1")
    if config.get("epistemic_mode") != EPISTEMIC_MODE:
        raise ValueError(f"Valuation preview requires epistemic_mode {EPISTEMIC_MODE}")
    classification = config.get("classification")
    if classification != "INTERNAL_SYNTHETIC_ANALYTICAL_PREVIEW_NOT_RELEASE_ARTIFACT":
        raise ValueError("Valuation preview requires its internal non-release classification")
    if config.get("scope_status") != "INCOMPLETE_MODEL_PROPOSAL":
        raise ValueError("Valuation preview requires scope_status INCOMPLETE_MODEL_PROPOSAL")
    if config.get("fact_state") != "MODEL_PROPOSED":
        raise ValueError("Valuation preview requires fact_state MODEL_PROPOSED")
    if config.get("as_of_date_basis") != "RETROSPECTIVE_SYNTHETIC_VALUATION_DATE":
        raise ValueError("Valuation preview requires an explicit retrospective date basis")
    components = {name: _component_values(values) for name, values in config["components"].items()}
    enterprise = tuple(sum(values[index] for values in components.values()) for index in range(3))
    bridge = {name: D(value) for name, value in config["transaction_bridge"].items()}
    equity = (
        enterprise[1]
        + bridge["cash_acquired"]
        - bridge["debt"]
        - bridge["debt_like_items"]
        - bridge["transaction_fees"]
        + bridge["working_capital_adjustment"]
    )
    qoe = {name: D(value) for name, value in config["qoe"].items()}
    normalized_ebitda = sum(qoe.values())
    result = {
        **source_snapshot_metadata(),
        "schema_version": config["schema_version"],
        "classification": classification,
        "scope_status": config["scope_status"],
        "fact_state": config["fact_state"],
        "as_of_date": str(config["as_of_date"]),
        "as_of_date_basis": config["as_of_date_basis"],
        "components": components,
        "enterprise_value_low_base_high": enterprise,
        "transaction_bridge": bridge,
        "equity_purchase_price_base": equity,
        "qoe": qoe,
        "normalized_ebitda": normalized_ebitda,
    }
    return result
