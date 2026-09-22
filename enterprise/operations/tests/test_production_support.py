import copy
from decimal import Decimal as D

import pytest

from enterprise.operations.completed_period import build
from enterprise.operations.production_support import validate


@pytest.fixture(scope="module")
def tables():
    return build()["tables"]


def test_complete_ps_work_population_preserves_cost(tables):
    result = validate(tables)
    assert result["employees"] == 12
    assert D(result["loaded_payroll_usd"]) == 203125
    assert D(result["production_support_payroll_usd"]) == 82875
    assert D(result["selling_corporate_payroll_usd"]) == 120250
    for row in tables["production_support_work"]:
        assert D(row["production_support_hours"]) + D(row["other_work_hours"]) == D(
            row["worked_hours"]
        )


@pytest.mark.parametrize("change", ["omit", "duplicate", "cost", "time"])
def test_work_or_cost_population_mutations_fail(tables, change):
    broken = copy.deepcopy(tables)
    rows = broken["production_support_work"]
    if change == "omit":
        rows.pop()
    elif change == "duplicate":
        rows.append(rows[0])
    else:
        rows[0][
            "production_support_payroll_usd" if change == "cost" else "production_support_hours"
        ] = "0"
    with pytest.raises(ValueError, match="Production-support"):
        validate(broken)
