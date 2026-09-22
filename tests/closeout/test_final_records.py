import json
from copy import deepcopy

import pytest

from enterprise.closeout import final_records as final
from enterprise.closeout import successor_records as previous
from enterprise.operations import completed_period, exports

CONTEXT = dict(
    repository_source_commit="fixture-head",
    repository_source_available_at="2026-09-22T23:00:00Z",
    publication_state="COMMITTED_SOURCE_REVIEWABLE_NOT_RELEASE_ACCEPTANCE",
    publishable_source_snapshot=True,
)


@pytest.fixture(scope="module")
def tables():
    return final.collect(CONTEXT)


def test_previous_tables_and_contract_unchanged(tables):
    old = previous.collect(CONTEXT)
    assert all(tables[name] == rows for name, rows in old.items())
    schema, scope = final.contracts()
    old_schema, old_scope = previous.contracts()
    assert all(schema[n] == v for n, v in old_schema.items())
    assert all(scope[n] == v for n, v in old_scope.items())
    receipt = final.validate_tables(tables, CONTEXT)
    assert sum(receipt["counts"].values()) == 1753
    assert receipt["additional_cash_usd"] == "0.00"


def test_names_join_without_money_or_person_changes(tables):
    people = {
        r["record_id"]: json.loads(r["payload_json"]) for r in tables["final_completed_people"]
    }
    original = completed_period.make_roster(completed_period.read(completed_period.SOURCE))[0]
    assert set(people) == {p["person_id"] for p in original}
    for person in original:
        for field in ["annual_salary_usd", "fte", "legal_employer", "position_id", "status"]:
            assert people[person["person_id"]][field] == person[field]
    assert people["SH-EMP-J2-HQ-0003"]["name"] == "Miriam Solano"
    assert people["SH-EMP-J2-CONTACT-0002"]["name"] == "Owen Faraday"
    assert people["SH-EMP-J2-JUDGMENT-0002"]["name"] == "Nadia Ivers"
    assert people["SH-EMP-J2-ORIENTATION-0002"]["name"] == "Leila Soren"
    assert all(
        json.loads(r["payload_json"])["implicit_grants"] == 0
        for r in tables["final_information_policy_subjects"]
    )


@pytest.mark.parametrize(
    "mutation",
    [
        lambda t: t["final_completed_people"].pop(),
        lambda t: t["final_completed_people"].append(deepcopy(t["final_completed_people"][0])),
        lambda t: t["final_personnel_profiles"][0].update(available_at="2026-09-22T00:00:00Z"),
        lambda t: t["final_completed_people"][0].update(entity="ARU"),
        lambda t: t["final_information_policy_subjects"].pop(),
        lambda t: t["final_personnel_profiles"][0].update(payload_json="{}"),
    ],
)
def test_adverse_populations_and_provenance(tables, mutation):
    data = deepcopy(tables)
    mutation(data)
    with pytest.raises(ValueError):
        final.validate_tables(data, CONTEXT)


def test_known_on_and_completed_period(tables):
    assert not final.visible(tables, effective_on="2026-08-31", known_on="2026-09-22T22:59:59Z")[
        "final_completed_people"
    ]
    assert (
        len(
            final.visible(tables, effective_on="2026-08-31", known_on="2026-09-22T23:00:00Z")[
                "final_completed_people"
            ]
        )
        == 702
    )
    assert not final.visible(tables, effective_on="2026-09-22", known_on="2026-09-22T23:00:00Z")[
        "final_completed_people"
    ]
    assert all(
        json.loads(r["payload_json"])["available_at"] == "2026-09-22T23:00:00Z"
        for r in tables["final_completed_people"]
    )


def test_existing_sqlite_roundtrip(tables, tmp_path):
    schema, scope = final.contracts()
    selected = {name: schema[name] for name in tables}
    exports.validate_schema(tables, selected, {name: scope[name] for name in tables})
    target = tmp_path / "records.sqlite"
    exports.database(target, tables, selected)
    exports.verify_database(target, tables, selected)


def test_legal_populations_separate_authority_and_money(tables):
    assert len(tables["final_debt_asset_identifiers"]) == 64
    assert len(tables["final_debt_fixture_sites"]) == 2
    assert len(tables["final_debt_filings"]) == 3
    releases = [json.loads(r["payload_json"]) for r in tables["final_debt_payoff_releases"]]
    assert sum(int(r["principal_received_usd"]) for r in releases) == 13500000
    assert all(r["new_cash_usd"] == "0" for r in releases)
    filings = [json.loads(r["payload_json"]) for r in tables["final_debt_filings"]]
    assert all(r["fee_allocation"]["amount_usd"] == "250.00" for r in filings)
    assert all(r["fee_allocation"]["additional_cash_usd"] == "0.00" for r in filings)
    carry = json.loads(tables["final_advisory_carry_disposition"][0]["payload_json"])
    assert carry["participant_count"] == carry["issued_units"] == 0
    assert tables["final_advisory_carry_disposition"][0]["entity"] == "SHI"
    assert tables["final_advisory_carry_disposition"][0]["unit"] == "advisory"
    old = final.visible(tables, effective_on="2026-08-31", known_on="2026-09-23T00:00:00Z")
    assert not old["final_debt_payoff_releases"]  # January payoff is not September release.


@pytest.mark.parametrize(
    "mutation",
    [
        lambda t: t["final_debt_asset_identifiers"].pop(),
        lambda t: t["final_debt_fixture_sites"][0].update(entity="BST"),
        lambda t: t["final_debt_filings"][0].update(additional_cash_usd="250.00"),
        lambda t: t["final_debt_payoff_releases"][0].update(effective_from="2026-01-07"),
        lambda t: t["final_advisory_carry_disposition"][0].update(
            payload_json='{"issued_units":1}'
        ),
        lambda t: t["final_debt_filings"][0].update(source_sha256="0" * 64),
    ],
)
def test_legal_export_cannot_expand_rights_or_backdate(tables, mutation):
    changed = deepcopy(tables)
    mutation(changed)
    with pytest.raises(ValueError):
        final.validate_tables(changed, CONTEXT)


def test_legal_authorship_floor_even_with_earlier_context():
    ctx = CONTEXT | {"repository_source_available_at": "2026-09-22T12:00:00Z"}
    rows = final.collect(ctx)
    for name in ["final_debt_filings", "final_advisory_carry_disposition"]:
        assert all(r["available_at"] > "2026-09-22T18:00:00" for r in rows[name])
        assert not final.visible(rows, effective_on="2026-09-22", known_on="2026-09-22T18:00:00Z")[
            name
        ]
