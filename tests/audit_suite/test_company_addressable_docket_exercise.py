"""Pending addressable cases are not HIPAA environmental decisions."""

import hashlib
import json
import shutil
import sqlite3
from pathlib import Path

import pytest

from enterprise.audit_suite.company_addressable_docket_exercise import (
    COMPANY,
    OMITTED_LOCATOR,
    create,
    verify,
)
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError

REPOSITORY = Path(__file__).resolve().parents[2]


def _build(tmp_path):
    root = tmp_path / "addressable-docket"
    create(root, repository=REPOSITORY, clean_branch="ADDR-CLEAN", messy_branch="ADDR-MESSY")
    return root


def test_exact_pending_dockets_and_causal_exception(tmp_path):
    root = _build(tmp_path)
    assert verify(root)["native_version_count"] == 50
    receipt = json.loads((root / "RECEIPT.json").read_text())
    assert receipt["addressable_inventory_role"] == "22_ITEM_SOURCE_LOCATOR_INVENTORY_NOT_DECISIONS"
    assert receipt["hipaa_analysis_role"] == "SEPARATE_SECTION_DESIGN_ANALYSIS_NOT_22_ITEM_REGISTER"
    assert receipt["related_sh_pol003_gap"] == "OPEN_INSUFFICIENT_SOURCE_UNCHANGED"
    assert receipt["open_exception_counts"] == {"CLEAN": 0, "MESSY": 1}
    assert receipt["exception_event_row_counts"] == {"CLEAN": 0, "MESSY": 4}
    assert receipt["final_states"] == {"CLEAN": "PENDING_REVIEW", "MESSY": "QUARANTINED"}
    with sqlite3.connect(
        (root / "company.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True
    ) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute("SELECT * FROM versions ORDER BY branch,event_at").fetchall()
        assert len(rows) == 50
        assert all(row["event_at"] > row["imported_at"] for row in rows)
        candidates = [
            json.loads(r["content"]) for r in rows if r["system"] == "addressable_candidate"
        ]
        for scenario in ("CLEAN", "MESSY"):
            selected = [c for c in candidates if c["scenario"] == scenario]
            assert len(selected) == 22
            assert len({c["source_locator"] for c in selected}) == 22
            assert all(
                c["docket_state"] == "PENDING_ENVIRONMENT_AND_QUALIFIED_LEGAL_REVIEW"
                and c["reasonableness_analysis"] is None
                and c["equivalent_alternative_analysis"] is None
                and c["implemented_safeguard_evidence"] is None
                and c["approver_id"] is None
                and c["related_generic_exception_control_id"] == "SH-POL-003"
                and "control_id" not in c
                for c in selected
            )
        late = next(
            c
            for c in candidates
            if c["scenario"] == "MESSY" and c["source_locator"] == OMITTED_LOCATOR
        )
        assert late["late_backfill"] is True
        events = [json.loads(r["content"]) for r in rows if r["system"] == "docket_event"]
        messy = sorted((e for e in events if e["scenario"] == "MESSY"), key=lambda e: e["sequence"])
        assert [e["observed_docket_count"] for e in messy] == [21, 21, 22, 22]
        assert [e["missing_source_locators"] for e in messy] == [
            [OMITTED_LOCATOR],
            [OMITTED_LOCATOR],
            [],
            [],
        ]
        assert all(
            e["approved_substitution"] is False
            and e["actual_legal_approval"] is False
            and e["implemented_safeguards_claimed"] is False
            and e["actual_addressable_reviewer"] is None
            for e in events
        )
        assert db.execute("SELECT COUNT(*) FROM grants").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM collections").fetchone()[0] == 0


def test_availability_gate_preserves_late_discovery(tmp_path):
    root = _build(tmp_path)
    clone = tmp_path / "read-clone"
    shutil.copytree(root, clone)
    store = CompanyStore(clone)
    store.grant("LEARNER", "LOCAL-CHECK", COMPANY, "ADDR-MESSY", "docket_event")
    with pytest.raises(CompanyStoreError):
        store.read_version(
            "LEARNER",
            "LOCAL-CHECK",
            COMPANY,
            "ADDR-MESSY",
            "docket_event",
            "GATE-02",
            version=1,
            as_of="2027-03-02T10:59:59+00:00",
        )
    row = store.read_version(
        "LEARNER",
        "LOCAL-CHECK",
        COMPANY,
        "ADDR-MESSY",
        "docket_event",
        "GATE-02",
        version=1,
        as_of="2027-03-02T11:00:00+00:00",
    )
    assert json.loads(row["content"])["missing_source_locators"] == [OMITTED_LOCATOR]
    assert verify(root)["audit_task_credit"] is False


def test_resealed_blanket_approval_cannot_pass(tmp_path):
    root = _build(tmp_path)
    with sqlite3.connect(root / "company.sqlite3") as db:
        raw = db.execute(
            "SELECT content FROM versions WHERE branch='ADDR-MESSY' AND record='GATE-01'"
        ).fetchone()[0]
        body = json.loads(raw)
        body["approved_substitution"] = True
        db.execute("DROP TRIGGER no_version_update")
        db.execute(
            "UPDATE versions SET content=? WHERE branch='ADDR-MESSY' AND record='GATE-01'",
            (json.dumps(body).encode(),),
        )
    manifest_path = root / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["company_db_sha256"] = hashlib.sha256(
        (root / "company.sqlite3").read_bytes()
    ).hexdigest()
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    with pytest.raises(CompanyStoreError, match="Native docket source identity or clocks differ"):
        verify(root)


def test_rejects_branch_collision_and_destination_reuse(tmp_path):
    target = tmp_path / "invalid"
    with pytest.raises(CompanyStoreError, match="Distinct branch"):
        create(target, repository=REPOSITORY, clean_branch="SAME", messy_branch="SAME")
    assert not target.exists()
    target = _build(tmp_path)
    with pytest.raises(CompanyStoreError, match="New private"):
        create(target, repository=REPOSITORY, clean_branch="OTHER-A", messy_branch="OTHER-B")
