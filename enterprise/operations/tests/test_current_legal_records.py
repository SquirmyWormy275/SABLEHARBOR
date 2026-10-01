import copy
from decimal import Decimal as D

import pytest

from enterprise.operations.completed_period import build
from enterprise.operations.current_legal_records import validate


@pytest.fixture(scope="module")
def tables():
    return build()["tables"]


def test_current_legal_scope_and_compensation_are_separate(tables):
    assert validate(tables) == {
        "advisory_sows": 4,
        "retention_instruments": 8,
        "consultancy_completed_months": 8,
    }
    assert sum(D(r["fee_usd"]) for r in tables["advisory_execution"]) == D("100000")
    assert all(
        r["shi_signatory_name"] == "Rowan Bell"
        and r["liability_limit_state"] == "NOT_SELECTED_NO_TEMPLATE_LIMIT_ADOPTED"
        for r in tables["advisory_execution"]
    )
    assert sum(D(r["first_gross_installment_usd"]) for r in tables["retention_execution"]) == D(
        "250000"
    )
    assert all(
        r["second_installment_state"] == "FUTURE_DUE_CONDITIONAL_SERVICE_NOT_PAID"
        for r in tables["retention_execution"]
    )
    assert all(
        r["authority"] == "KNOWLEDGE_TRANSFER_ONLY_NO_LINE_OR_CONTRACT_AUTHORITY"
        for r in tables["consultancy_delivery"]
    )


@pytest.mark.parametrize(
    "table,field,value",
    [
        ("advisory_execution", "fee_usd", "30000"),
        ("advisory_execution", "liability_limit_state", "CAPPED_TO_FEE"),
        ("advisory_execution", "shi_signatory_person_id", "P029"),
        ("retention_execution", "second_installment_state", "PAID"),
        ("retention_execution", "employee_signature_name", "Wrong employee"),
        ("consultancy_delivery", "authority", "MAY_DISPATCH"),
        ("consultancy_delivery", "amount_usd", "1"),
    ],
)
def test_execution_cannot_invent_terms_or_change_source_payment(tables, table, field, value):
    broken = copy.deepcopy(tables)
    broken[table][0][field] = value
    with pytest.raises(ValueError):
        validate(broken)
