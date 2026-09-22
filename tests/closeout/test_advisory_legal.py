import json

import pytest

from enterprise.closeout import advisory_legal as a


def test_current_zero_grants_preserves_ten_thousand_units():
    r = a.build()
    assert r["issued_units"] == r["participant_count"] == 0
    assert r["unallocated_units"] == 10000
    assert r["financial_effects"]["additional_liability_usd"] == "0"


@pytest.mark.parametrize(
    "key,value",
    [
        ("pool_pct", "25"),
        ("sponsor", "ARU"),
        ("issued_grants", [{"units": 100}]),
        ("rights_excluded", []),
    ],
)
def test_source_cannot_amplify_economics(key, value):
    s = json.loads(a.SOURCE.read_text())
    s[key] = value
    with pytest.raises(ValueError):
        a.build(source=s)


def fixture():
    s = json.loads(a.SOURCE.read_text())
    r = {k: "DOCUMENTARY_TEST_FIXTURE_ONLY" for k in s["required_grant_fields"]}
    r.update(
        former_j2_end="2026-09-20",
        participant_initiated_contact="2026-09-21",
        grant_date="2026-09-22",
        no_serving_promise_attestation=True,
        eligibility_gate="Orientation",
        units=100,
        holdback_fraction="0.2",
        payment_schedule_acknowledged=True,
    )
    return r


def test_documentary_gate_is_not_an_award():
    r = a.validate_grant(fixture())
    assert r["qualification_reperformance_required"]
    assert not r["grant_issued"]


@pytest.mark.parametrize(
    "key,value",
    [
        ("participant_initiated_contact", "2026-09-20"),
        ("no_serving_promise_attestation", False),
        ("eligibility_gate", "Headquarters"),
        ("legal_review", ""),
        ("units", 10001),
        ("holdback_fraction", "1.2"),
    ],
)
def test_invalid_or_unqualified_documentation(key, value):
    r = fixture()
    r[key] = value
    with pytest.raises(ValueError):
        a.validate_grant(r)
