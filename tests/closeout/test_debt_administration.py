import copy
import json

import pytest

from enterprise.closeout import debt_administration as d

C = {
    "repository_source_commit": "fixture",
    "repository_source_available_at": "2026-09-22T23:00:00Z",
    "publication_state": "COMMITTED_SOURCE_REVIEWABLE_NOT_RELEASE_ACCEPTANCE",
    "publishable_source_snapshot": True,
}


def source():
    return json.loads(d.SOURCE.read_text())


def test_population_and_current_release_not_backdated_payoff():
    r = d.build(context=C)
    assert len(r["assets"]) == 64
    assert [len(x["asset_ids"]) for x in r["filings"]] == [14, 44, 6]
    assert sum(int(x["principal_received_usd"]) for x in r["payoff_releases"]) == 13500000
    assert r["available_at"] == "2026-09-22T23:00:00Z"
    assert r["additional_cash_usd"] == r["additional_journal_usd"] == "0.00"
    earlier = d.build(context=C, as_of="2026-09-22T17:00:00Z")
    assert all(x["as_of_state"] == "NOT_YET_RELEASED" for x in earlier["payoff_releases"])
    assert all(x["as_of_state"] == "NOT_YET_ACKNOWLEDGED" for x in earlier["filings"])


@pytest.mark.parametrize(
    "mutation",
    [
        lambda s: s["assets"].pop(),
        lambda s: s["assets"].__setitem__(0, copy.deepcopy(s["assets"][1])),
        lambda s: s["assets"][0].update(owner="BST"),
        lambda s: s["filings"][0].update(submitted_at="2026-09-21T18:00:00Z"),
        lambda s: s["filings"][1]["asset_ids"].pop(),
        lambda s: s["filings"][2].update(real_filing=True),
        lambda s: s["payoff_releases"][0].update(principal_received_usd="12000000"),
        lambda s: s["payoff_releases"][0].update(new_cash_usd="11500000"),
        lambda s: s["fee_allocation"].update(additional_cash_usd="250.00"),
    ],
)
def test_adverse_source_mutations_fail(mutation):
    s = source()
    mutation(s)
    with pytest.raises(ValueError):
        d.build(source=s, context=C)
