import copy
import json

import pytest

from enterprise.ccf.company_closeout.host_terms import SOURCE, validate


def source():
    return json.loads(SOURCE.read_text())


def order():
    return {
        "order_id": "TEST-ONLY",
        "instrument_id": "SH-CRADLE-KGM-B-20260922",
        "start": "2026-10-01",
        "end": "2026-12-29",
        "SH_acceptor": "P025",
        "host_acceptor": "SYN-HOST-KGM-REP-001",
        "acceptance_received_at": "2026-09-30T12:00:00+00:00",
        "scope": "Designated test-only run",
        "interface_revision": "S17-A",
        "sale_capable": False,
        "economics": {
            "eligible_proceeds": "None; test-only no-sale run",
            "deductions": "None",
            "currency": "USD",
            "host_payment_formula": "Explicit zero for this test fixture",
            "cost_responsibility": "Test fixture only",
        },
    }


def test_current_two_instruments_no_orders_or_cash():
    assert validate()["accepted_work_orders"] == 0


def test_ninety_days_permitted_not_ninety_one():
    data = source()
    data["accepted_work_orders"] = [order()]
    assert validate(data)["accepted_work_orders"] == 1
    data["accepted_work_orders"][0]["end"] = "2026-12-30"
    with pytest.raises(ValueError, match="duration"):
        validate(data)


@pytest.mark.parametrize(
    "key,value,message",
    [
        ("start", "2026-09-14", "backdated"),
        ("host_acceptor", "P025", "authority"),
        ("acceptance_received_at", "2026-10-02T00:00:00+00:00", "before operation"),
    ],
)
def test_rejects_wrong_period_authority_and_late_acceptance(key, value, message):
    data = source()
    row = order()
    row[key] = value
    data["accepted_work_orders"] = [row]
    with pytest.raises(ValueError, match=message):
        validate(data)


def test_blank_economics_not_zero_and_demotte_requires_title():
    data = source()
    row = order()
    row["economics"]["host_payment_formula"] = ""
    data["accepted_work_orders"] = [row]
    with pytest.raises(ValueError, match="economics"):
        validate(data)
    row = order()
    row.update(
        instrument_id="SH-CRADLE-DEMOTTE-B-20260922",
        host_acceptor="SYN-HOST-DEMOTTE-REP-001",
        sale_capable=True,
    )
    data["accepted_work_orders"] = [row]
    with pytest.raises(ValueError, match="title"):
        validate(data)


def test_notice_runs_from_receipt_and_no_duplicate_orders():
    data = source()
    row = order()
    row.update(
        exit_notice_received_at="2026-10-01T12:00:00+00:00",
        early_exit_at="2026-10-31T11:59:59+00:00",
    )
    data["accepted_work_orders"] = [row]
    with pytest.raises(ValueError, match="notice"):
        validate(data)
    row["early_exit_at"] = "2026-10-31T12:00:00+00:00"
    validate(data)
    data["accepted_work_orders"].append(copy.deepcopy(row))
    with pytest.raises(ValueError, match="duplicate"):
        validate(data)


def test_rejects_unapproved_rate_and_proposal_drift():
    data = source()
    data["common_terms"]["permanent_host_rate"] = "0.20"
    with pytest.raises(ValueError, match="approved term"):
        validate(data)
    data = source()
    data["proposal"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="proposal bytes"):
        validate(data)


def test_same_day_receipt_after_date_only_start_is_late():
    data = source()
    row = order()
    row["acceptance_received_at"] = "2026-10-01T00:00:01+00:00"
    data["accepted_work_orders"] = [row]
    with pytest.raises(ValueError, match="before operation"):
        validate(data)
