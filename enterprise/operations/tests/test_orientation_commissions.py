"""Independent population, chronology, tenure and assignment boundary checks."""

import json
from copy import deepcopy

import pytest

from enterprise.operations import orientation_commissions as oo


def source():
    return json.loads((oo.ROOT / oo.SOURCE).read_text())


def test_complete_current_census_and_preserved_failure():
    counts = oo.validate(source())
    assert counts["occupied"] == 18 and counts["authorized"] == 24
    assert counts["admissions_attempts"] == 19
    assert counts["preserved_nonselections"] == 1
    assert counts["renewals"] == counts["waivers"] == 0


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d["records"].pop(),
        lambda d: d["records"].append(deepcopy(d["records"][0])),
        lambda d: d["records"][1].update(person_id="P067"),
        lambda d: d["records"][1]["commission"].update(
            pin_id=d["records"][0]["commission"]["pin_id"]
        ),
        lambda d: d["records"][0]["recommendations"].pop(),
        lambda d: d["records"][0]["recommendations"][0].update(perspective="peer"),
        lambda d: d["records"][0]["packet"]["components"].remove("writing_sample"),
        lambda d: d["records"][0]["apprenticeship"].update(start="2021-01-01"),
        lambda d: d["records"][0]["council"].update(candidate_is_reviewer=True),
        lambda d: d["records"][0]["commission"].update(start="2020-01-01"),
        lambda d: d["records"][0]["commission"].update(end_exclusive="2029-02-02"),
        lambda d: d["records"][0]["commission"]["waivers"].append("TRAINING_WAIVED"),
        lambda d: d["records"][0]["commission"]["restrictions"].pop(),
        lambda d: d["records"][0]["assignment"].update(line_executive_role=True),
        lambda d: d["records"][7]["assignment"].update(voting_board_seat=True),
        lambda d: d["records"][7]["assignment"].update(post="OFFICE_OF_CEO"),
        lambda d: d["records"][11]["attempts"].pop(0),
        lambda d: d["records"][1].update(name="Unapproved Name"),
        lambda d: d["source_hashes"].pop("docs/j2/ORIENTATION_OFFICER_PROFESSION.md"),
    ],
)
def test_reject_invalid_population_or_qualification(mutate):
    data = source()
    mutate(data)
    with pytest.raises(ValueError):
        oo.validate(data)


def test_expiry_exclusive_and_no_automatic_renewal_or_line_assignment():
    grant = source()["records"][0]
    assert oo.assignment_allowed(grant, "2027-02-01", "2027-02-02")
    assert not oo.assignment_allowed(grant, "2027-02-02", "2027-02-03")
    assert not oo.assignment_allowed(grant, "2021-02-01", "2021-02-03")
    assert not oo.assignment_allowed(grant, "2026-08-01", "2026-09-01", line_authority=True)
    assert not oo.assignment_allowed(grant, "2026-08-01", "2026-09-01", voting_seat=True)


def test_new_history_not_available_at_fictional_effective_date():
    context = dict(
        repository_source_commit="test",
        repository_source_available_at="2026-09-22T20:01:00Z",
        publication_state="COMMITTED_SOURCE_REVIEWABLE_NOT_RELEASE_ACCEPTANCE",
        publishable_source_snapshot=True,
    )
    result = oo.build(context)
    assert oo.known_on(result, "2026-09-22T20:00:59Z") == []
    assert len(oo.known_on(result, "2026-09-22T20:01:00Z")) == 18
    context.update(publication_state="DIRTY_WORKING_COPY_PREVIEW_NOT_PUBLISHABLE")
    assert oo.known_on(oo.build(context), "2027-01-01T00:00:00Z") == []
