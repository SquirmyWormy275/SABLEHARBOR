import json
from copy import deepcopy

import pytest

from enterprise.operations import j2_personnel_completion as j2
from enterprise.operations.completed_period import make_roster

CONTEXT = dict(
    repository_source_commit="fixture",
    repository_source_available_at="2026-09-22T23:00:00Z",
    publication_state="COMMITTED_SOURCE_REVIEWABLE_NOT_RELEASE_ACCEPTANCE",
    publishable_source_snapshot=True,
)


def source():
    return json.loads((j2.ROOT / j2.SOURCE).read_text())


def test_declared_profiles_and_existing_workforce_join():
    assert j2.validate(source()) == dict(
        profiles=10,
        preserved_names=6,
        new_names_existing_people=4,
        career_episodes=22,
        internal_reviews=10,
        additional_employees=0,
        additional_cash_usd="0.00",
    )
    people, _, _, _ = make_roster(
        j2.read("enterprise/operations/source/completed_period_2026_08.json")
    )
    before = deepcopy(people)
    updated = j2.join_people(people, known_on="2026-09-22T23:00:00Z", context=CONTEXT)
    assert people == before
    assert len(updated) == len(people) == 702
    assert sum(p["unit"].startswith("J2-") for p in updated) == 181
    old = {p["person_id"]: p for p in before}
    for p in updated:
        for key in set(p) - {"name", "position_title", "original_hire_year"}:
            assert p[key] == old[p["person_id"]][key]
    for _, (pid, name) in j2.NEW_NAMES.items():
        assert next(p for p in updated if p["person_id"] == pid)["name"] == name


@pytest.mark.parametrize(
    "mutation",
    [
        lambda d: d["profiles"].pop(),
        lambda d: d["profiles"].append(deepcopy(d["profiles"][0])),
        lambda d: d["profiles"][0].update(name="Changed accepted name"),
        lambda d: d["profiles"][0].update(company_joined_year=2019),
        lambda d: d["profiles"][6].update(name="Unreviewed replacement"),
        lambda d: d["profiles"][6].update(person_id="ADDITIONAL_EMPLOYEE"),
        lambda d: d["profiles"][0].update(legal_entity="SHIH"),
        lambda d: d["profiles"][0]["career_episodes"][0].update(end="2021"),
        lambda d: d["profiles"][0]["professional_limits"].update(new_payroll_usd="100.00"),
        lambda d: d["profiles"][0]["qualification_review"].update(reviewer_person_id="P063"),
        lambda d: d["profiles"][0]["qualification_review"].update(
            external_credential_or_license_claim=True
        ),
        lambda d: d["profiles"][4]["qualification_review"].update(commission_record_id=None),
        lambda d: d["profiles"][0]["qualification_review"]["observations"].pop(
            "authority_boundary_case"
        ),
        lambda d: d["profiles"][0].update(office_appointment_date="2020-01-01"),
        lambda d: d["source_hashes"].pop("docs/j2/J2_ESTABLISHMENT.md"),
    ],
)
def test_reject_identity_history_or_authority_drift(mutation):
    data = source()
    mutation(data)
    with pytest.raises(ValueError):
        j2.validate(data)


def test_known_on_and_dirty_preview_never_promote_names_early():
    people, _, _, _ = make_roster(
        j2.read("enterprise/operations/source/completed_period_2026_08.json")
    )
    assert j2.join_people(people, known_on="2026-09-22T22:59:59Z", context=CONTEXT) == people
    dirty = CONTEXT | {"publication_state": "DIRTY_WORKING_COPY_PREVIEW_NOT_PUBLISHABLE"}
    assert j2.join_people(people, known_on="2027-01-01T00:00:00Z", context=dirty) == people


def test_missing_duplicate_or_wrong_entity_join_rejected():
    people, _, _, _ = make_roster(
        j2.read("enterprise/operations/source/completed_period_2026_08.json")
    )
    variants = [people + [deepcopy(people[0])], [p for p in people if p["person_id"] != "P063"]]
    wrong = deepcopy(people)
    next(p for p in wrong if p["person_id"] == "P063")["legal_employer"] = "ARU"
    variants.append(wrong)
    for variant in variants:
        with pytest.raises(ValueError):
            j2.join_people(variant, known_on="2026-09-22T23:00:00Z", context=CONTEXT)
