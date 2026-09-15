import copy

import pytest

from enterprise.operations.payroll_legal_bridge import verify


def fixture():
    edition = {
        "tables": {
            "payroll": [
                {"legal_entity": "PS", "gross_usd": "156250", "employer_burden_usd": "46875"}
            ]
        }
    }
    journal = [
        dict(
            scenario="base",
            year=2026,
            month=8,
            entity=entity,
            account=account,
            signed_usd=str(amount),
            source_id=f"CO-PAYROLL-{entity}-202608",
        )
        for entity, account, amount in [
            ("PS", "5100", 78125),
            ("PS", "2150", -78125),
            ("RWH", "1150", 78125),
            ("RWH", "5100", -78125),
        ]
    ]
    trial = [
        dict(
            scenario="base",
            year=2026,
            month=month,
            entity="PS",
            account="5100",
            signed_usd=str(value),
        )
        for month, value in [(7, 875000), (8, 1078125)]
    ]
    return edition, journal, trial


def test_legal_employer_paid_on_behalf_reconciles():
    assert verify(*fixture())["additional_group_expense_usd"] == "0.00"


@pytest.mark.parametrize(
    "mutation", ["duplicate", "reverse", "period", "cash", "entity", "uncorrected_legal", "omit"]
)
def test_balanced_wrong_legal_payroll_is_rejected(mutation):
    edition, rows, trial = fixture()
    if mutation == "duplicate":
        rows += copy.deepcopy(rows)
    elif mutation == "reverse":
        for row in rows:
            row["signed_usd"] = str(-int(row["signed_usd"]))
    elif mutation == "period":
        rows[0]["month"] = 9
    elif mutation == "cash":
        rows[1]["account"] = "1000"
    elif mutation == "entity":
        rows[0]["entity"] = "SHI"
    elif mutation == "uncorrected_legal":
        trial[1]["signed_usd"] = "1000000"
    else:
        rows.pop()
    with pytest.raises(ValueError):
        verify(edition, rows, trial)
