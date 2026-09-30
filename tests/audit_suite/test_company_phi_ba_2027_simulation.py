"""Payload-free 2027 ePHI/BA simulation depends on exact reviewed site releases."""

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from enterprise.audit_suite import company_phi_ba_2027_simulation as simulation
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError
from enterprise.audit_suite.operating_source_bridge import encoded

REPOSITORY = Path(__file__).resolve().parents[2]


def _write(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")
    path.chmod(0o600)


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _transition(tmp_path, monkeypatch):
    root = tmp_path / "transition"
    root.mkdir(mode=0o700)
    store = CompanyStore(root)
    branches = {"CLEAN": "TRANS-CLEAN", "MESSY": "TRANS-MESSY"}
    statuses = {
        "CLEAN": {"RENO": "OPERATING_PRIMARY_SIMULATED", "BOISE": "OPERATING_RECOVERY_SIMULATED"},
        "MESSY": {
            "RENO": "OPERATING_PRIMARY_SIMULATED",
            "BOISE": "OPERATING_RECOVERY_WITH_OPEN_EXCEPTION_SIMULATED",
        },
    }
    records = {}
    for scenario, branch in branches.items():
        store.register_system(simulation.COMPANY, branch, "site_release", "AS-P007")
        records[scenario] = []
        for site in ("RENO", "BOISE"):
            date = (
                "2027-05-20T14:00:00+00:00"
                if site == "RENO"
                else "2027-07-28T14:00:00+00:00"
                if scenario == "CLEAN"
                else "2027-08-10T14:00:00+00:00"
            )
            body = {
                "status": statuses[scenario][site],
                "fictional_in_universe_operating_release": True,
                "real_world_provider_operation": False,
                "actual_real_world_phi_processing": False,
            }
            records[scenario].append(
                store.append_version(
                    simulation.COMPANY,
                    branch,
                    "site_release",
                    f"RL-{site}",
                    expected_version=0,
                    command_id=f"RT-{branch}-RL-{site}-V1",
                    event_at=date,
                    available_at=date,
                    content=encoded(body),
                    provenance={"source_reference": "test-transition-fixture"},
                )
            )
    receipt = {
        "schema": simulation.TRANSITION_SCHEMA,
        "company": simulation.COMPANY,
        "branches": branches,
        "records": records,
        "source_pins": simulation.SOURCE_PINS,
        "open_exception_counts": {"CLEAN": 0, "MESSY": 1},
        "final_site_status": statuses,
    }
    _write(root / "RECEIPT.json", receipt)
    manifest = {
        "schema": simulation.TRANSITION_SCHEMA + "_MANIFEST",
        "receipt_sha256": _sha(root / "RECEIPT.json"),
        "company_db_sha256": _sha(root / "company.sqlite3"),
        "audit_task_credit": False,
    }
    _write(root / "MANIFEST.json", manifest)
    monkeypatch.setattr(
        simulation,
        "REVIEWED_TRANSITION_PINS",
        {
            k: _sha(root / name)
            for k, name in {
                "receipt": "RECEIPT.json",
                "manifest": "MANIFEST.json",
                "database": "company.sqlite3",
            }.items()
        },
    )
    return root


def test_clean_and_messy_are_native_payload_free_and_causal(tmp_path, monkeypatch):
    transition = _transition(tmp_path, monkeypatch)
    dest = tmp_path / "phi-ba"
    manifest = simulation.create(
        dest,
        repository=REPOSITORY,
        transition_root=transition,
        clean_branch="PHI-CLEAN",
        messy_branch="PHI-MESSY",
    )
    assert manifest["native_version_count"] == 37
    assert simulation.verify(dest, repository=REPOSITORY, transition_root=transition) == manifest
    receipt = json.loads((dest / "RECEIPT.json").read_text())
    assert receipt["open_exception_counts"] == {"CLEAN": 0, "MESSY": 1}
    assert receipt["exception_event_row_counts"] == {"CLEAN": 0, "MESSY": 9}
    assert receipt["final_states"] == {"CLEAN": "RECONCILED", "MESSY": "QUARANTINED"}
    assert len(receipt["records"]["CLEAN"]) == 18
    assert len(receipt["records"]["MESSY"]) == 19
    with sqlite3.connect(dest / "company.sqlite3") as db:
        db.row_factory = sqlite3.Row
        assert db.execute("SELECT COUNT(*) FROM grants").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM collections").fetchone()[0] == 0
        bodies = [json.loads(x[0]) for x in db.execute("SELECT content FROM versions")]
    assert all(
        x["fixture_contains_real_phi"] is False for x in bodies if "fixture_contains_real_phi" in x
    )
    assert all(x["payload_bytes"] == 0 for x in bodies if "payload_bytes" in x)
    clean_downstream = next(
        x for x in bodies if x.get("scenario") == "CLEAN" and x.get("record") == "BAA-SUB-01"
    )
    clean_intake = next(
        x for x in bodies if x.get("scenario") == "CLEAN" and x.get("record") == "FLOW-RENO-01"
    )
    messy_downstream = next(
        x for x in bodies if x.get("scenario") == "MESSY" and x.get("record") == "BAA-SUB-01"
    )
    messy_route = next(
        x for x in bodies if x.get("scenario") == "MESSY" and x.get("record") == "FLOW-BOISE-01"
    )
    assert clean_downstream["event_at"] < clean_intake["event_at"]
    assert {
        "ROLE-01",
        "DA-PHI-BA-2027",
        "AP-CUST-LEGAL",
        "AP-CUST-TECH",
        "AP-CUST-SEC",
        "AP-CUST-DATA",
        "VA-CUST-01",
        "BAA-CUST-01",
        "AP-SUB-LEGAL",
        "AP-SUB-TECH",
        "AP-SUB-SEC",
        "AP-SUB-DATA",
        "VA-SUB-01",
        "BAA-SUB-01",
    } <= set(clean_intake["authorization_gate_refs"])
    assert all(
        x["effective_at"] <= clean_intake["event_at"]
        and x["available_at"] <= clean_intake["event_at"]
        for x in clean_intake["authorization_gate_refs"].values()
    )
    assert messy_route["event_at"] < messy_downstream["event_at"]
    assert messy_route["destination_ack"] == "UNVERIFIED"
    assert messy_route["simulated_support_copy_acknowledgement_status"] == "NOT_ESTABLISHED"
    assert messy_route["simulated_copy_reached_support"] == "UNDETERMINED"
    assert "BAA-SUB-01" not in messy_route["authorization_gate_refs"]
    assert {
        "DA-PHI-BA-2027",
        "AP-SUB-LEGAL",
        "AP-SUB-TECH",
        "AP-SUB-SEC",
        "AP-SUB-DATA",
        "VA-SUB-01",
    } <= set(messy_downstream["authorization_gate_refs"])
    for scenario in ("CLEAN", "MESSY"):
        approvals = [
            x
            for x in bodies
            if x.get("scenario") == scenario and x.get("system") == "contract_approval"
        ]
        assert len(approvals) == 8
        assert {(x["record"], x["actor_id"]) for x in approvals} == {
            (f"AP-{party}-{role}", actor)
            for party in ("CUST", "SUB")
            for role, actor in (
                ("LEGAL", "AS-P003"),
                ("TECH", "AS-P007"),
                ("SEC", "AS-P008"),
                ("DATA", "AS-P014"),
            )
        }
        assert all(x["approval_reviewer_ids"] == [x["actor_id"]] for x in approvals)
        for party in ("CUST", "SUB"):
            agreement = next(
                x
                for x in bodies
                if x.get("scenario") == scenario and x.get("record") == f"BAA-{party}-01"
            )
            terms = agreement["synthetic_terms"]
            assert len(terms) == 8
            expected_hash = simulation.sha(encoded(terms))
            assert agreement["reviewed_synthetic_terms_sha256"] == expected_hash
            for prefix in ("AP", "VA"):
                related = [
                    x
                    for x in bodies
                    if x.get("scenario") == scenario
                    and x.get("record", "").startswith(f"{prefix}-{party}-")
                ]
                assert len(related) == (4 if prefix == "AP" else 1)
                assert all(x["reviewed_synthetic_terms_sha256"] == expected_hash for x in related)
    assert messy_downstream["exception_open"] is True
    assert all(
        x["contract_executed_in_simulation"] is False
        for x in bodies
        if x.get("system") in {"contract_approval", "counterparty_acceptance"}
    )
    assert all(x.get("real_world_operation") is False for x in bodies if x.get("system"))


def test_unreviewed_transition_cannot_create_source(tmp_path, monkeypatch):
    monkeypatch.setattr(simulation, "REVIEWED_TRANSITION_PINS", None)
    dest = tmp_path / "phi-ba"
    with pytest.raises(CompanyStoreError, match="reviewed transition pins"):
        simulation.create(
            dest,
            repository=REPOSITORY,
            transition_root=tmp_path,
            clean_branch="PHI-CLEAN",
            messy_branch="PHI-MESSY",
        )
    assert not dest.exists()


def test_transition_release_or_hash_tamper_blocks_creation(tmp_path, monkeypatch):
    transition = _transition(tmp_path, monkeypatch)
    receipt_path = transition / "RECEIPT.json"
    receipt = json.loads(receipt_path.read_text())
    receipt["records"]["MESSY"] = [
        x for x in receipt["records"]["MESSY"] if x["record"] != "RL-BOISE"
    ]
    _write(receipt_path, receipt)
    with pytest.raises(CompanyStoreError, match="Reviewed transition source bytes"):
        simulation.create(
            tmp_path / "blocked",
            repository=REPOSITORY,
            transition_root=transition,
            clean_branch="PHI-CLEAN",
            messy_branch="PHI-MESSY",
        )


def test_active_transition_sidecar_blocks_creation(tmp_path, monkeypatch):
    transition = _transition(tmp_path, monkeypatch)
    sidecar = transition / "company.sqlite3-wal"
    sidecar.write_bytes(b"uncheckpointed")
    with pytest.raises(CompanyStoreError, match="no sidecars"):
        simulation.create(
            tmp_path / "blocked",
            repository=REPOSITORY,
            transition_root=transition,
            clean_branch="PHI-CLEAN",
            messy_branch="PHI-MESSY",
        )


def test_dangling_transition_sidecar_symlink_blocks_creation(tmp_path, monkeypatch):
    transition = _transition(tmp_path, monkeypatch)
    (transition / "company.sqlite3-shm").symlink_to(transition / "absent-shm")
    with pytest.raises(CompanyStoreError, match="no sidecars"):
        simulation.create(
            tmp_path / "blocked",
            repository=REPOSITORY,
            transition_root=transition,
            clean_branch="PHI-CLEAN",
            messy_branch="PHI-MESSY",
        )


def test_transition_private_mode_change_during_read_blocks_creation(tmp_path, monkeypatch):
    transition = _transition(tmp_path, monkeypatch)
    original = simulation._frozen_snapshot
    called = False

    def flip_after_first_snapshot(paths):
        nonlocal called
        snapshot = original(paths)
        if not called:
            called = True
            paths["database"].chmod(0o644)
        return snapshot

    monkeypatch.setattr(simulation, "_frozen_snapshot", flip_after_first_snapshot)
    with pytest.raises(CompanyStoreError, match="Private regular source file"):
        simulation.create(
            tmp_path / "blocked",
            repository=REPOSITORY,
            transition_root=transition,
            clean_branch="PHI-CLEAN",
            messy_branch="PHI-MESSY",
        )


def test_prior_transition_schema_rejected_even_with_repinned_hashes(tmp_path, monkeypatch):
    transition = _transition(tmp_path, monkeypatch)
    receipt_path = transition / "RECEIPT.json"
    manifest_path = transition / "MANIFEST.json"
    receipt = json.loads(receipt_path.read_text())
    receipt["schema"] = "SH_FICTIONAL_2027_RUNTIME_TRANSITION_V2"
    _write(receipt_path, receipt)
    manifest = json.loads(manifest_path.read_text())
    manifest["schema"] = "SH_FICTIONAL_2027_RUNTIME_TRANSITION_V2_MANIFEST"
    manifest["receipt_sha256"] = _sha(receipt_path)
    _write(manifest_path, manifest)
    monkeypatch.setattr(
        simulation,
        "REVIEWED_TRANSITION_PINS",
        {
            "receipt": _sha(receipt_path),
            "manifest": _sha(manifest_path),
            "database": _sha(transition / "company.sqlite3"),
        },
    )
    with pytest.raises(CompanyStoreError, match="Reviewed transition scope"):
        simulation.create(
            tmp_path / "blocked",
            repository=REPOSITORY,
            transition_root=transition,
            clean_branch="PHI-CLEAN",
            messy_branch="PHI-MESSY",
        )


def test_authorization_gate_requires_available_as_well_as_effective_time():
    gates = {
        key: {
            "sha256": "fixture",
            "effective_at": "2027-08-11T03:00:00+00:00",
            "available_at": "2027-08-11T07:00:00+00:00",
        }
        for key in ("ROLE-01", "BAA-CUST-01", "BAA-SUB-01")
    }
    with pytest.raises(CompanyStoreError, match="effective and available"):
        simulation._check_event_gate("CLEAN", "FLOW-RENO-01", "2027-08-11T05:00:00+00:00", gates)


def test_transition_missing_release_rejected_even_if_file_hashes_repinned(tmp_path, monkeypatch):
    transition = _transition(tmp_path, monkeypatch)
    receipt_path = transition / "RECEIPT.json"
    manifest_path = transition / "MANIFEST.json"
    receipt = json.loads(receipt_path.read_text())
    receipt["records"]["MESSY"] = [
        x for x in receipt["records"]["MESSY"] if x["record"] != "RL-BOISE"
    ]
    _write(receipt_path, receipt)
    manifest = json.loads(manifest_path.read_text())
    manifest["receipt_sha256"] = _sha(receipt_path)
    _write(manifest_path, manifest)
    monkeypatch.setattr(
        simulation,
        "REVIEWED_TRANSITION_PINS",
        {
            "receipt": _sha(receipt_path),
            "manifest": _sha(manifest_path),
            "database": _sha(transition / "company.sqlite3"),
        },
    )
    with pytest.raises(CompanyStoreError, match="Exact reviewed site release"):
        simulation.create(
            tmp_path / "blocked",
            repository=REPOSITORY,
            transition_root=transition,
            clean_branch="PHI-CLEAN",
            messy_branch="PHI-MESSY",
        )


def test_frozen_flow_tamper_rejected(tmp_path, monkeypatch):
    transition = _transition(tmp_path, monkeypatch)
    dest = tmp_path / "phi-ba"
    simulation.create(
        dest,
        repository=REPOSITORY,
        transition_root=transition,
        clean_branch="PHI-CLEAN",
        messy_branch="PHI-MESSY",
    )
    receipt_path = dest / "RECEIPT.json"
    receipt = json.loads(receipt_path.read_text())
    receipt["open_exception_counts"]["MESSY"] = 0
    _write(receipt_path, receipt)
    with pytest.raises(CompanyStoreError, match="manifest/source pin"):
        simulation.verify(dest, repository=REPOSITORY, transition_root=transition)
