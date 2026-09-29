"""Independent selected-review semantics; malformed native documents are not repaired."""

import json
from dataclasses import replace

import pytest

from enterprise.audit_suite import company_access_remediation_activity as activity
from enterprise.audit_suite.company_lifecycle_activity import LifecycleSourceRef, read_inputs
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError
from enterprise.audit_suite.operating_source_bridge import encoded, sha
from tests.audit_suite.test_company_access_remediation_operator import ROOT
from tests.audit_suite.test_company_access_remediation_operator import prepared as prepared_source


@pytest.fixture
def prepared(tmp_path):
    return prepared_source.__wrapped__(tmp_path)


def _recipe(value):
    return activity.AccessRemediationRecipe(
        **(
            value
            | {
                "branch_ids": tuple(value["branch_ids"]),
                "source_refs": tuple(LifecycleSourceRef(**r) for r in value["source_refs"]),
            }
        )
    )


def _malformed_query_source(tmp_path, prepared, query=None, *, fault=None):
    original, value = prepared
    original_store = CompanyStore(original / "company")
    with original_store._db() as db:
        rows = [
            dict(r)
            for r in db.execute(
                "SELECT * FROM versions ORDER BY company,branch,system,record,version"
            )
        ]
        systems = [dict(r) for r in db.execute("SELECT * FROM systems")]
    root = tmp_path / "malformed-native"
    root.mkdir(mode=0o700)
    target = CompanyStore(root)
    for system in systems:
        target.register_system(
            system["company"],
            system["branch"],
            system["system"],
            system["owner"],
        )
    pop_row = next(
        r
        for r in rows
        if r["system"] == "review_population"
        and r["branch"] == "activity-messy"
        and r["record"] == "PRIV-2027-Q2"
    )
    population = json.loads(pop_row["content"])
    if query is not None:
        population["query"] = query
    if fault == "inverted_period":
        population["period_start"] = "2027-08-01T00:00:00Z"
    new_population_hash = sha(encoded(population))
    for n, row in enumerate(rows):
        content = row["content"]
        if row["branch"] == "activity-messy" and row["record"] == "PRIV-2027-Q2":
            body = json.loads(content)
            if row["system"] == "review_population":
                body = population
            elif row["system"] in {"review_decisions", "review_reconciliation"}:
                body["population_sha256"] = new_population_hash
                if fault == "inverted_period":
                    body["period_start"] = population["period_start"]
                if fault == "decision_before_population" and row["system"] == "review_decisions":
                    row["event_at"] = row["available_at"] = "2027-07-01T00:00:30Z"
                if (
                    fault == "reconciliation_before_decision"
                    and row["system"] == "review_reconciliation"
                ):
                    row["event_at"] = row["available_at"] = "2027-07-01T00:01:30Z"
            if fault == "population_not_yet_available" and row["system"] == "review_population":
                row["available_at"] = "2027-07-01T00:02:30Z"
            if fault == "decision_not_yet_available" and row["system"] == "review_decisions":
                row["available_at"] = "2027-07-01T00:03:30Z"
            content = encoded(body)
        target.append_version(
            row["company"],
            row["branch"],
            row["system"],
            row["record"],
            expected_version=row["version"] - 1,
            command_id=f"native-{n}",
            event_at=row["event_at"],
            available_at=row["available_at"],
            content=content,
            provenance=json.loads(row["provenance"]),
            origin=row["origin"],
        )
    refs = []
    with target._db() as db:
        for ref in value["source_refs"]:
            checksum = db.execute(
                "SELECT sha256 FROM versions WHERE company=? AND branch=? "
                "AND system=? AND record=? AND version=?",
                tuple(ref[k] for k in ("company", "branch", "system", "record", "version")),
            ).fetchone()[0]
            refs.append(LifecycleSourceRef(**(ref | {"sha256": checksum})))
    _, pin = read_inputs(root, tuple(refs))
    return root, replace(_recipe(value), source_refs=tuple(refs), source_versions_sha256=pin)


@pytest.mark.parametrize(
    "query",
    [
        {"system": "application", "as_of_exclusive": "2027-08-01T00:00:00Z"},
        {"system": "directory", "as_of_exclusive": "2027-07-01T00:00:00Z"},
    ],
)
def test_native_population_query_must_match_selected_application_period(tmp_path, prepared, query):
    source, recipe = _malformed_query_source(tmp_path, prepared, query)
    with pytest.raises(CompanyStoreError):
        activity.generate_pair(
            tmp_path / "result", repository=ROOT, source_root=source, recipe=recipe
        )
    assert not (tmp_path / "result").exists()


def test_native_remediation_lineage_preserves_original_gap_and_operating_limits(tmp_path, prepared):
    source, value = prepared
    before = (source / "company/company.sqlite3").read_bytes()
    output = tmp_path / "continued"
    result = activity.generate_pair(
        output, repository=ROOT, source_root=source / "company", recipe=_recipe(value)
    )
    assert (source / "company/company.sqlite3").read_bytes() == before
    store = CompanyStore(output)
    with store._db() as db:
        rows = [dict(r) for r in db.execute("SELECT * FROM versions")]
        assert db.execute("SELECT COUNT(*) FROM grants").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM collections").fetchone()[0] == 0
    originals = {(r["branch"], r["system"], r["record"], r["version"]): r for r in rows}
    for row in rows:
        body = json.loads(row["content"])
        assert body["independent_assurance"] == "NOT_PERFORMED"
        assert body["population_completeness"] == "NOT_ESTABLISHED_OR_REMEDIATED_BY_THIS_SLICE"
        assert body["recorded_unresolved_population_ids"] == ["P014"]
        assert body["subject_person_id"] == "P015"
        assert body["parent_branch"] == "activity-messy"
        assert body["source_versions_sha256"] == value["source_versions_sha256"]
        assert [
            {k: v for k, v in ref.items() if k != "source_store_id"}
            for ref in body["source_records"]
        ] == sorted(
            value["source_refs"],
            key=lambda ref: tuple(
                ref[k] for k in ("company", "branch", "system", "record", "version")
            ),
        )
        for prior in body["previous_events"]:
            native = originals[row["branch"], prior["system"], prior["record"], prior["version"]]
            assert prior["sha256"] == native["sha256"] == sha(native["content"])
            assert native["available_at"] <= row["event_at"]

    def body(branch, system, version):
        return json.loads(
            next(
                r["content"]
                for r in rows
                if r["branch"] == branch and r["system"] == system and r["version"] == version
            )
        )

    assert body("removal-b", "validation_probes", 1)["removed_permission_probes"] == {
        "billing-admin": "ALLOW"
    }
    assert body("removal-b", "validation_probes", 2)["removed_permission_probes"] == {
        "billing-admin": "DENY"
    }
    assert body("removal-a", "validation_probes", 1)["removed_permission_probes"] == {
        "billing-admin": "DENY"
    }
    assert result["old_quarterly_sources_unchanged"] is True


@pytest.mark.parametrize(
    "fault",
    [
        "inverted_period",
        "decision_before_population",
        "reconciliation_before_decision",
        "population_not_yet_available",
        "decision_not_yet_available",
    ],
)
def test_native_review_chronology_precedes_continuation(tmp_path, prepared, fault):
    source, recipe = _malformed_query_source(tmp_path, prepared, fault=fault)
    with pytest.raises(CompanyStoreError):
        activity.generate_pair(
            tmp_path / "result", repository=ROOT, source_root=source, recipe=recipe
        )
    assert not (tmp_path / "result").exists()
