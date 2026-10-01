"""Migration preserves operations while preventing authoring/Key and custody leaks."""

import copy
import json
import sqlite3
from pathlib import Path

import pytest

from enterprise.audit_suite import company_operational_projection as source
from enterprise.audit_suite.company_store import CompanyStoreError
from enterprise.audit_suite.operating_source_bridge import encoded, sha

REPOSITORY = Path(__file__).resolve().parents[2]
PRIVATE = Path("/home/kingoftheeast/Projects/SABLEHARBOR-audit-suite")


@pytest.fixture
def created(tmp_path):
    root = tmp_path / "library"
    source.create(root, repository=REPOSITORY, private_repository=PRIVATE)
    return root


def _reseal(root):
    manifest = json.loads((root / "MANIFEST.json").read_text())
    manifest["files"] = {name: source._digest(root / name) for name in manifest["files"]}
    (root / "MANIFEST.json").write_text(json.dumps(manifest))


def _edit(root, mutate):
    with sqlite3.connect(root / "company.sqlite3") as db:
        db.row_factory = sqlite3.Row
        trigger = db.execute(
            "SELECT sql FROM sqlite_master WHERE name='no_version_update'"
        ).fetchone()[0]
        db.execute("DROP TRIGGER no_version_update")
        mutate(db)
        db.execute(trigger)
    _reseal(root)


def _verify(root):
    return source.verify(root, repository=REPOSITORY, private_repository=PRIVATE)


def test_business_discrepancy_correction_and_custody_survive(created):
    receipt = _verify(created)
    assert receipt["native_versions"] == 69
    with sqlite3.connect(f"file:{created}/company.sqlite3?mode=ro&immutable=1", uri=True) as db:
        db.row_factory = sqlite3.Row
        rows = [dict(r) for r in db.execute("SELECT * FROM versions")]
    assert len(rows) == 69
    indexed = {(r["branch"], r["system"], r["record"]): json.loads(r["content"]) for r in rows}
    branch = "HARBOR-OPERATIONS-B"
    scan = indexed[branch, "sec003vuln.vulnerability_scan", "SCAN-OCT-01"]
    assert scan["action"] == "SCAN_RESULT"
    assert len(scan["detail"]["observed_asset_ids"]) == 3
    assert scan["detail"]["reported_count"] == 4
    assert scan["detail"]["finding_asset_ids"] == []
    signoff = indexed[branch, "sec003vuln.vulnerability_reconciliation", "RECON-OCT-01"]
    assert signoff["action"] == "COVERAGE_ATTESTATION"
    assert signoff["detail"]["reported_coverage"] == "4/4"
    assert signoff["detail"]["actual_coverage"] == "3/4"
    assert signoff["detail"]["decision"] == "ACCEPTED"
    census = indexed[branch, "sec003vuln.vulnerability_inventory", "CENSUS-OCT-01"]
    assert census["detail"]["omitted_asset_id"] == "SIM-BOI-OPS-01"
    rescan = indexed[branch, "sec003vuln.vulnerability_scan", "RESCAN-NOV-01"]
    assert rescan["detail"]["finding_asset_ids"] == ["SIM-BOI-EDGE-01"]
    assert rescan["event_at"] > scan["event_at"]
    assert (
        indexed[branch, "sec003vuln.vulnerability_exception", "EXC-SEC003-Q4-01"]["detail"][
            "status"
        ]
        == "OPEN"
    )
    recheck = indexed[branch, "sec005operated.security_reconciliation", "SECURITY-RECHECK-NOV-01"]
    assert recheck["reviewer_id"] == recheck["october_reviewer_id"]
    assert recheck["independent_of_own_prior_review"] is False
    assert (
        len(
            indexed[branch, "sec005operated.security_monitor", "MONITOR-OCT-01"][
                "received_probe_record_ids"
            ]
        )
        == 2
    )
    for r in rows:
        body, provenance = json.loads(r["content"]), json.loads(r["provenance"])
        assert not source._leaks(body)
        assert not source._leaks(provenance)
        assert provenance["name"].endswith(".json")
        assert receipt["initialized_at"] <= r["imported_at"] <= receipt["completed_at"]
        assert r["origin"] == "MIGRATED_SYNTHETIC_HISTORY"
    projected_hashes = {r["sha256"] for r in rows}
    private = json.loads((created / "TRANSFORMATION.json").read_text())
    assert len(private["records"]) == 69
    for item in private["reference_custody"]:
        ref = item["projected_reference"]
        if "sha256" in ref:
            assert ref["sha256"] in projected_hashes
            assert ref["branch"] in source.BRANCHES
            assert ref["available_at"] <= next(
                r["event_at"]
                for r in rows
                if json.loads(r["provenance"])["raw_content_sha256"] == item["input_sha256"]
            )
        else:
            assert ref["status"] == "RESTRICTED_UPSTREAM_NOT_IMPORTED"
            assert "provenance" not in ref
    assert (
        receipt["engagement_created"]
        is receipt["access_granted"]
        is receipt["audit_task_credit"]
        is False
    )


