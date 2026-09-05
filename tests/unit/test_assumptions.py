from pathlib import Path

from sable_harbor.accounting.models import FactState
from sable_harbor.config.assumptions import load_assumptions


def test_baseline_assumptions_validate() -> None:
    assumptions = load_assumptions(Path("config/finance/assumptions"))
    assert assumptions
    assert assumptions[0].fact_state is FactState.MODEL_PROPOSED
    assert assumptions[0].reversible
