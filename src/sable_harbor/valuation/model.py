from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import yaml

D = Decimal


def load_valuation_config(
    path: Path = Path("config/finance/scenarios/valuation.yml"),
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
    return {
        "fact_state": config["fact_state"],
        "as_of_date": str(config["as_of_date"]),
        "components": components,
        "enterprise_value_low_base_high": enterprise,
        "transaction_bridge": bridge,
        "equity_purchase_price_base": equity,
        "qoe": qoe,
        "normalized_ebitda": normalized_ebitda,
    }
