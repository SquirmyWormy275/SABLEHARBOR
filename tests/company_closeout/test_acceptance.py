import copy
import json

import pytest

from tools.company_closeout import acceptance
from tools.company_closeout.edition import EditionError, sha


@pytest.fixture
def accepted(tmp_path, monkeypatch):
    revision = "1" * 40
    merge = dict(
        pr_number=166,
        pr_url=f"https://github.com/{acceptance.REPOSITORY}/pull/166",
        merge_commit=revision,
        accepted_at="2026-09-21T10:00:00Z",
    )
    monkeypatch.setattr(acceptance, "read_merge", lambda number: merge)
    (tmp_path / "records.json").write_text('{"state":"PENDING_LOCAL_REVIEW","outcome":"FAILED"}')
    scope = dict(
        status="LOCKED_ON_REPOSITORY_ACCEPTANCE",
        adopted_sources=[
            dict(
                path="records.json",
                sha256=sha((tmp_path / "records.json").read_bytes()),
                scope="Adopt source implementation; retain event failure and local review state",
            )
        ],
        preserved_states=["PENDING_LOCAL_REVIEW", "FAILED", "UNADOPTED_MATERIAL_RIGHTS"],
        work_packages=[
            dict(id=f"SH-C{i:02d}", disposition="SCOPED_WITH_LIMITATIONS") for i in range(1, 11)
        ],
    )
    (tmp_path / "scope.json").write_text(json.dumps(scope))
    receipt = acceptance.collect(tmp_path, revision, 166, "scope.json")
    contract = dict(
        status="ACCEPTED_SCOPED_EDITION",
        source_commit_required=revision,
        acceptance_receipt=receipt,
        components=[
            dict(
                available_at="2026-09-21T11:00:00Z",
                members=[
                    dict(path=p, sha256=sha((tmp_path / p).read_bytes()))
                    for p in ("records.json", "scope.json")
                ],
            )
        ],
    )
    return tmp_path, contract


def test_actual_merge_scope_binding_preserves_source_states(accepted):
    root, contract = accepted
    before = (root / "records.json").read_bytes()
    acceptance.validate(contract)
    acceptance.verify_live(contract, root)
    assert (root / "records.json").read_bytes() == before
    assert b"PENDING_LOCAL_REVIEW" in before and b"FAILED" in before
    with pytest.raises(EditionError, match="merge commit"):
        acceptance.collect(root, "2" * 40, 166, "scope.json")


@pytest.mark.parametrize(
    "fault",
    [
        "missing",
        "wrong_source",
        "wrong_merge",
        "wrong_repo",
        "backdate",
        "omitted_source",
        "duplicate_source",
        "missing_package",
        "candidate",
    ],
)
def test_reject_false_or_incomplete_acceptance(accepted, fault):
    _, original = accepted
    contract = copy.deepcopy(original)
    r = contract["acceptance_receipt"]
    if fault == "missing":
        contract.pop("acceptance_receipt")
    elif fault == "wrong_source":
        r["source_commit"] = "2" * 40
    elif fault == "wrong_merge":
        r["merge_commit"] = "2" * 40
    elif fault == "wrong_repo":
        r["pr_url"] = "https://github.com/another/repository/pull/166"
    elif fault == "backdate":
        contract["components"][0]["available_at"] = "2026-09-15T00:00:00Z"
    elif fault == "omitted_source":
        contract["components"][0]["members"].pop(0)
    elif fault == "duplicate_source":
        r["adopted_sources"] *= 2
    elif fault == "missing_package":
        r["work_packages"].pop()
    else:
        contract["status"] = "REVIEW_CANDIDATE"
    with pytest.raises(EditionError):
        acceptance.validate(contract)


def test_reject_changed_adoption_scope_even_with_original_member_hash(accepted):
    root, contract = accepted
    contract["acceptance_receipt"]["adopted_sources"][0]["scope"] = "All failed events now passed"
    with pytest.raises(EditionError, match="differs"):
        acceptance.verify_live(contract, root)
    (root / "records.json").write_text('{"state":"LOCKED","outcome":"PASSED"}')
    with pytest.raises(EditionError, match="Changed"):
        acceptance.verify_live(contract, root)


@pytest.mark.parametrize("fault", ["unmerged", "open", "other_base", "other_repo"])
def test_readback_rejects_clean_but_unaccepted_branch(monkeypatch, fault):
    record = dict(
        merged=True,
        state="closed",
        base=dict(ref="main", repo=dict(full_name=acceptance.REPOSITORY)),
        html_url=f"https://github.com/{acceptance.REPOSITORY}/pull/166",
        merge_commit_sha="1" * 40,
        merged_at="2026-09-21T10:00:00Z",
    )
    if fault == "unmerged":
        record["merged"] = False
    elif fault == "open":
        record["state"] = "open"
    elif fault == "other_base":
        record["base"]["ref"] = "draft"
    else:
        record["base"]["repo"]["full_name"] = "other/repository"
    monkeypatch.setattr(
        acceptance.subprocess, "check_output", lambda *args, **kwargs: json.dumps(record)
    )
    with pytest.raises(EditionError, match="actually merged"):
        acceptance.read_merge(166)