def test_resealed_company_answer_annotation_rejected(created):
    def mutate(db):
        row = db.execute("SELECT * FROM versions LIMIT 1").fetchone()
        body = json.loads(row["content"])
        body["rubric"] = "EXPECTED_FINDING"
        data = encoded(body)
        db.execute(
            "UPDATE versions SET content=?,sha256=? WHERE command_id=?",
            (data, sha(data), row["command_id"]),
        )

    _edit(created, mutate)
    with pytest.raises(CompanyStoreError, match="native body/provenance/clock custody"):
        _verify(created)


def test_resealed_answer_bearing_provenance_rejected(created):
    _edit(
        created,
        lambda db: db.execute(
            "UPDATE versions SET provenance=json_set(provenance,'$.scenario','MESSY')"
        ),
    )
    with pytest.raises(CompanyStoreError, match="native body/provenance/clock custody"):
        _verify(created)


@pytest.mark.parametrize("attack", ["MISSING", "INERT", "EXTRA_TABLE"])
def test_resealed_schema_or_trigger_rejected(created, attack):
    with sqlite3.connect(created / "company.sqlite3") as db:
        if attack == "EXTRA_TABLE":
            db.execute("CREATE TABLE hidden_answers(answer TEXT)")
        else:
            db.execute("DROP TRIGGER no_version_update")
            if attack == "INERT":
                db.execute(
                    "CREATE TRIGGER no_version_update BEFORE UPDATE ON versions BEGIN SELECT 1; END"
                )
    _reseal(created)
    with pytest.raises(CompanyStoreError, match="exact database schema"):
        _verify(created)


def test_resealed_extra_receipt_branch_rejected(created):
    path = created / "RECEIPT.json"
    value = json.loads(path.read_text())
    value["branches"].append("UNDECLARED")
    path.write_text(json.dumps(value))
    _reseal(created)
    with pytest.raises(CompanyStoreError, match="exact receipt"):
        _verify(created)


def test_resealed_access_grant_rejected(created):
    with sqlite3.connect(created / "company.sqlite3") as db:
        row = db.execute("SELECT company,branch,system FROM systems LIMIT 1").fetchone()
        db.execute("INSERT INTO grants VALUES(?,?,?,?,?,?)", ("unapproved", "uncreated", *row, 1))
    _reseal(created)
    with pytest.raises(CompanyStoreError, match="unauthorized access"):
        _verify(created)


def test_resealed_historical_import_clock_rejected(created):
    _edit(
        created,
        lambda db: db.execute("UPDATE versions SET imported_at='2025-01-01T00:00:00.000000+00:00'"),
    )
    with pytest.raises(CompanyStoreError, match="native body/provenance/clock custody"):
        _verify(created)


def test_missing_explicit_annotation_rule_and_cross_branch_fail_closed():
    registry = source._registry(REPOSITORY)
    _, _, rows, _ = source._inputs(registry, PRIVATE)
    bad = copy.deepcopy(registry)
    del bad["records"][0]["operations"]["/scenario"]
    with pytest.raises(CompanyStoreError, match="undeclared answer annotation"):
        source._project(bad, rows)
    bad = copy.deepcopy(registry)
    referenced = next(
        p
        for p in bad["records"]
        if any(
            o["kind"] == "NATIVE_REFERENCE" and rows[p["input_sha256"]]["cohort"] == "sec003vuln"
            for o in p["operations"].values()
        )
    )
    referenced["branch"] = (
        source.BRANCHES[1] if referenced["branch"] == source.BRANCHES[0] else source.BRANCHES[0]
    )
    with pytest.raises(CompanyStoreError, match="cross-branch"):
        source._project(bad, rows)


def test_private_reference_manifest_drift_rejected(created):
    p = created / "TRANSFORMATION.json"
    value = json.loads(p.read_text())
    value["reference_custody"][0]["raw_reference"]["sha256"] = "0" * 64
    p.write_text(json.dumps(value))
    _reseal(created)
    with pytest.raises(CompanyStoreError, match="exact transformation"):
        _verify(created)


def test_dangling_sidecar_rejected_without_touching_source(created):
    (created / "company.sqlite3-wal").symlink_to(created / "missing")
    with pytest.raises(CompanyStoreError, match="exact private file set"):
        _verify(created)
