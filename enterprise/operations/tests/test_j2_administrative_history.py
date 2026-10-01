import json
from copy import deepcopy

import pytest

from enterprise.operations import j2_administrative_history as j2


def data():
    return json.loads((j2.ROOT / j2.SOURCE).read_text())


def test_exact_existing_population():
    assert j2.validate(data())["additional_employees"] == 0
    assert j2.validate(data())["occupied_august"] == 181


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d["events"].pop(),
        lambda d: d["events"].append(deepcopy(d["events"][0])),
        lambda d: d["events"][0].update(company_joined_year=2021),
        lambda d: d["events"][0].update(current_office_appointment_date="2020-01-01"),
        lambda d: d["events"][0].update(acknowledgement_date="2025-01-01"),
        lambda d: d["events"][0].update(new_authority=True),
        lambda d: d["events"][4].update(commission_date="2026-01-05"),
        lambda d: d["events"][6].update(name="Invented Person"),
        lambda d: d["source_hashes"].update({"docs/j2/J2_ESTABLISHMENT.md": "0" * 64}),
    ],
)
def test_reject_administrative_history_corruption(change):
    d = data()
    change(d)
    with pytest.raises(ValueError):
        j2.validate(d)


def test_actual_availability_not_authored_day_or_historical_appointment():
    ctx = dict(
        repository_source_commit="test",
        repository_source_available_at="2026-09-22T18:30:00Z",
        publication_state="COMMITTED_SOURCE_REVIEWABLE_NOT_RELEASE_ACCEPTANCE",
        publishable_source_snapshot=True,
    )
    result = j2.build(ctx)
    assert j2.known_on(result, "2026-09-22T18:29:59Z") == []
    assert len(j2.known_on(result, "2026-09-22T18:30:00Z")) == 10
    ctx.update(
        publication_state="DIRTY_WORKING_COPY_PREVIEW_NOT_PUBLISHABLE",
        publishable_source_snapshot=False,
    )
    assert j2.known_on(j2.build(ctx), "2027-01-01T00:00:00Z") == []
